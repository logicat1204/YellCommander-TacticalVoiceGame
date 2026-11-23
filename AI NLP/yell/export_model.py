"""Export the neural encoder and check numerical parity on the service batch size."""

import argparse
import json
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from .contract import ROOT, UNITS
from .scratch import CHECKPOINT, ScratchModel, encode, tokenize


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT)
    parser.add_argument("--output", type=Path, default=ROOT / "models" / "scratch.onnx")
    parser.add_argument("--report", type=Path, default=ROOT.parent / "Documentacion/results/onnx.json")
    args = parser.parse_args()
    scratch = ScratchModel(args.checkpoint)

    def inputs(text):
        words, _ = tokenize(text, UNITS)
        return torch.tensor([encode(words, scratch.vocab)]), torch.tensor([len(words)])

    tensors = inputs("Alfa, avancen por el centro")
    names = ["intent", "action", "subject", "bio"]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with torch.no_grad():
        torch.onnx.export(scratch.model, tensors, args.output, opset_version=17, dynamo=False,
                          input_names=["ids", "lengths"], output_names=names)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    runtime = ort.InferenceSession(str(args.output), providers=["CPUExecutionProvider"], sess_options=options)
    rows = []
    with torch.no_grad():
        for sentence in ("Alfa, avancen por el centro", "Médicos, atiendan a Bravo en el centro", "Buenas tardes",
                         "Alfa, no avancen por la izquierda"):
            ids, lengths = inputs(sentence)
            pytorch = scratch.model(ids, lengths)
            onnx = runtime.run(names, {"ids": ids.numpy(), "lengths": lengths.numpy()})
            errors = {name: float(np.max(np.abs(reference.numpy() - estimate)))
                      for name, reference, estimate in zip(names, pytorch, onnx)}
            if max(errors.values()) >= 1e-4:
                raise RuntimeError(f"Diferencia de exportación para {sentence}: {errors}")
            rows.append({"text": sentence, "max_absolute_logit_errors": errors})
    report = {"opset": 17, "batch_size": 1, "runtime_version": ort.__version__, "examples": rows}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exportador ONNX verificado en CPU: {args.output}")


if __name__ == "__main__":
    main()
