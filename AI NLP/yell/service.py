import argparse
import base64
import binascii
import io
import json
import re
import threading
import time
import wave
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .contract import PLACES, ROOT, UNITS, command, matches, tokens
from .inference import SPEECH_FEEDBACK, LocalLLM, SpeechToText, infer
from .metrics import semantic
from .live_commands import direct_order, negated_order, repair_spoken_order
from .decision import WEIGHTS, DecisionModel, decide, resolve, wire

MAX_BODY = 3_200_000
MAX_PENDING = 4


def wav_input(encoded):
    if not isinstance(encoded, str):
        raise ValueError("El audio debe codificarse en base64")
    try:
        wav = base64.b64decode(encoded, validate=True)
        with wave.open(io.BytesIO(wav), "rb") as stream:
            channels, width, rate, frames = (stream.getnchannels(), stream.getsampwidth(),
                                             stream.getframerate(), stream.getnframes())
            if (channels, width) != (1, 2) or not 8000 <= rate <= 96000 or not 0.25 <= frames / rate <= 12.1:
                raise ValueError("El audio debe ser WAV PCM mono de 16 bits y durar entre 0,25 y 12 segundos")
            if len(stream.readframes(frames)) != frames * width * channels:
                raise ValueError("El archivo WAV está incompleto")
    except (binascii.Error, EOFError, wave.Error) as exc:
        raise ValueError("El audio WAV es inválido") from exc
    return wav


def active_aliases(names, soldiers=None):
    if not isinstance(names, list) or not 1 <= len(names) <= 5 or any(
            not isinstance(name, str) or not tokens(name) or len(name) > 64 for name in names):
        raise ValueError("Catálogo de pelotones inválido")
    aliases = {**UNITS, **{name: UNITS.get(name, [name]) for name in names}}
    if soldiers is None:
        return aliases
    if not isinstance(soldiers, list) or len(soldiers) > 25:
        raise ValueError("Catálogo de soldados inválido")
    numbers = ("uno", "dos", "tres", "cuatro", "cinco")
    for soldier in soldiers:
        if not isinstance(soldier, str) or not 2 < len(soldier) <= 64:
            raise ValueError("Indicativo de soldado inválido")
        prefix, _, suffix = soldier.rpartition("-")
        if prefix not in names or suffix not in ("1", "2", "3", "4", "5"):
            raise ValueError("El indicativo de soldado requiere un pelotón activo")
        word = numbers[int(suffix) - 1]
        aliases[soldier] = [f"soldado {prefix} {word}", f"soldado {prefix} {suffix}"]
        if (prefix, suffix) != ("Médico", "1"):
            aliases[soldier].append(f"{prefix} {word}")
    return aliases


def check_live_agreement(proposal, reference):
    return proposal["intent"] not in ("orden", "motivacion") or (
        reference is not None and semantic(proposal) == semantic(reference)
    )


def prefer_retry(first, second, aliases):
    if second.status != "voz":
        return False
    qualifiers = {"no", "nunca", "jamas", "tampoco", "ni", "si", "cuando", "excepto", "pero", "despues", "luego"}
    lost = set(tokens(first.text)) - set(tokens(second.text))
    if lost & qualifiers or ("?" in first.text and "?" not in second.text):
        return False
    for catalog in (aliases, PLACES):
        named = {name for _, _, name in matches(first.text, catalog)}
        if named and named != {name for _, _, name in matches(second.text, catalog)}:
            return False
    return True


class Service(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port, models, speech, threshold, speech_retry=None, verifier=None):
        self.models, self.speech, self.threshold = models, speech, threshold
        self.speech_retry = speech_retry
        self.verifier = verifier or models.get("C")
        self.inference_slot = threading.BoundedSemaphore(MAX_PENDING)
        self.speech_lock = threading.Lock()
        self.decision_lock = threading.Lock()
        super().__init__(("127.0.0.1", port), Handler)

    def interpret(self, model, text, aliases, squads, spoken):
        if negated_order(text, aliases):
            return command(), command(), "Orden negada. El pelotón mantiene su instrucción.", "negacion", None
        names = matches(text, aliases)
        if (len(names) == 1 and names[0][0] == 0
                and tokens(text)[names[0][1]:] in (["defiendan"], ["protejan"], ["cubran"])):
            name = names[0][2]
            reason = f"¿Qué lugar debe defender {name}? Por ejemplo, «{name}, defiendan nuestra base»."
            return command(), command(), reason, "aclaracion", None
        direct = direct_order(text, aliases)
        if direct is not None:
            return direct, direct, "", "gramatica", None
        if spoken:
            repaired = repair_spoken_order(text, aliases, squads)
            if repaired is not None:
                return repaired, repaired, "", "indicativo_voz", None
        raw, guarded, reason, _ = infer(self.models[model], text, aliases, self.threshold)
        if model == "B" and guarded["intent"] in ("orden", "motivacion"):
            for name, verifier in (("A", self.models.get("A")), ("C", self.verifier)):
                if verifier is not None:
                    _, reference, _, _ = infer(verifier, text, aliases, self.threshold)
                    if check_live_agreement(guarded, reference):
                        return raw, guarded, reason, "modelo", name
            return raw, command(), "La interpretación no fue consistente. Repita la orden con otras palabras.", "modelo", None
        return raw, guarded, reason, "modelo", None


