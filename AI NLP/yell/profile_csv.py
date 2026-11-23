"""Summarize an Unreal CSV Profiler capture after the initial warm-up."""

import argparse
import csv
import json
from pathlib import Path
from statistics import median, quantiles


def summarize(path, warmup, window=None):
    fields = ("FrameTime", "GameThreadTime", "RenderThreadTime", "RHIThreadTime")
    times = {name: [] for name in fields}
    elapsed = 0.0
    index = 0
    with path.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                frame = [float(row[name]) for name in fields]
            except (ValueError, TypeError, KeyError):
                continue
            elapsed += frame[0] / 1000
            index += 1
            if index <= warmup or (window and not window[0] <= elapsed <= window[1]):
                continue
            for name, duration in zip(fields, frame):
                times[name].append(duration)
    if len(times["FrameTime"]) < 2:
        raise ValueError("La captura no tiene suficientes fotogramas válidos")
    stats = {name: {"median_ms": median(values), "p95_ms": quantiles(values, n=100, method="inclusive")[94]}
             for name, values in times.items()}
    return {"capture": path.name, "warmup_frames_excluded": warmup, "frames": len(times["FrameTime"]),
            "elapsed_window_s": window,
            "fps_from_median": 1000 / stats["FrameTime"]["median_ms"], "timings": stats}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path, nargs="+")
    parser.add_argument("--warmup", type=int, default=120)
    parser.add_argument("--window", type=float, nargs=2, metavar=("INICIO_S", "FIN_S"))
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = [summarize(path, args.warmup, args.window) for path in args.csv]
    payload = json.dumps(report, indent=2) + "\n"
    print(payload, end="")
    if args.out:
        args.out.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
