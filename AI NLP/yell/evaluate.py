import argparse
import json
from pathlib import Path

from .contract import ACTIONS, ROOT, UNITS, command
from .data import corpus
from .inference import LocalLLM, infer
from .metrics import classification, summary


def get_model(name, checkpoint=None, llama_port=8081):
    if name == "A":
        from .scratch import CHECKPOINT, ScratchModel

        return ScratchModel(checkpoint or CHECKPOINT)
    if name == "B":
        return LocalLLM(llama_port)
    if name == "C":
        from .transfer import MODEL_C, TransferModel

        return TransferModel(checkpoint or MODEL_C)
    raise ValueError(f"Modelo no reconocido: {name}")


def evaluate_text(model, text, aliases=UNITS, threshold=0.70):
    try:
        prediction, validated, reason, ms = infer(model, text, aliases, threshold)
    except ValueError as exc:
        prediction, validated, reason, ms = None, command(), str(exc), None
    return {"prediction": prediction, "command": validated, "reason": reason, "nlp_ms": ms}


def calibration(expected, predicted):
    measurements = [
        (row["model_confidence"], int(all(expected_label[k] == row[k] for k in ("intent", "action"))))
        for expected_label, row in zip(expected, predicted) if row["model_confidence"] is not None
    ]
    if not measurements:
        return None
    count = len(measurements)
    buckets = [[] for _ in range(10)]
    for confidence, correct in measurements:
        buckets[min(int(confidence * 10), 9)].append((confidence, correct))
    point_error = sum((confidence - correct) ** 2 for confidence, correct in measurements) / count
    ece = 0.0
    histogram = []
    for index, bucket in enumerate(buckets):
        if bucket:
            confidence = sum(x[0] for x in bucket) / len(bucket)
            accuracy = sum(x[1] for x in bucket) / len(bucket)
            ece += len(bucket) * abs(confidence - accuracy) / count
            histogram.append({"min_confidence": index / 10, "count": len(bucket), "mean_confidence": confidence,
                              "accuracy": accuracy})
    return {"task": "intent_and_action", "count": count, "ece": ece, "brier": point_error, "bins": histogram}


def evaluate_rows(model, rows, name, threshold=0.70, progress=False):
    evaluate_text(model, "Alfa, avancen por el centro", threshold=threshold)
    outputs = []
    for index, row in enumerate(rows):
        result = evaluate_text(model, row["text"], threshold=threshold)
        outputs.append({"text": row["text"], "family": row["family"], "expected": row["label"],
                        "raw": result["prediction"] or command(), "guarded": result["command"],
                        "reason": result["reason"], "ms": result["nlp_ms"],
                        "invalid_response": result["nlp_ms"] is None})
        if progress and (index + 1) % 20 == 0:
            print(f"{name} {index + 1}/{len(rows)}", flush=True)
    expected = [row["label"] for row in rows]
    raw = [x["raw"] for x in outputs]
    guarded = [x["guarded"] for x in outputs]
    metrics = {}
    for stage, predictions in (("raw", raw), ("guarded", guarded)):
        times = [x["ms"] for x in outputs if x["ms"] is not None] if stage == "guarded" else ()
        metrics[stage] = summary(expected, predictions, times)
        orders = [(a["action"], p["action"]) for a, p in zip(expected, predictions) if a["intent"] == "orden"]
        metrics[stage]["action"] = classification([a for a, _ in orders], [p for _, p in orders], ACTIONS)
    return {"model": name, "threshold": threshold, "invalid_responses": sum(x["invalid_response"] for x in outputs),
            **metrics, "calibration": calibration(expected, raw), "predictions": outputs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=("A", "B", "C"), required=True)
    parser.add_argument("--llama-port", type=int, default=8081)
    parser.add_argument("--text")
    parser.add_argument("--dataset", choices=("v1", "v2"), default="v1")
    parser.add_argument("--threshold", type=float, default=0.70)
    parser.add_argument("--checkpoint", type=Path, help="Ruta del archivo A o directorio de C")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 1:
        parser.error("El umbral debe estar entre 0 y 1")
    model = get_model(args.model, args.checkpoint, args.llama_port)
    if args.text is not None:
        print(json.dumps(evaluate_text(model, args.text, threshold=args.threshold), ensure_ascii=False, indent=2))
        return
    if args.dataset == "v2":
        from .phase1_data import build_phase1

        rows = build_phase1()["test_v2"]
    else:
        rows = corpus()["test"]
    report = evaluate_rows(model, rows, args.model, args.threshold, progress=True)
    report["dataset"] = args.dataset
    default_report = (f"evaluation-{args.model}.json" if args.model in ("A", "B") and args.dataset == "v1"
                      else f"fase1/evaluation-{args.model}-{args.dataset}.json")
    dest = args.out or ROOT.parent / "Documentacion" / "results" / default_report
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    final = report["guarded"]
    print(f"{args.model} / {args.dataset}: {final['samples']} frases · JSON exacto {final['exact_match']:.1%}"
          f" · F1 intención {final['intent']['macro_f1']:.1%} · {dest}")


if __name__ == "__main__":
    main()
