"""Prueba de voz con el servicio de partida iniciado por el lanzador."""
import argparse
import base64
import json
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

from .contract import ROOT
from .voice_bench import SyntheticSpeaker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18765)
    parser.add_argument("--out", type=Path, default=ROOT.parent / "Documentacion/results/fase2/partida-nlp-voz.json")
    args = parser.parse_args()
    speaker = SyntheticSpeaker()
    client = build_opener(ProxyHandler({}))
    rows = []
    failures = []
    for kind, phrase, intent, name, action, zone in (
        ("voz", "Alfa, avancen por el centro", "orden", "Alfa", "avanzar", "centro"),
        ("voz", "Bravo, defiendan nuestra base", "orden", "Bravo", "defender", "base_aliada"),
        ("voz", "Alfa, ataquen la base enemiga", "orden", "Alfa", "atacar", "base_enemiga"),
        ("voz", "Médicos, vayan al centro", "orden", "Médico", "avanzar", "centro"),
        ("voz", "Alfa, no ataquen la base enemiga", "desconocido", None, None, None),
        ("voz", "Me gusta el clima de hoy", "charla", None, None, None),
        ("texto", "Bravo defiendan", "desconocido", None, None, None),
        ("texto", "Alfa, exploren el flanco del medio", "orden", "Alfa", "explorar", "centro"),
        ("texto", "Muchachos vamos a ganar, ustedes pueden", "motivacion", None, None, None),
    ):
        payload = {"text": phrase} if kind == "texto" else {
            "wav": base64.b64encode(speaker.synthesize(phrase)).decode("ascii")}
        for model in ("A", "B"):
            data = dict(payload, model=model, squads=["Alfa", "Bravo", "Médico"], request_id=str(uuid4()))
            request = Request(f"http://127.0.0.1:{args.port}/v1/interpret", data=json.dumps(data).encode())
            with client.open(request, timeout=90) as response:
                result = json.load(response)
            order = result["command"]
            actual = (order["intent"], (order["subject"] or {}).get("name"), order["action"],
                      (order["location"] or {}).get("id"))
            correct = actual == (intent, name, action, zone)
            rows.append(dict(reference=phrase, input=kind, correct=correct, **result))
            if not correct:
                failures.append((model, phrase, actual))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"{len(rows) - len(failures)}/{len(rows)} respuestas esperadas", flush=True)
    if failures:
        raise SystemExit(str(failures))


if __name__ == "__main__":
    main()
