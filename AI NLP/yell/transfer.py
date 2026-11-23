"""Spanish DistilBERT adapter for the same local text contract as A and B."""
import json
from dataclasses import dataclass
from pathlib import Path

import torch
from safetensors.torch import load_file
from torch import nn
from transformers import AutoConfig, AutoModel, AutoTokenizer

from .contract import ACTIONS, INTENTS, MEDICAL, PLACES, ROOT, UNITS, command, matches, tokens
from .scratch import TAGS

BASE = ROOT / "models" / "distilbert-base-es-cased"
MODEL_C = ROOT / "models" / "transfer-c"
MAX_PIECES = 56


@dataclass
class TextFeatures:
    ids: list[int]
    first_piece: list[int | None]
    units: list
    places: list


def encode_text(tokenizer, text, aliases):
    words = tokens(text)
    units, places = matches(text, aliases), matches(text, PLACES)
    for spans, replacement in ((units, "unidad"), (places, "zona")):
        for start, stop, _ in spans:
            words[start:stop] = [replacement] * (stop - start)
    encoded = tokenizer(words or ["vacío"], is_split_into_words=True, max_length=MAX_PIECES, truncation=True)
    seen = set()
    first_piece = []
    for index in encoded.word_ids():
        first_piece.append(index if index is not None and index not in seen else None)
        seen.add(index)
    return TextFeatures(encoded["input_ids"], first_piece, units, places)


class TransferEncoder(nn.Module):
    def __init__(self, encoder, dropout=0.2):
        super().__init__()
        self.encoder = encoder
        width = encoder.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.pool_norm = nn.LayerNorm(width * 2)
        self.intent = nn.Linear(width * 2, len(INTENTS))
        self.action = nn.Linear(width * 2, len(ACTIONS))
        self.bio = nn.Linear(width, len(TAGS))

    def forward(self, ids, mask):
        states = self.encoder(input_ids=ids, attention_mask=mask).last_hidden_state
        counts = mask.sum(1, keepdim=True).clamp_min(1)
        mean = (states * mask.unsqueeze(-1)).sum(1) / counts
        features = self.dropout(self.pool_norm(torch.cat((states[:, 0], mean), dim=-1)))
        return self.intent(features), self.action(features), self.bio(self.dropout(states))

    def freeze_prefix(self, trainable_blocks):
        self.encoder.requires_grad_(False)
        for block in self.encoder.transformer.layer[-trainable_blocks:]:
            block.requires_grad_(True)

    def train(self, mode=True):
        super().train(mode)
        if mode:
            if not any(p.requires_grad for p in self.encoder.embeddings.parameters()):
                self.encoder.embeddings.eval()
            for block in self.encoder.transformer.layer:
                if not any(p.requires_grad for p in block.parameters()):
                    block.eval()
        return self


def decode_transfer(outputs, features, temperatures=None):
    intent_logits, action_logits, bio_logits = outputs
    intent = INTENTS[int(intent_logits.argmax())]
    action = ACTIONS[int(action_logits.argmax())] if intent == "orden" else None
    tags = {word: TAGS[tag] for word, tag in zip(features.first_piece, bio_logits.argmax(-1).tolist())
            if word is not None}

    def entity(candidates, role):
        found = {name for start, _, name in candidates if tags.get(start) == f"B-{role}"}
        return next(iter(found)) if len(found) == 1 else None

    subject = entity(features.units, "SUB") if intent in ("orden", "motivacion") else None
    location = entity(features.places, "LOC") if intent == "orden" else None
    target = entity(features.units, "TGT") if action in MEDICAL else None
    confidence = None
    if temperatures is not None:
        confidence = float((intent_logits / temperatures[0]).softmax(-1).max())
        if action:
            confidence = min(confidence, float((action_logits / temperatures[1]).softmax(-1).max()))
    return command(intent, subject, action, location, target, confidence)


class TransferModel:
    def __init__(self, path=MODEL_C, threads=3):
        path = Path(path)
        data = json.loads((path / "training.json").read_text(encoding="utf-8"))
        if data["format"] != 1 or data["intents"] != INTENTS or data["actions"] != ACTIONS or data["tags"] != TAGS:
            raise ValueError("Las etiquetas del checkpoint no coinciden con el contrato")
        torch.set_num_threads(threads)
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        config = AutoConfig.from_pretrained(path, local_files_only=True)
        self.encoder = TransferEncoder(AutoModel.from_config(config), data["dropout"])
        self.encoder.load_state_dict(load_file(path / "transfer.safetensors"))
        self.encoder.eval()
        self.temperatures = data["temperatures"]

    @torch.inference_mode()
    def predict(self, text, aliases=UNITS):
        feature = encode_text(self.tokenizer, text, aliases)
        ids = torch.tensor([feature.ids])
        outputs = self.encoder(ids, torch.ones_like(ids))
        return decode_transfer([head[0] for head in outputs], feature, self.temperatures)
