"""Resume los tiempos que Unreal registra por identificador de solicitud."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import median, quantiles

from .contract import ROOT


def read_log(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8-sig").splitlines() if line.strip()]


def summarize(directory, limit):
    rows = read_log(directory / "YellOrders.jsonl")[-limit:]
    audio = {r["request_id"]: r for r in read_log(directory / "YellAudio.jsonl") if r["event"] == "iniciado"}
    capture = {r["request_id"]: r for r in read_log(directory / "YellVoice.jsonl")}
    groups = defaultdict(list)
    for row in rows:
        trace = capture.get(row["request_id"], {})
        sound = audio.get(row["request_id"], {})
        dialogue = row.get("dialogue") or {}
        mode = row.get("input", "voz" if "release_to_feedback_ms" in row else "texto")
        kind = (row.get("decision") or {}).get("tipo", (row.get("command") or {}).get("intent", "error"))
        enriched = {
            "captura_ms": trace.get("audio_ms"), "pulsacion_ms": trace.get("held_ms"),
            "espera_stt_ms": row.get("stt_wait_ms"), "whisper_base_ms": row.get("stt_primary_ms"),
            "whisper_reintento_ms": row.get("stt_retry_ms"), "stt_ms": row.get("stt_ms"),
            "espera_decision_ms": row.get("decision_wait_ms"), "decision_ms": row.get("nlp_ms"),
            "espera_charla_ms": dialogue.get("generation_wait_ms"), "charla_ms": dialogue.get("generation_ms"),
            "primer_token_ms": dialogue.get("first_token_ms"), "espera_tts_ms": dialogue.get("tts_wait_ms"),
            "tts_ms": dialogue.get("tts_ms"), "servicio_ms": row.get("total_ms"),
            "respuesta_ms": row.get("release_to_feedback_ms", row.get("round_trip_ms")),
            "espera_reproduccion_ms": sound.get("since_queued_ms"),
            "inicio_audio_ms": sound.get("since_input_ms"),
        }
        enriched["reintento"] = bool((row.get("speech") or {}).get("retried"))
        groups[(row.get("profile", "actual"), row.get("model", "?"), mode, kind,
                dialogue.get("model", ""))].append(enriched)
    report = []
    for (profile, model, mode, kind, chat_model), items in sorted(groups.items()):
        metrics = {}
        for field in items[0]:
            if field == "reintento":
                continue
            values = [r[field] for r in items if isinstance(r[field], (float, int))]
            if values:
                metrics[field] = {"n": len(values), "p50": round(median(values), 1),
                                  "p95": round(quantiles(values, n=100, method="inclusive")[94], 1)
                                  if len(values) > 1 else None}
        report.append({"perfil": profile, "modelo": model, "modelo_charla": chat_model or None, "entrada": mode,
                       "tipo": kind, "n": len(items), "reintentos": sum(r["reintento"] for r in items), "tiempos": metrics})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saved", type=Path, default=ROOT.parent / "WarCommanderDemo" / "Saved")
    parser.add_argument("--ultimas", type=int, default=30)
    args = parser.parse_args()
    if args.ultimas < 1:
        parser.error("--ultimas debe ser positivo")
    report = summarize(args.saved, args.ultimas)
    if not report:
        parser.error(f"No hay transmisiones en {args.saved.resolve()}")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
