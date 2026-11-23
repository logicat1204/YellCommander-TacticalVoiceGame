"""Plot the measured loss curves, semantic accuracy and confusion matrices."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

from .contract import INTENTS, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=ROOT.parent / "Documentacion/results")
    args = parser.parse_args()

    def load(name):
        return json.loads((args.results / f"{name}.json").read_text(encoding="utf-8"))

    training = load("scratch")
    reports = {model: load(f"evaluation-{model}") for model in ("A", "B")}
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), layout="constrained")
    blue, orange = "#166980", "#bc5731"
    fig.suptitle("Yell Commander · evaluación textual", fontsize=17, x=.50, weight="bold")

    ax = axes[0, 0]
    epochs = training["history"]
    for key, name, color in (("train_loss", "Entrenamiento", blue), ("validation_loss", "Validación", orange)):
        ax.plot([row["epoch"] for row in epochs], [row[key] for row in epochs], label=name, color=color, lw=2)
    ax.axvline(training["best_epoch"], linestyle="--", color="#78848b", linewidth=1)
    ax.set(xlabel="Época", ylabel="Pérdida ponderada", title="A · entrenamiento de la BiGRU")
    ax.legend(frameon=False, loc="upper right")
    ax.grid(axis="y", alpha=.2)

    ax = axes[0, 1]
    selectors = ("exact_match", "order_exact_match", "incorrect_order_proposal_rate")
    indices = np.arange(len(selectors))
    for offset, model, color in ((-.18, "A", blue), (.18, "B", orange)):
        bars = ax.bar(indices + offset, [reports[model]["guarded"][key] for key in selectors], .32,
                      label=model, color=color)
        ax.bar_label(bars, labels=[f"{bar.get_height():.0%}" for bar in bars], fontsize=8, padding=2)
    ax.set(ylim=(0, 1.09), xticks=indices, xticklabels=("JSON exacto", "Orden exacta", "Orden errónea"),
           title="Prueba reservada · 172 frases")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.grid(axis="y", alpha=.2)
    ax.legend(frameon=False)

    for ax, model in zip(axes[1], reports):
        confusion = np.array(reports[model]["guarded"]["intent"]["confusion"])
        normalized = confusion / np.maximum(confusion.sum(axis=1, keepdims=True), 1)
        ax.imshow(normalized, vmin=0, vmax=1, cmap="Blues")
        for i, j in np.ndindex(confusion.shape):
            ax.text(j, i, str(confusion[i, j]), ha="center", va="center", fontsize=9,
                    color="white" if normalized[i, j] > .56 else "#15242b")
        ax.set_xticks(range(len(INTENTS)), INTENTS, rotation=22, ha="right", fontsize=9)
        ax.set_yticks(range(len(INTENTS)), INTENTS, fontsize=9)
        ax.set(xlabel="Predicción validada", ylabel="Etiqueta de referencia", title=f"{model} · matriz de intención")
    fig.savefig(args.results / "evaluacion-textual.png", dpi=185, facecolor="white")


if __name__ == "__main__":
    main()
