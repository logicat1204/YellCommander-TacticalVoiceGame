"""Mismas entradas por HTTP, tres perfiles y modelos precalentados. Excluye Gemma y TTS."""
import argparse
import base64
import json
import sys
import subprocess
import tempfile
import threading
import time
import uuid
from contextlib import ExitStack
from pathlib import Path
from statistics import median, quantiles
from urllib.request import ProxyHandler, Request, build_opener

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parents[1] / "AI NLP"))
from slots import MOVEMENT, STATIC, SlotClassifier
from voz import Voz
from yell.contract import ROOT
from yell.decision import DecisionModel
from yell.decision_data import read_data
from yell.inference import SpeechObservation, SpeechToText
from yell.service import Service, classify_current
from yell.voice_bench import SyntheticSpeaker


def metrics(rows):
    values = [r["ms"] for r in rows]
    return dict(n=len(rows), exactos=sum(r["ok"] for r in rows),
                ordenes_esperadas=sum(r["esperado"] is not None for r in rows),
                ordenes_recuperadas=sum(r["ok"] and r["esperado"] is not None for r in rows),
                sujeto_o_destino_erroneo=sum(not r["ok"] and r["esperado"] is not None and
                                             r["obtenido"] is not None for r in rows),
                movimientos_indebidos=sum(r["movimiento_indebido"] for r in rows),
                p50_ms=round(median(values), 2), p95_ms=round(quantiles(values, n=100, method="inclusive")[94], 2))


def project(result):
    if result.get("accion") not in MOVEMENT:
        return None
    return [result["sujeto"]["id"], result["lugar"]]


def test_text(model, variant, rows=None):
    posture = SlotClassifier(posture=True)
    records = {"actual": [], "sujeto_lugar": [], "sujeto_lugar_postura": []}
    for row in rows if rows is not None else read_data()["test"]:
        expected = [row["subject"], row["location"]] if row["label"] in MOVEMENT else None
        for key, classifier in (("actual", classify_current), ("sujeto_lugar", variant.classify),
                                ("sujeto_lugar_postura", posture.classify)):
            start = time.perf_counter()
            decision, _, _ = classifier(model, row["text"], row["aliases"], row["roster"], row["here"], False)
            ms = round((time.perf_counter()-start)*1000, 3)
            actual = project(decision)
            posture_ok = (decision.get("postura") == ("mantener" if row["label"] in STATIC else "avanzar")
                          if expected else "postura" not in decision)
            records[key].append(dict(ok=actual == expected, postura_correcta=posture_ok and actual == expected,
                                     movimiento_indebido=actual is not None and expected is None,
                                     ms=ms, texto=row["text"], esperado=expected, obtenido=actual))
    report = {key: dict(**metrics(rows), errores=[r for r in rows if not r["ok"]]) for key, rows in records.items()}
    report["sujeto_lugar_postura"]["exactos_incluida_postura"] = sum(r["postura_correcta"] for r in records["sujeto_lugar_postura"])
    return report


