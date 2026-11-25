"""Prueba el servicio en ejecución con datos reproducibles, incluida la charla con TTS."""
import argparse
import base64
import json
import sys
import time
import uuid
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parents[1] / "AI NLP"))
from yell.voice_bench import SyntheticSpeaker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--puerto", type=int, default=18766)
    parser.add_argument("--salida", type=Path, required=True)
    args = parser.parse_args()
    client = build_opener(ProxyHandler({}))
    root = f"http://127.0.0.1:{args.puerto}"
    with client.open(root + "/health", timeout=3) as response:
        health = json.load(response)
    speaker = SyntheticSpeaker()
    rows = []
    actor = dict(nombre="Alex", peloton="Alfa", distancia=230, disponible=True, estado="en servicio",
                 salud=67, bajas=2, ve_rival=False, historia="Antes arreglaba relojes.")
    for phrase, spoken in (("Alex, avancen al centro.", False), ("Alfa, avancen por el centro.", True),
                           ("Alex, ¿cuánta salud tienes?", False), ("Alex, ¿a qué te dedicabas antes?", False),
                           ("Alfa, avancen por el centro.", True)):
        body = dict(request_id=str(uuid.uuid4()), model="D", squads=["Alfa"], soldiers=["Alfa-1"],
                    roster={"Alfa-1": actor}, here="centro", radio=True)
        body["wav" if spoken else "text"] = base64.b64encode(speaker.synthesize(phrase)).decode() if spoken else phrase
        req = Request(root + "/v1/interpret", json.dumps(body).encode(), {"Content-Type": "application/json"})
        start = time.perf_counter()
        with client.open(req, timeout=90) as response:
            row = json.load(response)
        row["ida_vuelta_ms"] = round(1000*(time.perf_counter()-start), 2)
        row["frase"] = phrase
        talk = row.get("dialogue", {})
        if talk:
            talk["bytes_pcm"] = len(base64.b64decode(talk.pop("pcm", "")))
        rows.append(row)
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(dict(health=health, casos=rows), ensure_ascii=False, indent=2), encoding="utf8")
    assert [r.get("command", {}).get("subject", {}).get("name") for r in rows[:2]] == ["Alfa-1", "Alfa"]
    assert all(r["command"]["location"] == {"id": "centro"} for r in rows[:2])
    voices = []
    for r in rows[2:4]:
        talk = r["dialogue"]
        assert talk["speaker_id"] == "Alfa-1" and talk["bytes_pcm"] > 0 and not talk.get("llm_error"), talk
        voices.append(talk["voice"])
        print(talk["text"], talk.get("first_token_ms"), talk.get("tts_ms"))
    assert len(set(voices)) == 1
    assert rows[-1]["command"]["subject"]["name"] == "Alfa" and rows[-1]["command"]["location"] == {"id":"centro"}


if __name__ == "__main__":
    main()
