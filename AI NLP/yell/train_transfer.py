"""Fine-tune the final Transformer block and the task heads in PyTorch."""
import argparse
import json
import random
import time
from collections import Counter
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path

import torch
from safetensors.torch import save_file
from torch import nn
from torch.utils.data import DataLoader
from transformers import AutoModel, AutoTokenizer, __version__ as transformers_version

from .contract import ACTIONS, INTENTS, ROOT, UNITS, check_grounding
from .metrics import summary
from .phase1_data import audit_phase1, build_phase1
from .scratch import TAGS, fit_temperature
from .transfer import BASE, MODEL_C, TransferEncoder, decode_transfer, encode_text


@dataclass
class TrainingConfig:
    base: Path = BASE
    output: Path = MODEL_C
    report: Path = ROOT.parent / "Documentacion/results/fase1/entrenamiento-c.json"
    epochs: int = 8
    patience: int = 3
    batch_size: int = 32
    encoder_lr: float = 6e-5
    head_lr: float = 9e-4
    dropout: float = 0.2
    weight_decay: float = 0.015
    trainable_blocks: int = 1
    threads: int = 5
    seed: int = 421
    device: str = "auto"


def collate(batch, pad_id):
    features, labels = zip(*batch)
    length = max(len(item.ids) for item in features)
    ids = torch.full((len(batch), length), pad_id, dtype=torch.long)
    mask = torch.zeros_like(ids)
    bio = torch.full_like(ids, -100)
    categories = []
    for index, (feature, item) in enumerate(batch):
        size = len(feature.ids)
        ids[index, :size] = torch.tensor(feature.ids)
        mask[index, :size] = 1
        category = item["label"]
        categories.append((INTENTS.index(category["intent"]), ACTIONS.index(category["action"])))
        for subword, word in enumerate(feature.first_piece):
            if word is not None and word < len(item["bio"]):
                bio[index, subword] = TAGS.index(item["bio"][word])
    return ids, mask, torch.tensor(categories), bio, features, labels


def loader(tokenizer, rows, cfg, shuffle=False):
    entries = [(encode_text(tokenizer, item["text"], UNITS), item) for item in rows]
    return DataLoader(entries, batch_size=cfg.batch_size, shuffle=shuffle,
                      generator=torch.Generator().manual_seed(cfg.seed),
                      collate_fn=partial(collate, pad_id=tokenizer.pad_token_id))


def categorical_weights(values, length):
    counts = Counter(values)
    largest = max(counts.values())
    return torch.tensor([min(5.0, (largest / max(counts[index], 1)) ** 0.48) for index in range(length)])


def objective(rows, device):
    actions = categorical_weights((ACTIONS.index(item["label"]["action"]) for item in rows), len(ACTIONS))
    intents = categorical_weights((INTENTS.index(item["label"]["intent"]) for item in rows), len(INTENTS))
    tags = categorical_weights((TAGS.index(tag) for item in rows for tag in item["bio"]), len(TAGS))
    losses = [nn.CrossEntropyLoss(weight=weight.to(device), label_smoothing=0.02)
              for weight in (intents, actions, tags)]

    def calculate(predictions, categories, bio):
        intent, action, tokens = predictions
        return (losses[0](intent, categories[:, 0]) + 1.5 * losses[1](action, categories[:, 1])
                + 0.65 * losses[2](tokens.flatten(0, 1), bio.flatten()))

    return calculate


@torch.inference_mode()
def validate_epoch(model, batches, loss, device):
    model.eval()
    total, count = 0.0, 0
    proposed, expected = [], []
    logits = [[], []]
    labels = []
    for ids, mask, categories, bio, features, items in batches:
        preds = model(ids.to(device), mask.to(device))
        total += float(loss(preds, categories.to(device), bio.to(device))) * len(ids)
        count += len(ids)
        cpu = [head.cpu() for head in preds]
        for index, feature in enumerate(features):
            output = decode_transfer([head[index] for head in cpu], feature)
            proposed.append(check_grounding(items[index]["text"], output, UNITS)[0])
            expected.append(items[index]["label"])
        for head, cache in zip(cpu, logits):
            cache.append(head)
        labels.append(categories)
    return total / count, summary(expected, proposed), [torch.cat(head) for head in logits], torch.cat(labels)