def test_audio(variant, staged=False):
    # La devolución mínima permite medir el instante en que ya se conoce la decisión.
    class SilentDialogue:
        def reply(self, *args):
            return {"text": ""}
    synth = SyntheticSpeaker()
    cases = [
        ("Alfa, avancen por el centro.", ["Alfa", "centro"]),
        ("Bravo, defiendan nuestra base.", ["Bravo", "base_aliada"]),
        ("Alex, movete al centro.", ["Alfa-1", "centro"]),
        ("Alfa, ataquen la base enemiga.", ["Alfa", "base_enemiga"]),
        ("Alex, ¿cómo estás?", None), ("Bravo, ¿qué tal va todo?", None),
        ("Alfa, no avancen por el centro.", None), ("Alex, defendé.", None),
        ("Necesito a Bravo en el centro.", ["Bravo", "centro"]),
        ("Alfa, asegurame el flanco derecho.", ["Alfa", "flanco_derecho"]),
        ("Alfa, avancen por el centro.", ["Alfa", "centro"]),
        ("", None),
        ("Bravo, vayan a la izquierda.", ["Bravo", "flanco_izquierdo"]),
        ("Alex, pasate por el puente.", ["Alfa-1", "centro"]),
        ("Alfa, protejan el cuartel aliado.", ["Alfa", "base_aliada"]),
        ("Alex, ¿cuánta vida tenés?", None),
        ("Bravo, si te llaman desde el centro, avisame.", None),
        ("Alfa, tomá la base rival.", ["Alfa", "base_enemiga"]),
        ("Alex y Bravo, vayan al centro.", None),
        ("Bravo, volvé a nuestra base.", ["Bravo", "base_aliada"]),
    ]
    clips = [synth.synthesize(text, snr=12 if i == 10 else None) for i, (text, _) in enumerate(cases)]
    # Un segundo de silencio en PCM válido para la API.
    import io, wave
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wav:
            wav.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            wav.writeframes(bytes(32000))
        clips[11] = buf.getvalue()
    if staged:
        class Replay:
            def __init__(self, records):
                self.records = dict(zip(clips, records))
                self.device = records[0]["device"]
            def recognize(self, wav):
                return SpeechObservation(**self.records[wav]["observation"])
        with tempfile.TemporaryDirectory() as tmp:
            for i, clip in enumerate(clips):
                (Path(tmp)/f"{i:02}.wav").write_bytes(clip)
            engines = []
            for size in ("base", "small", "base-gpu", "small-gpu"):
                subprocess.run([sys.executable, __file__, "transcribir", "--datos", tmp, "--tam", size], check=True)
                engines.append(Replay(json.loads((Path(tmp)/"medidas.json").read_text(encoding="utf8"))))
        primary, retry, primary_gpu, retry_gpu = engines
    else:
        primary = SpeechToText(ROOT / "models/whisper-base")
        retry = SpeechToText(ROOT / "models/whisper-small")
        primary_gpu, retry_gpu = Voz(), Voz("small")
        primary.recognize(clips[0])
        retry.recognize(clips[0])
        primary_gpu.recognize(clips[0])
        retry_gpu.recognize(clips[0])
    model = DecisionModel()
    model.rank("unidad lugar")
    services = {}
    records = {}
    client = build_opener(ProxyHandler({}))
    with ExitStack() as stack:
        for name in ("anterior", "actual", "sujeto_lugar"):
            srv = stack.enter_context(Service(0, {"D": model}, primary_gpu if name=="sujeto_lugar" else primary,
                                              .7, retry_gpu if name=="sujeto_lugar" else retry, adaptive=name!="anterior",
                                              classifier=variant.classify if name=="sujeto_lugar" else classify_current,
                                              profile=name))
            srv.dialogue = SilentDialogue()
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            stack.callback(srv.shutdown)
            services[name] = srv.server_port
            records[name] = []
        names = list(services)
        for i, (text, expected) in enumerate(cases):
            for name in names[i%3:] + names[:i%3]:
                actor = dict(nombre="Alex", peloton="Alfa", distancia=10, disponible=True, estado="en servicio")
                body = dict(request_id=str(uuid.uuid4()), model="D", squads=["Alfa", "Bravo"], soldiers=["Alfa-1"],
                            roster={"Alfa-1": actor}, here="centro", wav=base64.b64encode(clips[i]).decode())
                req = Request(f"http://127.0.0.1:{services[name]}/v1/interpret", json.dumps(body).encode())
                with client.open(req, timeout=90) as response:
                    r = json.load(response)
                actual = project(r.get("decision", {}))
                if staged:
                    source = primary_gpu if name=="sujeto_lugar" else primary
                    decode = source.records[clips[i]]["ms"]
                    retry_source = retry_gpu if name=="sujeto_lugar" else retry
                    second = retry_source.records[clips[i]]["ms"] if r["speech"]["retried"] else 0.
                    r["total_ms"] += decode + second - r["stt_primary_ms"] - r["stt_retry_ms"]
                    r["stt_primary_ms"], r["stt_retry_ms"] = decode, second
                records[name].append(dict(texto=text, esperado=expected, obtenido=actual, ok=actual==expected,
                        movimiento_indebido=actual is not None and expected is None, ms=r["total_ms"],
                        nlp_ms=r["nlp_ms"], base_ms=r["stt_primary_ms"], small_ms=r["stt_retry_ms"],
                        transcripcion=r["transcript"], ruta=r["nlp_route"], speech=r["speech"]))
    return {k: dict(**metrics(v), tiempos="suma de etapas medidas" if staged else "HTTP servicio",
                    reintentos=sum(r["speech"]["retried"] for r in v), casos=v) for k,v in records.items()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prueba", choices=["texto", "voz", "transcripciones", "transcribir"])
    parser.add_argument("--por-etapas", action="store_true")
    parser.add_argument("--datos", type=Path)
    parser.add_argument("--tam", choices=["base", "small", "base-gpu", "small-gpu"])
    args = parser.parse_args()
    if args.prueba == "transcribir":
        from dataclasses import asdict
        engine = Voz(args.tam.split("-")[0]) if args.tam.endswith("-gpu") else SpeechToText(ROOT / f"models/whisper-{args.tam}")
        audios = [p.read_bytes() for p in sorted(args.datos.glob("*.wav"))]
        engine.recognize(audios[0])
        records = []
        for clip in audios:
            start = time.perf_counter()
            observation = engine.recognize(clip)
            records.append(dict(ms=round((time.perf_counter()-start)*1000, 3), observation=asdict(observation),
                                device=getattr(engine, "device", "cpu")))
        (args.datos/"medidas.json").write_text(json.dumps(records), encoding="utf8")
        sys.exit(0)
    slot = SlotClassifier()
    if args.prueba in ("texto", "transcripciones"):
        model = DecisionModel()
        model.rank("unidad lugar")
        diagnostic = None
        if args.prueba == "transcripciones":
            lines = (ROOT / "Data/decisiones/transcripciones.jsonl").read_text(encoding="utf8").splitlines()
            diagnostic = [json.loads(line) for line in lines if line]
        result = test_text(model, slot, diagnostic)
    else:
        result = test_audio(slot, args.por_etapas)
    path = DIR / f"resultados_{args.prueba}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8")
    print({k: {a:b for a,b in v.items() if a not in ("errores", "casos")} for k,v in result.items()})
