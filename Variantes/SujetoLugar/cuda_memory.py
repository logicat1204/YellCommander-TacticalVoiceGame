"""Consulta la memoria disponible del adaptador CUDA sin cargar PyTorch."""
import ctypes
import os


def free_bytes():
    if os.name != "nt":
        import torch
        return torch.cuda.mem_get_info()[0] if torch.cuda.is_available() else 0
    # El runtime CUDA devuelve la memoria libre en el dispositivo de este proceso.
    try:
        lib = ctypes.WinDLL("cudart64_12.dll")
    except OSError:
        return 0
    free, total = ctypes.c_size_t(), ctypes.c_size_t()
    error = lib.cudaMemGetInfo(ctypes.byref(free), ctypes.byref(total))
    return free.value if error == 0 else 0
