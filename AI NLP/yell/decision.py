"""Contrato de decisiones y resolución contra el catálogo vivo de Valle Alfa."""
import re

from .contract import ACTIONS, MEDICAL, PLACES, ROOT, command, matches, tokens
from .live_commands import direct_order, repair_spoken_order

LABELS = ["charla", *ACTIONS[1:]]
WEIGHTS = ROOT / "models" / "decisiones"
ZONES = {key: list(values) for key, values in PLACES.items()}
ZONES["base_aliada"] += ["casa", "nuestro cuartel"]
ZONES["centro"] += ["el medio", "por el medio"]


def features(text, aliases, here=None):
    locations = {key: list(vals) for key, vals in ZONES.items()}
    if here in locations:
        locations[here] += ["aca", "aqui", "esta posicion"]
    units, zones = matches(text, aliases), matches(text, locations)
    words = tokens(text)
    for start, end, tag in sorted([(a,b,"unidad") for a,b,_ in units] +
                                  [(a,b,"lugar") for a,b,_ in zones], reverse=True):
        words[start:end] = [tag]
    encoded = " ".join(words)
    if "?" in text or "¿" in text:
        encoded = "¿ " + encoded + " ?"
    return encoded, list(dict.fromkeys(n for _,_,n in units)), list(dict.fromkeys(n for _,_,n in zones))


def resolve(text, labels, aliases, roster, here=None, threshold=.65):
    _, units, places = features(text, aliases, here)
    def entity(key):
        return {"tipo": "soldado" if key in roster else "peloton", "id": key,
                "nombre": roster[key]["nombre"] if key in roster else key}
    addressed = entity(units[0]) if units else None
    chat = {"tipo": "charla", "interlocutor": addressed}
    action, score = labels[0]
    if action == "charla" or score < threshold or not units or len(places) != 1:
        return chat
    if "?" in text or "¿" in text or re.search(r"\b(no|nunca|jamas|si|cuando|luego|despues|pero|ni)\b", " ".join(tokens(text))):
        return chat
    if len(units) > (2 if action in MEDICAL else 1):
        return chat
    decision = {"tipo":"accion", "sujeto": addressed, "accion":action, "lugar":places[0]}
    if len(units) == 2:
        decision["objetivo"] = entity(units[1])
    return decision


class DecisionModel:
    def __init__(self, path=WEIGHTS, device=None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        if (path/"actual.txt").is_file():
            path = path/(path/"actual.txt").read_text(encoding="utf8").strip()
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
        self.net = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True).to(self.device).eval()
        self.labels = [self.net.config.id2label[i] for i in range(len(LABELS))]
        if self.labels != LABELS:
            raise ValueError("Checkpoint incompatible con el catálogo de decisiones")
        self.threshold = self.net.config.decision_threshold

    def rank(self, phrase):
        import torch
        batch = self.tokenizer(phrase, return_tensors="pt", truncation=True, max_length=80).to(self.device)
        with torch.inference_mode():
            probs = self.net(**batch).logits[0].softmax(-1).cpu().tolist()
        return sorted(zip(self.labels, probs), key=lambda pair: -pair[1])


def decide(model, text, aliases, roster, here=None, spoken=False):
    if spoken and not matches(text,aliases):
        recovered = repair_spoken_order(text,aliases,[key for key in aliases if key not in roster])
        if recovered is not None:
            text = re.sub(r"^(?:y\s+)?\w+",recovered["subject"]["name"],text.strip(),count=1,flags=re.I)
    phrase, _, _ = features(text, aliases, here)
    if model is None:
        # Preview available while the owner trains the first checkpoint.
        direct = direct_order(text, aliases)
        label = direct["action"] if direct else "charla"
        for pattern, action in ((r"unidad (?:anda a cuidar|cuidame|cuiden|que nadie pase(?: por)?) (?:el |la )?lugar", "defender"),
                                (r"unidad (?:volve|volvan|regresa) (?:a )?(?:el |la )?lugar", "retirarse"),
                                (r"unidad (?:anda|andate|movete nomas) (?:a |al )?(?:el |la )?lugar", "avanzar")):
            if re.fullmatch(pattern,phrase):
                label = action
                break
        ranking = [(label, 1.0)]
    else:
        ranking = model.rank(phrase)
    result = resolve(text, ranking, aliases, roster, here, model.threshold if model else .65)
    return result, ranking


def wire(result):
    if result["tipo"] == "charla":
        return command("charla")
    return command("orden", result["sujeto"]["id"], result["accion"], result["lugar"],
                   result.get("objetivo", {}).get("id"))