def train(config):
    random.seed(config.seed)
    torch.manual_seed(config.seed)
    torch.set_num_threads(config.threads)
    device = torch.device(("cuda" if torch.cuda.is_available() else "cpu") if config.device == "auto" else config.device)
    splits = build_phase1()
    audit = audit_phase1(splits)
    tokenizer = AutoTokenizer.from_pretrained(config.base, local_files_only=True)
    pretrained = AutoModel.from_pretrained(config.base, local_files_only=True, use_safetensors=True)
    if not 1 <= config.trainable_blocks <= pretrained.config.num_hidden_layers:
        raise ValueError("Cantidad de bloques entrenables inválida")
    training = loader(tokenizer, splits["train"], config, shuffle=True)
    validation = loader(tokenizer, splits["val"], config)
    model = TransferEncoder(pretrained, config.dropout).to(device)
    model.freeze_prefix(config.trainable_blocks)
    unfrozen = {name for name, param in model.named_parameters() if param.requires_grad}
    params = dict(model.named_parameters())
    active = [param for name, param in params.items() if name in unfrozen]
    optimizer = torch.optim.AdamW([
        {"params": [params[name] for name in sorted(unfrozen) if name.startswith("encoder.")], "lr": config.encoder_lr},
        {"params": [params[name] for name in sorted(unfrozen) if not name.startswith("encoder.")], "lr": config.head_lr},
    ], weight_decay=config.weight_decay)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.55, patience=1)
    loss = objective(splits["train"], device)
    history = []
    config.output.mkdir(parents=True, exist_ok=True)
    config.report.parent.mkdir(parents=True, exist_ok=True)
    delta = config.output / "best-trainable.safetensors"
    selected_epoch, best_utility = 0, -1.0
    started = time.perf_counter()
    for epoch in range(1, config.epochs + 1):
        model.train()
        running = 0.0
        epoch_started = time.perf_counter()
        for ids, mask, labels, bio, _, _ in training:
            optimizer.zero_grad(set_to_none=True)
            preds = model(ids.to(device), mask.to(device))
            value = loss(preds, labels.to(device), bio.to(device))
            value.backward()
            nn.utils.clip_grad_norm_(active, max_norm=1.0)
            optimizer.step()
            running += float(value.detach()) * len(ids)
        val_loss, metrics, _, _ = validate_epoch(model, validation, loss, device)
        utility = 0.7 * metrics["exact_match"] + 0.3 * metrics["intent"]["macro_f1"]
        history.append({"epoch": epoch, "train_loss": running / len(splits["train"]), "val_loss": val_loss,
                        "exact_match": metrics["exact_match"], "order_exact_match": metrics["order_exact_match"],
                        "intent_macro_f1": metrics["intent"]["macro_f1"], "entity_f1": metrics["normalized_entity_f1"],
                        "seconds": round(time.perf_counter() - epoch_started, 2),
                        "encoder_lr": optimizer.param_groups[0]["lr"], "head_lr": optimizer.param_groups[1]["lr"]})
        print(json.dumps(history[-1]), flush=True)
        if utility > best_utility + 0.0001:
            selected_epoch, best_utility = epoch, utility
            save_file({name: params[name].detach().cpu().contiguous() for name in sorted(unfrozen)}, delta)
        scheduler.step(utility)
        if epoch - selected_epoch >= config.patience:
            break
    from safetensors.torch import load_file

    model.load_state_dict(load_file(delta), strict=False)
    _, best_validation, logits, y = validate_epoch(model, validation, loss, device)
    temperatures = [fit_temperature(head, y[:, idx]) for idx, head in enumerate(logits)]
    tokenizer.save_pretrained(config.output)
    model.encoder.config.save_pretrained(config.output)
    save_file({name: value.cpu().contiguous() for name, value in model.state_dict().items()},
              config.output / "transfer.safetensors")
    hyperparameters = {key: str(value) if isinstance(value, Path) else value for key, value in asdict(config).items()}
    metadata = {"format": 1, "base_model": "Geotrend/distilbert-base-es-cased@1db4091",
                "intents": INTENTS, "actions": ACTIONS, "tags": TAGS,
                "dropout": config.dropout, "temperatures": temperatures, "selected_epoch": selected_epoch,
                "trainable_parameters": sum(param.numel() for param in active),
                "parameters": sum(param.numel() for param in model.parameters()),
                "torch": str(torch.__version__), "transformers": transformers_version, "device": str(device),
                "dataset": audit, "config": hyperparameters, "training_seconds": round(time.perf_counter() - started, 2)}
    (config.output / "training.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {**metadata, "history": history, "validation": best_validation}
    config.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, default=BASE)
    parser.add_argument("--output", type=Path, default=MODEL_C)
    parser.add_argument("--report", type=Path, default=TrainingConfig.report)
    parser.add_argument("--epochs", type=int, default=TrainingConfig.epochs)
    parser.add_argument("--batch-size", type=int, default=TrainingConfig.batch_size)
    parser.add_argument("--threads", type=int, default=TrainingConfig.threads)
    parser.add_argument("--device", choices=("cpu", "cuda", "auto"), default="auto")
    train(TrainingConfig(**vars(parser.parse_args())))


if __name__ == "__main__":
    main()
