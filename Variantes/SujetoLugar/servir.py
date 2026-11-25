import argparse
from pathlib import Path
import sys

DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DIR.parents[1] / "AI NLP"))
from slots import SlotClassifier
from voz import Voz
from yell.contract import ROOT
from yell.dialogue import Dialogue
from yell.service import Service


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18766)
    parser.add_argument("--postura", action="store_true")
    parser.add_argument("--gemma2", action="store_true")
    parser.add_argument("--stt-cpu", action="store_true")
    args = parser.parse_args()
    classifier = SlotClassifier(args.postura)
    config = ROOT / "yell/dialogue.json" if args.gemma2 else DIR / "dialogue.json"
    with Service(args.port, {"D": None}, Voz(cpu=args.stt_cpu), .7,
                 Voz("small", cpu=args.stt_cpu), classifier=classifier.classify,
                 profile="sujeto_lugar_postura" if args.postura else "sujeto_lugar") as server:
        server.dialogue = Dialogue(config, defer_voice=True)
        if sys.platform == "win32":
            # Whisper usa CUDA en este proceso. Kokoro usa ONNX CPU para evitar
            # que el cargador nativo de cuDNN aborte al sintetizar la primera charla.
            server.dialogue.voice_device = "cpu"
        server.dialogue.context_fields = ("nombre", "peloton", "estado", "historia", "salud", "bajas", "ve_rival")
        server.serve_forever()


if __name__ == "__main__":
    main()
