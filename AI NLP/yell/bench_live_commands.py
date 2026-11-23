"""Mide el recorrido HTTP local de las órdenes de juego más frecuentes."""
import base64
import json
from statistics import median
from threading import Thread
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

from .contract import ROOT
from .evaluate import get_model
from .inference import SpeechToText
from .service import Service


def main():
    phrases = [
        ("Alfa, avancen hacia adelante a atacar", "atacar", "base_enemiga"),
        ("Alfa ataquen la base enemiga", "atacar", "base_enemiga"),
        ("Bravo, vayan a destruir la base del enemigo", "atacar", "base_enemiga"),
        ("Alpha ataque en la base enemigo.", "atacar", "base_enemiga"),
        ("Alfa adelante", "avanzar", "base_enemiga"),
        ("Bravo, avanzar más adelante", "avanzar", "base_enemiga"),
        ("Médicos al centro", "avanzar", "centro"),
        ("Médicos vayan a curar al centro", "curar", "centro"),
    ]
    models = {name: get_model(name) for name in "ABC"}
    opener = build_opener(ProxyHandler({}))
    with Service(0, models, SpeechToText(ROOT / "models/whisper-base"), 0.70) as server:
        Thread(target=server.serve_forever, daemon=True).start()
        def request(name, **inputs):
            body = dict(request_id=str(uuid4()), squads=["Alfa", "Bravo", "Médico"], model=name, **inputs)
            req = Request(f"http://127.0.0.1:{server.server_port}/v1/interpret", data=json.dumps(body).encode())
            with opener.open(req, timeout=30) as response:
                return json.load(response)
        for name in models:
            timings = []
            for _ in range(5):
                for phrase, action, zone in phrases:
                    result = request(name, text=phrase)
                    assert result["nlp_route"] == "gramatica", phrase
                    assert (result["command"]["action"], result["command"]["location"]["id"]) == (action, zone), phrase
                    timings.append(result["nlp_ms"])
            print(name, len(timings), "mediana NLP (ms)", median(timings), flush=True)
        clip = ROOT.parent / ".yell-cache/phase2-voice/alfa.wav"
        if clip.exists():
            result = request("B", wav=base64.b64encode(clip.read_bytes()).decode())
            assert result["command"]["action"] == "avanzar" and result["nlp_route"] == "gramatica"
            print("Voz sintética", result["stt_ms"], result["nlp_ms"], result["total_ms"], flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
