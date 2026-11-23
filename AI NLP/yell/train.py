import argparse
import json
import random
from collections import Counter
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .contract import ACTIONS, INTENTS, ROOT, UNITS, check_grounding
from .data import audit, corpus
from .metrics import summary
from .scratch import CHECKPOINT, TAGS, WINDOW, Encoder, build_vocab, decode, encode, fit_temperature, tokenize


def materialize(rows, vocab):
    tokenized = [tokenize(row["text"], UNITS) for row in rows]
    labels = [row["label"] for row in rows]
    arrays = [
        [encode(words, vocab) for words, _ in tokenized],
        [len(words) for words, _ in tokenized],
        [INTENTS.index(x["intent"]) for x in labels],
        [ACTIONS.index(x["action"]) for x in labels],
        [int(x["subject"] is not None) for x in labels],
        [[TAGS.index(tag) for tag in row["bio"][:WINDOW]] + [-100] * max(0, WINDOW - len(row["bio"]))
         for row in rows],
    ]
    return TensorDataset(*(torch.tensor(array) for array in arrays)), [hits for _, hits in tokenized]


def weights(labels, count, max_ratio=4.0):
    sizes = Counter(labels.tolist())
    largest = max(sizes.values())
    return torch.tensor([min(max_ratio, (largest / max(1, sizes[i])) ** 0.55) for i in range(count)])


def objectives(training, device):
    sizes = [len(INTENTS), len(ACTIONS), 2, len(TAGS)]
    losses = [nn.CrossEntropyLoss(weight=weights(target.flatten(), size, max_ratio=ratio).to(device),
                                  label_smoothing=0.025)
              for target, size, ratio in zip(training.tensors[2:], sizes, (7.0, 3.0, 3.0, 3.0))]

    def calculate(outputs, targets):
        results = [loss(out.flatten(end_dim=-2), target.flatten()) for loss, out, target in zip(losses, outputs, targets)]
        return sum(value * weight for value, weight in zip(results, (1.1, 1.4, 0.4, 1.0)))

    return calculate


@torch.inference_mode()
def inspect(model, data, hits, rows, loss, device, temperatures=None):
    model.eval()
    logits, total = [], 0.0
    for ids, lengths, *targets in DataLoader(data, batch_size=64):
        outputs = model(ids.to(device), lengths.to(device))
        total += float(loss(outputs, [target.to(device) for target in targets])) * len(ids)
        logits.append(tuple(output.cpu() for output in outputs))
    outputs = [torch.cat(head) for head in zip(*logits)]
    predictions = [decode(logit, candidates, temperatures) for logit, candidates in zip(zip(*outputs), hits)]
    guarded = [check_grounding(row["text"], value, UNITS)[0] for row, value in zip(rows, predictions)]
    return total / len(data), summary([row["label"] for row in rows], guarded), outputs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--patience", type=int, default=9)
    parser.add_argument("--lr", type=float, default=0.002)
    parser.add_argument("--dropout", type=float, default=0.24)
    parser.add_argument("--seed", type=int, default=421)
    parser.add_argument("--threads", type=int, default=3)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--dataset", choices=("original", "fase1-v2"), default="original")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    device = torch.device(args.device)
    if args.dataset == "fase1-v2":
        from .phase1_data import build_phase1

        phase1 = build_phase1()
        rows = {"train": phase1["train"], "val": phase1["val"], "test": phase1["test_v1"]}
        args.checkpoint = args.checkpoint or CHECKPOINT.with_name("scratch-fase1.pt")
        default_report = "fase1/entrenamiento-a-v2.json"
    else:
        rows = corpus()
        args.checkpoint = args.checkpoint or CHECKPOINT
        default_report = "scratch.json"
    args.report = args.report or ROOT.parent / "Documentacion" / "results" / default_report
    vocab = build_vocab(rows["train"])
    data = {split: materialize(items, vocab) for split, items in rows.items()}
    training, _ = data["train"]
    validation, val_hits = data["val"]
    loader = DataLoader(training, batch_size=40, shuffle=True, generator=torch.Generator().manual_seed(args.seed))
    model = Encoder(len(vocab) + 2, args.dropout).to(device)
    loss = objectives(training, device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.012)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.55, patience=3)
    best_score, best_epoch, best_weights = -1.0, 0, None
    history = []
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for ids, lengths, *targets in loader:
            optimizer.zero_grad(set_to_none=True)
            outputs = model(ids.to(device), lengths.to(device))
            value = loss(outputs, [target.to(device) for target in targets])
            value.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(value.detach()) * len(ids)
        val_loss, val_metrics, _ = inspect(model, validation, val_hits, rows["val"], loss, device)
        score = 0.65 * val_metrics["exact_match"] + 0.35 * val_metrics["intent"]["macro_f1"]
        history.append({"epoch": epoch, "lr": optimizer.param_groups[0]["lr"], "train_loss": total / len(training),
                        "validation_loss": val_loss, "validation_exact_match": val_metrics["exact_match"],
                        "validation_intent_macro_f1": val_metrics["intent"]["macro_f1"]})
        print(json.dumps(history[-1]), flush=True)
        if score > best_score + 0.0001:
            best_score, best_epoch = score, epoch
            best_weights = {name: weight.detach().cpu().clone() for name, weight in model.state_dict().items()}
            torch.save({"weights": best_weights, "vocab": vocab}, args.checkpoint)
        scheduler.step(score)
        if epoch - best_epoch >= args.patience:
            break
    model.load_state_dict(best_weights)
    _, _, logits = inspect(model, validation, val_hits, rows["val"], loss, device)
    temperatures = [fit_temperature(logits[i], validation.tensors[2 + i]) for i in range(2)]
    torch.save({"weights": best_weights, "vocab": vocab, "temperatures": temperatures}, args.checkpoint)
    _, test, _ = inspect(model, *data["test"], rows["test"], loss, device, temperatures)
    report = {"config": {key: str(value) if isinstance(value, Path) else value for key, value in vars(args).items()},
              "pytorch": str(torch.__version__), "corpus": {k: len(v) for k, v in rows.items()},
              "sources": {k: dict(Counter(r["source"] for r in v)) for k, v in rows.items()},
              "legacy_audit": audit(), "vocabulary": len(vocab), "parameters": sum(p.numel() for p in model.parameters()),
              "best_epoch": best_epoch, "temperatures": temperatures, "history": history, "held_out_guarded": test}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Checkpoint: {args.checkpoint}\nExact Match en prueba: {test['exact_match']:.3f}")


if __name__ == "__main__":
    main()
