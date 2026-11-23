"""Conversación local. El texto generado solo alimenta subtítulos y audio."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
from threading import Lock
import time
from urllib.request import Request, ProxyHandler, build_opener

from .contract import ROOT


class Dialogue:
    def __init__(self, config):
        import torch  # Carga las DLL CUDA y cuDNN antes de ONNX Runtime.
        if os.name == "nt":
            os.environ["PATH"] = str(Path(torch.__file__).parent/"lib") + os.pathsep + os.environ["PATH"]
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        self.cfg = json.loads(config.read_text(encoding="utf8"))
        assets = ROOT/"models/dialogo"
        options = ort.SessionOptions()
        options.log_severity_level = 3
        session = ort.InferenceSession(str(assets/"kokoro.onnx"),sess_options=options,
            providers=[("CUDAExecutionProvider",{"gpu_mem_limit":1024**3}),"CPUExecutionProvider"])
        if session.get_providers()[0] != "CUDAExecutionProvider":
            raise RuntimeError("Kokoro requiere ONNX Runtime GPU con CUDA y cuDNN disponibles.")
        self.tts = Kokoro.from_session(session,str(assets/"voices.bin"))
        self.tts.create("Listo.",voice=self.cfg["voices"][0],speed=self.cfg["speed"],lang="es")
        self.client = build_opener(ProxyHandler({}))
        self.generation_lock = Lock()
        self.synthesis_lock = Lock()

    def reply(self, text, decision, roster, radio):
        import numpy as np
        from scipy.signal import butter, sosfilt
        who = decision.get("interlocutor") or {}
        candidates = [(uid,v) for uid,v in roster.items() if v["disponible"] and (
            not who or uid == who["id"] or v["peloton"] == who["id"])]
        if not candidates:
            return {"text":"Ningún interlocutor disponible en este canal."}
        uid, actor = min(candidates,key=lambda item:(item[1]["distancia"],item[0]))
        context = {k:actor[k] for k in ("nombre","peloton","estado")}
        prompt = self.cfg["persona"] + "\nPersonaje y estado: " + json.dumps(context,ensure_ascii=False)
        data = dict(model=self.cfg["model"],temperature=self.cfg["temperature"],max_tokens=self.cfg["max_tokens"],
                    stream=True,messages=[{"role":"system","content":prompt},{"role":"user","content":text}])
        req = Request(self.cfg["endpoint"],json.dumps(data).encode(),{"Content-Type":"application/json"})
        result = {"speaker_id":uid,"name":actor["nombre"]}
        waiting = time.perf_counter()
        with self.generation_lock:
            started = time.perf_counter()
            result["generation_wait_ms"] = round(1000 * (started - waiting), 3)
            line = self.generate(req, result, started)
            result["generation_ms"] = round(1000 * (time.perf_counter() - started), 3)
        result["text"] = line
        voice_index = int.from_bytes(hashlib.sha256(uid.encode()).digest()[:2],"big") % len(self.cfg["voices"])
        waiting = time.perf_counter()
        with self.synthesis_lock:
            started = time.perf_counter()
            result["tts_wait_ms"] = round(1000 * (started - waiting), 3)
            try:
                samples, rate = self.tts.create(line,voice=self.cfg["voices"][voice_index],speed=self.cfg["speed"],lang="es")
                if radio:
                    samples = sosfilt(butter(3,[300,3400],fs=rate,btype="bandpass",output="sos"),samples)
                pcm = (np.clip(samples[:rate*18],-1,1)*32767).astype("<i2").tobytes()
                result.update(pcm=base64.b64encode(pcm).decode(),rate=rate)
            except (ValueError,RuntimeError,OSError) as exc:
                result["tts_error"] = str(exc)[:160]
            result["tts_ms"] = round(1000 * (time.perf_counter() - started), 3)
        return result

    def generate(self, req, result, started):
        line = ""
        try:
            with self.client.open(req,timeout=12) as response:
                for event in response:
                    if not event.startswith(b"data:"): continue
                    payload = event[5:].strip()
                    if payload == b"[DONE]": break
                    choices = json.loads(payload).get("choices",[])
                    if not choices: continue
                    fragment = choices[0].get("delta",{}).get("content") or ""
                    if fragment.strip() and "first_token_ms" not in result:
                        result["first_token_ms"] = round(1000 * (time.perf_counter() - started), 3)
                    line += fragment
                    if re.search(r"[.!?](?:\s|$)",line): break
            line = re.split(r"(?<=[.!?])\s",line.strip(),maxsplit=1)[0][:220]
            if not line: raise ValueError("Respuesta vacía")
        except (OSError,ValueError,KeyError) as exc:
            line = "No te escuché bien, ¿podés repetir?"
            result["llm_error"] = str(exc)[:160]
        return line

