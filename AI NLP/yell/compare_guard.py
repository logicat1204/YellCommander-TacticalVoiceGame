"""Reapply the in-game agreement policy to the paired model evaluation reports."""

import argparse
import json
from pathlib import Path

from .contract import ROOT, command
from .metrics import summary
from .service import check_live_agreement


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=ROOT.parent / "Documentacion" / "results")
    args = parser.parse_args()
    data = [json.loads((args.results / f"evaluation-{key}.json").read_text(encoding="utf-8"))["predictions"]
            for key in ("A", "B")]
    if [(r["text"], r["expected"]) for r in data[0]] != [(r["text"], r["expected"]) for r in data[1]]:
        raise ValueError("Ambos informes deben evaluar las mismas frases y etiquetas")
    expected, predictions = [], []
    rejected = 0
    for a, b in zip(*data):
        proposal = b["guarded"]
        allowed = check_live_agreement(proposal, a["guarded"])
        expected.append(b["expected"])
        predictions.append(proposal if allowed else command())
        rejected += not allowed
    report = summary(expected, predictions)
    report["rejected_by_agreement"] = rejected
    destination = args.results / "evaluation-B-acuerdo.json"
    destination.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(destination)


if __name__ == "__main__":
    main()
