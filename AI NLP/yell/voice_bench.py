"""Run an offline smoke test on reproducible Spanish audio and silence."""

import argparse
import ctypes
import io
import json
import math
import random
import time
import wave
from pathlib import Path
from statistics import median

from .contract import ROOT, tokens
from .inference import SpeechToText, infer

SENTENCES = (
    "Alfa, avancen por el centro.",
    "Bravo, defiendan nuestra base.",
    "Bravo, cancelen la orden anterior.",
    "Charlie, retrocedan inmediatamente.",
    "Alfa, no avancen por el centro.",
)
REPLIES = {
    "RadioCopiado": "¡Copiado, mi General!",
    "RadioAclarar": "Repita la orden, mi General.",
    "RadioMoral": "¡Por usted y por el almuerzo, mi General!",
}


class SyntheticSpeaker:
    def __init__(self):
        from espeakng_loader import get_data_path, load_library

        self.library = load_library()
        if not self.library:
            raise RuntimeError("No se pudo cargar eSpeak NG")
        self.samples = []
        self.callback_type = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(ctypes.c_short),
                                               ctypes.c_int, ctypes.c_void_p)
        self.callback = self.callback_type(self.on_audio)
        # AUDIO_OUTPUT_SYNCHRONOUS and espeakCHARS_UTF8, from the eSpeak NG C API.
        self.rate = self.library.espeak_Initialize(2, 0, str(Path(get_data_path()).parent).encode(), 0)
        if self.rate <= 0 or self.library.espeak_SetVoiceByName(b"es-419") != 0:
            raise RuntimeError("La voz sintética es-419 no está disponible")
        self.library.espeak_SetSynthCallback(self.callback)
        self.library.espeak_Synth.argtypes = [
            ctypes.c_char_p, ctypes.c_size_t, ctypes.c_uint, ctypes.c_int, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
        ]

    def on_audio(self, pcm, count, _events):
        if pcm and count > 0:
            self.samples.extend(pcm[:count])
        return 0

    def synthesize(self, phrase, snr=None):
        self.samples.clear()
        if phrase:
            text = phrase.encode("utf-8")
            if self.library.espeak_Synth(text, len(text) + 1, 0, 1, 0, 1, None, None) != 0:
                raise RuntimeError("No se pudo sintetizar la frase")
        pad = [0] * (self.rate // 4)
        samples = pad + self.samples + pad
        if snr is not None:
            rms = math.sqrt(sum(x * x for x in self.samples) / max(len(self.samples), 1))
            rng = random.Random(421)
            samples = [int(max(-32768, min(32767, x + rng.gauss(0, rms / (10 ** (snr / 20)))))) for x in samples]
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as stream:
            stream.setparams((1, 2, self.rate, 0, "NONE", "not compressed"))
            stream.writeframes(bytes((ctypes.c_short * len(samples))(*samples)))
        return buffer.getvalue()


def changes(left, right):
    prev = list(range(len(right) + 1))
    for row, word in enumerate(left, 1):
        curr = [row]
        for col, guess in enumerate(right, 1):
            curr.append(min(curr[-1] + 1, prev[col] + 1, prev[col - 1] + (word != guess)))
        prev = curr
    return prev[-1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT.parent / "Documentacion/results/voice.json")
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--reply-dir", type=Path, help="Genera las réplicas de radio para importarlas en Unreal")
    parser.add_argument("models", nargs="*", type=Path)
    args = parser.parse_args()
    if not args.models and not args.reply_dir:
        parser.error("Indica al menos un modelo de voz o --reply-dir")
    speaker = SyntheticSpeaker()
    if args.reply_dir:
        args.reply_dir.mkdir(parents=True, exist_ok=True)
        for key, text in REPLIES.items():
            (args.reply_dir / f"{key}.wav").write_bytes(speaker.synthesize(text))
    if not args.models:
        return
    utterances = [(text, noise, speaker.synthesize(text, noise)) for text in SENTENCES for noise in (None, 12)]
    utterances.append(("", None, speaker.synthesize("")))
    if args.fixture:
        args.fixture.parent.mkdir(parents=True, exist_ok=True)
        args.fixture.write_bytes(utterances[0][2])
    from .scratch import ScratchModel
    nlp = ScratchModel()
    report = {}
    for path in args.models:
        t0 = time.perf_counter()
        speech = SpeechToText(path)
        load_ms = round((time.perf_counter() - t0) * 1000, 2)
        speech.transcribe(utterances[0][2])
        outputs = []
        for text, snr, audio in utterances:
            start = time.perf_counter()
            transcript = speech.transcribe(audio)
            elapsed = (time.perf_counter() - start) * 1000
            _, command, reason, nlp_ms = infer(nlp, transcript)
            outputs.append({"text": text, "snr_db": snr, "transcript": transcript, "stt_ms": elapsed,
                            "nlp_ms": nlp_ms, "semantic_command": command, "reason": reason})
        clean, noisy = ([item for item in outputs if item["snr_db"] == snr and item["text"]] for snr in (None, 12))
        aggregate = {}
        for group, items in (("clean", clean), ("noisy", noisy)):
            words = sum(len(tokens(row["text"])) for row in items)
            errors = sum(changes(tokens(row["text"]), tokens(row["transcript"])) for row in items)
            aggregate[group] = {"samples": len(items), "wer": errors / words,
                                "stt_median_ms": median(row["stt_ms"] for row in items)}
        report[path.name] = {"load_ms": load_ms, "stats": aggregate, "examples": outputs}
        print(f"{path.name}: {aggregate}", flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