class Handler(BaseHTTPRequestHandler):
    def respond(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_GET(self):
        if self.path == "/health":
            self.respond(200, {"models": list(self.server.models), "stt_configured": self.server.speech is not None,
                               "stt_retry": self.server.speech_retry is not None,
                               "verifier_c": self.server.verifier is not None, "max_pending": MAX_PENDING})
        else:
            self.respond(404, {"error": "Ruta desconocida"})

    def do_POST(self):
        if self.path != "/v1/interpret":
            self.respond(404, {"error": "Ruta desconocida"})
            return
        request_id = ""
        received = time.perf_counter()
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= MAX_BODY:
                raise ValueError("Tamaño de solicitud inválido")
            self.connection.settimeout(10)
            body = json.loads(self.rfile.read(length))
            required = {"request_id", "model", "squads"}
            if (not isinstance(body, dict) or not required <= set(body)
                    or set(body) - required - {"soldiers", "roster", "here", "radio"} not in ({"text"}, {"wav"})):
                raise ValueError("Campos de solicitud inválidos")
            if not isinstance(body["request_id"], str) or not re.fullmatch(r"[a-fA-F0-9-]{16,48}", body["request_id"]):
                raise ValueError("Identificador de solicitud inválido")
            request_id = body["request_id"]
            if not isinstance(body["model"], str) or body["model"] not in self.server.models:
                self.respond(503, {"request_id": request_id, "error": "El modelo seleccionado no está configurado"})
                return
            aliases = active_aliases(body["squads"], body.get("soldiers"))
            roster = body.get("roster", {})
            if not isinstance(roster,dict) or len(roster)>25:
                raise ValueError("Plantilla inválida")
            for uid, actor in roster.items():
                if (uid not in body.get("soldiers",[]) or not isinstance(actor,dict)
                        or actor.get("peloton") != uid.rpartition("-")[0]
                        or not isinstance(actor.get("nombre"),str) or not 0<len(actor["nombre"])<=40
                        or not isinstance(actor.get("estado"),str) or len(actor["estado"])>100
                        or not isinstance(actor.get("distancia"),(int,float))
                        or not isinstance(actor.get("disponible"),bool)):
                    raise ValueError("Datos de soldado inválidos")
                aliases[uid].append(actor["nombre"])
            text = body.get("text", "")
            if not isinstance(text, str) or len(text) > 500:
                raise ValueError("La frase debe tener como máximo 500 caracteres")
            wav = wav_input(body["wav"]) if "wav" in body else None
            if wav and not self.server.speech:
                self.respond(503, {"request_id": request_id, "error": "Whisper no está configurado"})
                return
            if not self.server.inference_slot.acquire(blocking=False):
                self.respond(429, {"request_id": request_id, "error": "La radio ya tiene cuatro solicitudes pendientes."})
                return
            try:
                started = time.perf_counter()
                extra = {}
                timing = {"stt_wait_ms": 0., "stt_primary_ms": 0., "stt_retry_ms": 0., "decision_wait_ms": 0.}
                observation = None
                speech_info = None
                if wav:
                    waiting = time.perf_counter()
                    with self.server.speech_lock:
                        primary = time.perf_counter()
                        timing["stt_wait_ms"] = 1000 * (primary - waiting)
                        first = observation = self.server.speech.recognize(wav)
                        timing["stt_primary_ms"] = 1000 * (time.perf_counter() - primary)
                        retried = (self.server.speech_retry is not None
                                   and first.status in ("voz", "transcripcion_incierta")
                                   and not direct_order(first.text, aliases) and not negated_order(first.text, aliases))
                        if retried:
                            retry_start = time.perf_counter()
                            second = self.server.speech_retry.recognize(wav)
                            timing["stt_retry_ms"] = 1000 * (time.perf_counter() - retry_start)
                            if prefer_retry(first, second, aliases):
                                observation = second
                    speech_info = asdict(observation)
                    text = speech_info.pop("text")
                    speech_info.update(retried=retried, first_transcript=first.text, used_retry=observation is not first)
                stt_ms = timing["stt_primary_ms"] + timing["stt_retry_ms"]
                if observation and observation.status != "voz":
                    raw, guarded = command(), command()
                    reason, route, verified_by, nlp_ms = SPEECH_FEEDBACK[observation.status], "sin_voz", None, 0.0
                elif body["model"] == "D":
                    active = {k:v for k,v in aliases.items() if k in body["squads"] or k in roster}
                    model = self.server.models["D"]
                    waiting = time.perf_counter()
                    with self.server.decision_lock:
                        parsing = time.perf_counter()
                        # A short, explicit order can be resolved against the live roster directly.
                        direct = direct_order(text, active)
                        route = "clasificador" if model else "vista_previa"
                        result = None
                        if direct is not None:
                            ranks = [(direct["action"], 1.0)]
                            result = resolve(text, ranks, active, roster, body.get("here"))
                            if result["tipo"] == "accion":
                                route = "gramatica"
                            else:
                                result = None
                        if result is None:
                            result, ranks = decide(model,text,active,roster,body.get("here"),observation is not None)
                    timing["decision_wait_ms"] = 1000 * (parsing - waiting)
                    nlp_ms = round(1000*(time.perf_counter()-parsing),3)
                    raw = guarded = wire(result)
                    reason, verified_by = "", None
                    extra.update(decision=result,alternativas=ranks[:3])
                    if result["tipo"] == "charla":
                        extra["dialogue"] = self.server.dialogue.reply(text,result,roster,body.get("radio",True))
                else:
                    waiting = time.perf_counter()
                    with self.server.decision_lock:
                        parsing = time.perf_counter()
                        raw, guarded, reason, route, verified_by = self.server.interpret(
                            body["model"], text, aliases, body["squads"], observation is not None)
                    timing["decision_wait_ms"] = 1000 * (parsing - waiting)
                    nlp_ms = round((time.perf_counter() - parsing) * 1000, 3)
            finally:
                self.server.inference_slot.release()
            self.respond(200, {**extra,"request_id": request_id, "model": body["model"], "transcript": text,
                               "prediction": raw, "command": guarded, "reason": reason,
                               "input": "voz" if wav else "texto",
                               "request_parse_ms": round(1000 * (started - received), 3),
                               **{k: round(v, 3) for k, v in timing.items()},
                               "speech": speech_info, "nlp_route": route, "verified_by": verified_by,
                               "stt_ms": round(stt_ms, 3), "nlp_ms": nlp_ms,
                               "total_ms": round((time.perf_counter() - started) * 1000, 3)})
        except (ValueError, TypeError, UnicodeError, TimeoutError) as exc:
            self.respond(400, {"request_id": request_id, "error": str(exc)})
        except RuntimeError as exc:
            self.respond(503, {"request_id": request_id, "error": str(exc)})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--llama-port", type=int, default=8081)
    trained = ROOT / "models" / "scratch-fase1.pt"
    parser.add_argument("--checkpoint", type=Path, default=trained if trained.is_file() else ROOT / "models" / "scratch.pt")
    parser.add_argument("--whisper", type=Path)
    parser.add_argument("--whisper-retry", type=Path)
    parser.add_argument("--transfer", type=Path)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--decisiones", action="store_true")
    parser.add_argument("--dialogue-config",type=Path,default=Path(__file__).with_name("dialogue.json"))
    parser.add_argument("--threshold", type=float, default=0.70)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("El umbral debe estar entre 0 y 1")
    models = {} if args.no_llm else {"B": LocalLLM(args.llama_port)}
    if args.checkpoint.is_file() and not args.decisiones:
        from .scratch import ScratchModel

        models["A"] = ScratchModel(args.checkpoint)
        print(f"Pesos activos de A: {args.checkpoint.name}", flush=True)
    if args.transfer:
        from .transfer import TransferModel

        models["C"] = TransferModel(args.transfer)
    dialogue = None
    if args.decisiones:
        from .dialogue import Dialogue
        dialogue = Dialogue(args.dialogue_config)
    speech = SpeechToText(args.whisper) if args.whisper else None
    retry = SpeechToText(args.whisper_retry) if speech and args.whisper_retry else None
    verifier = models.get("C")
    weights = ROOT / "models" / "transfer-c"
    if "B" in models and verifier is None and (weights / "transfer.safetensors").is_file():
        try:
            from .transfer import TransferModel
        except ImportError:
            print("Verificación de B disponible con A. Faltan dependencias opcionales de C.", flush=True)
        else:
            verifier = TransferModel(weights)
    with Service(args.port, models, speech, args.threshold, retry, verifier) as server:
        if args.decisiones:
            models.clear()
            models["D"] = DecisionModel() if (WEIGHTS/"actual.txt").is_file() else None
            server.dialogue = dialogue
            print("Clasificador entrenado" if models["D"] else "Vista previa hasta entrenar el clasificador",flush=True)
        print(f"Yell Commander en http://127.0.0.1:{args.port}. Modelos configurados: {', '.join(models)}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
