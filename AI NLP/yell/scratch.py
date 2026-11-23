import math
from collections import Counter

import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence, pad_packed_sequence

from .contract import ACTIONS, INTENTS, PLACES, ROOT, UNITS, command, matches, tokens

CHECKPOINT = ROOT / "models" / "scratch.pt"
TAGS = ["O", "B-SUB", "I-SUB", "B-LOC", "I-LOC", "B-TGT", "I-TGT"]
WINDOW = 48
PIECES = 16


def tokenize(text, aliases):
    words = tokens(text)
    entities = matches(text, aliases), matches(text, PLACES)
    for hits, marker in zip(entities, ("unit", "place")):
        for first, end, _ in hits:
            words[first:end] = [f"<{marker}>", *([f"<{marker}+>"] * (end - first - 1))]
    return words[:WINDOW] or ["<empty>"], entities


def pieces(word):
    marked = "^" + word + "$"
    if word.startswith("<"):
        return [word]
    chars = [f"#{marked[i:i + 3]}" for i in range(len(marked) - 2)]
    return [word, *chars[:7], *chars[-8:]] if len(chars) > 15 else [word, *chars]


def build_vocab(rows):
    counts = Counter(fragment for row in rows for word in tokenize(row["text"], UNITS)[0]
                     for fragment in pieces(word))
    return {fragment: index + 2 for index, fragment in enumerate(sorted(counts))}


def encode(words, vocab):
    ids = [[vocab.get(fragment, 1) for fragment in pieces(word)] for word in words]
    return [line + [0] * (PIECES - len(line)) for line in ids] + [[0] * PIECES] * (WINDOW - len(ids))


class Encoder(nn.Module):
    def __init__(self, vocabulary, dropout=0.24):
        super().__init__()
        self.embedding = nn.Embedding(vocabulary, 48, padding_idx=0)
        self.gru = nn.GRU(48, 56, batch_first=True, bidirectional=True)
        self.dropout = nn.Dropout(dropout)
        self.intent = nn.Linear(112, len(INTENTS))
        self.action = nn.Linear(112, len(ACTIONS))
        self.subject = nn.Linear(112, 2)
        self.bio = nn.Linear(112, len(TAGS))

    def forward(self, ids, lengths):
        embedded = self.embedding(ids).sum(dim=2) / (ids.ne(0).sum(dim=2, keepdim=True).clamp_min(1).sqrt())
        packed = pack_padded_sequence(self.dropout(embedded), lengths.cpu(), batch_first=True,
                                      enforce_sorted=False)
        hidden, _ = self.gru(packed)
        hidden, _ = pad_packed_sequence(hidden, batch_first=True, total_length=ids.size(1))
        mask = torch.arange(ids.size(1), device=ids.device).unsqueeze(0) < lengths.unsqueeze(1)
        pooled = self.dropout(hidden.masked_fill(~mask.unsqueeze(-1), -1e4).amax(dim=1))
        return self.intent(pooled), self.action(pooled), self.subject(pooled), self.bio(self.dropout(hidden))


def decode(outputs, hits, temperatures=None):
    intent_logits, action_logits, subject_logits, bio = outputs
    intent = INTENTS[int(intent_logits.argmax())]
    action = ACTIONS[int(action_logits.argmax())] if intent == "orden" else None
    has_subject = int(subject_logits.argmax()) == 1
    tags = bio.argmax(dim=-1).tolist()
    units, places = hits

    def extract(candidates, role):
        accepted = {name for start, stop, name in candidates if stop <= WINDOW
                    and tags[start] == TAGS.index("B-" + role)}
        return next(iter(accepted)) if len(accepted) == 1 else None

    subject = extract(units, "SUB") if has_subject and intent in ("orden", "motivacion") else None
    target = extract(units, "TGT") if action in ("curar", "reanimar") else None
    place = extract(places, "LOC") if action else None
    confidence = None
    if temperatures is not None:
        confidence = float((intent_logits / temperatures[0]).softmax(dim=-1).max())
        if action is not None:
            confidence = min(confidence, float((action_logits / temperatures[1]).softmax(dim=-1).max()))
    return command(intent, subject, action, place, target, None if confidence is None else round(confidence, 5))


class ScratchModel:
    def __init__(self, checkpoint=CHECKPOINT):
        data = torch.load(checkpoint, map_location="cpu", weights_only=True)
        self.vocab = data["vocab"]
        self.temperatures = data.get("temperatures")
        self.model = Encoder(len(self.vocab) + 2)
        self.model.load_state_dict(data["weights"])
        self.model.eval()
        torch.set_num_threads(min(torch.get_num_threads(), 2))

    @torch.inference_mode()
    def predict(self, text, aliases):
        words, hits = tokenize(text, aliases)
        batch = torch.tensor([encode(words, self.vocab)])
        outputs = self.model(batch, torch.tensor([len(words)]))
        return decode([item[0] for item in outputs], hits, self.temperatures)


def fit_temperature(logits, targets):
    # A short grid search keeps calibration independent of the test distribution.
    temperatures = [math.exp(x / 10) for x in range(-12, 28)]
    return min(temperatures, key=lambda t: float(nn.functional.cross_entropy(logits / t, targets)))
