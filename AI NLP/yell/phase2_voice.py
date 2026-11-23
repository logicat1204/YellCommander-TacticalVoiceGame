"""Generate repeatable 48 kHz fixtures and profile Phase 2 speech locally."""
import argparse
import io
import json
import time
import wave
from dataclasses import asdict
from pathlib import Path
from statistics import median, quantiles

import av
import numpy as np

from .contract import ROOT
from .evaluate import get_model, evaluate_text
from .inference import SpeechToText
from .voice_bench import SyntheticSpeaker

RATE = 48000


def wav_pcm(samples):
    output = io.BytesIO()
    with wave.open(output, "wb") as stream:
        stream.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        stream.writeframes(np.asarray(samples, dtype="<i2").tobytes())
    return output.getvalue()


def resample(wav):
    with wave.open(io.BytesIO(wav), "rb") as stream:
        rate = stream.getframerate()
        source = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2")
    frame = av.AudioFrame.from_ndarray(source.reshape(1, -1), format="s16", layout="mono")
    frame.sample_rate = rate
    adapter = av.AudioResampler(format="s16", layout="mono", rate=RATE)
    result = adapter.resample(frame) + adapter.resample(None)
    return np.concatenate([block.to_ndarray().reshape(-1) for block in result])


def create_fixtures(root):
    root.mkdir(parents=True, exist_ok=True)
    speaker = SyntheticSpeaker()
    phrases = {
        "alfa": "Alfa, avancen por el centro.",
        "alfa_negada": "Alfa, no avancen por el centro.",
        "bravo": "Bravo, defiendan nuestra base.",
        "arenga": "Soldados, ustedes pueden con esto, vamos a ganar.",
    }
    clips = {name: resample(speaker.synthesize(text)) for name, text in phrases.items()}
    rng = np.random.default_rng(421)
    audio = clips["alfa"].astype(np.float64)
    noise = np.sqrt(np.mean(audio ** 2)) / (10 ** (12 / 20)) * rng.standard_normal(audio.size)
    clips["alfa_ruido_12db"] = np.clip(audio + noise, -32768, 32767)
    clips["ruido"] = np.clip(rng.normal(0, 1200, RATE * 2), -32768, 32767)
    clips["silencio"] = np.zeros(RATE, dtype=np.int16)
    for name, clip in clips.items():
        (root / f"{name}.wav").write_bytes(wav_pcm(clip))
    return phrases


def summarize(values):
    result = {"p50_ms": round(median(values), 2)}
    if len(values) > 1:
        result["p95_ms"] = round(quantiles(values, n=100, method="inclusive")[94], 2)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, default=ROOT.parent / ".yell-cache/phase2-voice")
    parser.add_argument("--out", type=Path, default=ROOT.parent / "Documentacion/results/fase2/voz-sintetica.json")
    args = parser.parse_args()
    phrases = create_fixtures(args.fixtures)
    models = {label: get_model(label) for label in ("A", "C")}
    report = {"sample_rate": RATE, "source": "eSpeak NG es-419; ruido blanco reproducible; silencio digital",
              "by_whisper": {}}
    for backend in ("tiny", "base"):
        recognizer = SpeechToText(ROOT / "models" / f"whisper-{backend}")
        recognizer.recognize((args.fixtures / "alfa.wav").read_bytes())
        rows = {}
        for name in (*phrases, "alfa_ruido_12db", "ruido", "silencio"):
            data = (args.fixtures / f"{name}.wav").read_bytes()
            begin = time.perf_counter()
            observed = recognizer.recognize(data)
            elapsed = (time.perf_counter() - begin) * 1000
            proposals = {label: evaluate_text(model, observed.text) for label, model in models.items()} if observed.text else {}
            rows[name] = {"reference": phrases.get(name, phrases["alfa"] if name == "alfa_ruido_12db" else None),
                          "recognition": asdict(observed), "stt_ms": round(elapsed, 3), "proposals": proposals}
        timings = [row["stt_ms"] for name, row in rows.items() if name != "silencio"]
        report["by_whisper"][backend] = {"cases": rows, "stt": summarize(timings)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for backend, data in report["by_whisper"].items():
        print(backend, data["stt"], {name: row["recognition"]["status"] for name, row in data["cases"].items()})


if __name__ == "__main__":
    main()
