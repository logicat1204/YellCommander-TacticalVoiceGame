"""Convert the supplied cues and synthesize short boot steps for the dirt arena."""
from pathlib import Path
import wave

import av
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RATE = 24000
OUTPUT = ROOT / ".yell-cache" / "valle-sounds"
OUTPUT.mkdir(parents=True, exist_ok=True)


def save(name, samples):
    peak = float(np.max(np.abs(samples)))
    pcm = (np.clip(samples / max(peak, 1), -1, 1) * 30000).astype("<i2")
    with wave.open(str(OUTPUT / f"{name}.wav"), "wb") as stream:
        stream.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        stream.writeframes(pcm.tobytes())


def convert(source, name, length=None):
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=RATE)
    frames = []
    with av.open(str(ROOT / "Assets" / "Sounds" / source)) as audio:
        for frame in audio.decode(audio=0):
            frames.extend(resampler.resample(frame))
        frames.extend(resampler.resample(None))
    samples = np.concatenate([f.to_ndarray()[0] for f in frames])
    active = np.flatnonzero(np.abs(samples) > np.max(np.abs(samples)) * .035)
    if active.size:
        samples = samples[max(0, active[0] - 160):active[-1] + 400]
    if length:
        samples = samples[:int(RATE * length)].copy()
        fade = min(len(samples), 360)
        samples[-fade:] *= np.linspace(1, 0, fade)
    save(name, samples)


convert("gunshot.mp3", "Disparo")
convert("soldier death.mp3", "Caida")
convert("walkie talkie start.mp3", "RadioEnvio", .24)
rng = np.random.default_rng(421)
for index in range(3):
    t = np.arange(int(RATE * .23)) / RATE
    grit = np.convolve(rng.uniform(-1, 1, len(t)), np.ones(7) / 7, "same")
    heel = np.sin(2 * np.pi * (55 - index * 4) * t) * np.exp(-42 * t)
    toe = np.exp(-((t - .065) / .028) ** 2) + .7 * np.exp(-((t - .028) / .012) ** 2)
    save(f"Paso{index + 1}", (.42 * heel + .83 * grit * toe) * np.minimum(1, t * 280))
