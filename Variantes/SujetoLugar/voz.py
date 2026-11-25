"""Whisper Base en CUDA con alternativa CPU si faltan memoria o DLL."""
import os
import sys
from pathlib import Path
from yell.contract import ROOT
from yell.inference import SpeechToText


class Voz:
    def __init__(self, size="base", cpu=False):
        self.path = ROOT / f"models/whisper-{size}"
        self.device = "cpu" if cpu else "cuda"
        self.engine = None
        if not cpu and os.name == "nt":
            cuda_lib = Path(sys.prefix) / "Lib/site-packages/torch/lib"
            self.dll_path = os.add_dll_directory(str(cuda_lib))
            os.environ["PATH"] = str(cuda_lib) + os.pathsep + os.environ["PATH"]
        self.reserve = (1.5 if size == "small" else 1.) * 1024**3

    def fallback(self, exc):
        if self.device == "cpu":
            raise exc
        print(f"{self.path.name} pasa a CPU: {exc}", file=sys.stderr, flush=True)
        self.device = "cpu"
        self.engine = None
        self.engine = SpeechToText(self.path)

    def recognize(self, wav):
        try:
            if self.engine is None:
                if self.device == "cuda":
                    from cuda_memory import free_bytes
                    if free_bytes() < self.reserve:
                        self.device = "cpu"
                self.engine = SpeechToText(self.path, self.device)
            return self.engine.recognize(wav)
        except (RuntimeError, OSError, MemoryError) as exc:
            self.fallback(exc)
            return self.engine.recognize(wav)
