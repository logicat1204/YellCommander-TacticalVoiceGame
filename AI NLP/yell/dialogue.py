"""Conversación local. El texto generado solo alimenta subtítulos y audio."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import sysconfig
from threading import Lock
import time
from urllib.request import Request, ProxyHandler, build_opener

from .contract import ROOT


class Dialogue:
    context_fields = ("nombre", "peloton", "estado")
    def __init__(self, config, defer_voice=False):
        self.cfg = json.loads(config.read_text(encoding="utf8"))
        self.client = build_opener(ProxyHandler({}))
        self.generation_lock = Lock()
        self.synthesis_lock = Lock()
        self.tts = None
        self.voice_device = "cuda"
        self.allow_cpu = defer_voice
        if not defer_voice:
            import torch  # Precalentamiento del perfil original.
            self.init_voice()
            self.tts.create("Listo.", voice=self.cfg["voices"][0], speed=self.cfg["speed"], lang="es")

    def init_voice(self):
        if os.name == "nt" and self.voice_device == "cuda":
            lib = Path(sysconfig.get_path("purelib")) / "torch/lib"
            self.cuda_dlls = os.add_dll_directory(str(lib))
            os.environ["PATH"] = str(lib) + os.pathsep + os.environ["PATH"]
        import onnxruntime as ort
        from kokoro_onnx import Kokoro
        assets = ROOT/"models/dialogo"
        options = ort.SessionOptions()
        options.log_severity_level = 3
        options.intra_op_num_threads = 3
        providers = ["CPUExecutionProvider"]
        if self.voice_device == "cuda":
            providers.insert(0, ("CUDAExecutionProvider", {"gpu_mem_limit": 1024**3,
                "cudnn_conv_use_max_workspace": "0", "cudnn_conv_algo_search": "HEURISTIC"}))
        session = ort.InferenceSession(str(assets/"kokoro.onnx"),sess_options=options, providers=providers)
        if session.get_providers()[0] != "CUDAExecutionProvider" and not self.allow_cpu:
            raise RuntimeError("Kokoro requiere ONNX Runtime GPU con CUDA y cuDNN disponibles.")
        self.voice_device = "cuda" if session.get_providers()[0] == "CUDAExecutionProvider" else "cpu"
        self.tts = Kokoro.from_session(session,str(assets/"voices.bin"))

    def reply(self, text, decision, roster, radio):
        import numpy as np
        from scipy.signal import butter, sosfilt
        who = decision.get("interlocutor") or {}
        candidates = [(uid,v) for uid,v in roster.items() if v["disponible"] and (
            not who or uid == who["id"] or v["peloton"] == who["id"])]
        if not candidates:
            return {"text":"Ningún interlocutor disponible en este canal."}
        uid, actor = min(candidates,key=lambda item:(item[1]["distancia"],item[0]))
        context = {k:actor[k] for k in self.context_fields if k in actor}
        prompt = self.cfg["persona"] + "\nPersonaje y estado: " + json.dumps(context,ensure_ascii=False)
        data = dict(model=self.cfg["model"],temperature=self.cfg["temperature"],max_tokens=self.cfg["max_tokens"],
                    stream=True,messages=[{"role":"system","content":prompt},{"role":"user","content":text}])
        if self.cfg.get("respuesta_json"):
            data["response_format"] = {"type":"json_schema","json_schema":{"name":"replica","schema":{
                "type":"object","properties":{"replica":{"type":"string"}},
                "required":["replica"],"additionalProperties":False}}}
        req = Request(self.cfg["endpoint"],json.dumps(data).encode(),{"Content-Type":"application/json"})
        result = {"speaker_id":uid,"name":actor["nombre"],"model":self.cfg["model"]}
        waiting = time.perf_counter()
        with self.generation_lock:
            started = time.perf_counter()
            result["generation_wait_ms"] = round(1000 * (started - waiting), 3)
            line = self.generate(req, result, started)
            result["generation_ms"] = round(1000 * (time.perf_counter() - started), 3)
        result["text"] = line
        voice_index = int.from_bytes(hashlib.sha256(uid.encode()).digest()[:2],"big") % len(self.cfg["voices"])
        result["voice"] = self.cfg["voices"][voice_index]
        waiting = time.perf_counter()
        with self.synthesis_lock:
            started = time.perf_counter()
            result["tts_wait_ms"] = round(1000 * (started - waiting), 3)
            try:
                def speak():
                    if self.tts is None:
                        init = time.perf_counter()
                        self.init_voice()
                        result["tts_init_ms"] = round(1000 * (time.perf_counter() - init), 3)
                    return self.tts.create(line,voice=result["voice"],speed=self.cfg["speed"],lang="es")
                try:
                    samples, rate = speak()
                except Exception as err:
                    if not self.allow_cpu or self.voice_device != "cuda":
                        raise
                    result["tts_gpu_error"] = str(err)[:180]
                    self.tts = None
                    self.voice_device = "cpu"
                if "tts_gpu_error" in result:
                    samples, rate = speak()
                if radio:
                    samples = sosfilt(butter(3,[300,3400],fs=rate,btype="bandpass",output="sos"),samples)
                pcm = (np.clip(samples[:rate*18],-1,1)*32767).astype("<i2").tobytes()
                result.update(pcm=base64.b64encode(pcm).decode(),rate=rate)
            except Exception as exc:
                result["tts_error"] = str(exc)[:160]
            result["tts_device"] = self.voice_device
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
                    if not self.cfg.get("respuesta_json") and re.search(r"[.!?](?:\s|$)",line): break
            if self.cfg.get("respuesta_json"):
                line = json.loads(line)["replica"]
            line = re.split(r"(?<=[.!?])\s",line.strip(),maxsplit=1)[0][:220]
            if not line: raise ValueError("Respuesta vacía")
        except (OSError,ValueError,KeyError) as exc:
            line = "No te escuché bien, ¿podés repetir?"
            result["llm_error"] = str(exc)[:160]
        return line

