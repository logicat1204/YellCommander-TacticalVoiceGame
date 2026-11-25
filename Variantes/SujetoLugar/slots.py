"""Clasificación local de movimiento y extracción contra el catálogo de la partida."""
import json
import re
from pathlib import Path

import joblib
from yell.contract import matches, tokens
from yell.decision import conversational_question, features
from yell.live_commands import direct_order, repair_spoken_order

DIR = Path(__file__).resolve().parent
MOVEMENT = {"avanzar", "atacar", "defender", "explorar", "patrullar", "retirarse", "reagruparse", "mantener_posicion"}
STATIC = {"defender", "mantener_posicion"}
BLOCK = re.compile(r"\b(no|nunca|jamas|tampoco|ni|si|cuando|despues|luego|pero|ayer|ojala|dijo|pregunto|estaba|estabas|dicen|recuerdo|olvida\w*|cancel\w*|revoc\w*|anul\w*|cural\w*|curen|reanim\w*)\b")


class SlotClassifier:
    def __init__(self, posture=False):
        self.gate, self.stance, self.threshold = joblib.load(DIR / "modelos" / "intencion.joblib")
        self.posture = posture

    def classify(self, model, text, aliases, roster, here, spoken):
        phrase, subjects, places = features(text, aliases, here)
        if spoken and not subjects:
            recovered = repair_spoken_order(text, aliases, [k for k in aliases if k not in roster])
            if recovered:
                repaired = re.sub(r"^(?:y\s+)?\w+", recovered["subject"]["name"], text.strip(), count=1, flags=re.I)
                phrase, subjects, places = features(repaired, aliases, here)
        subject = subjects[0] if len(subjects) == 1 else None
        actor = ({"id": subject, "tipo": "soldado" if subject in roster else "peloton",
                  "nombre": roster[subject]["nombre"] if subject in roster else subject} if subject else None)
        chat = {"tipo": "charla", "interlocutor": actor}
        if not actor or len(places) != 1 or "?" in phrase or BLOCK.search(phrase) or conversational_question(text):
            return chat, [("charla", 1.)], "sujeto_lugar"
        # Una segunda llamada mal transcrita no debe convertir una orden plural en individual.
        prefix, sep, tail = text.partition(",")
        if sep and len(tokens(prefix)) == 1 and tokens(prefix)[0] not in (
                "oye", "bueno", "vamos", "atencion", "dale", "listo", "ahora", "che"):
            recipients = matches(tail, aliases)
            if recipients and recipients[0][0] == 0 and not matches(prefix, aliases):
                return chat, [("charla", 1.)], "sujeto_lugar"
        if re.match(r"^\w+ y unidad\b", phrase):
            return chat, [("charla", 1.)], "sujeto_lugar"
        explicit = direct_order(text, aliases)
        if explicit and explicit["action"] not in MOVEMENT:
            return chat, [("charla", 1.)], "sujeto_lugar"
        prob = 1. if explicit else float(self.gate.predict_proba([phrase])[0, 1])
        ranks = sorted([("movimiento", prob), ("charla", 1-prob)], key=lambda item: -item[1])
        if prob < self.threshold:
            return chat, ranks, "sujeto_lugar"
        location = places[0]
        # El núcleo rival de UE solo recibe daño cuando el destinatario tiene Attack.
        action = "atacar" if location == "base_enemiga" else "avanzar"
        decision = dict(tipo="accion", sujeto=actor, lugar=location, accion=action)
        if self.posture:
            static = explicit["action"] in STATIC if explicit else bool(self.stance.predict([phrase])[0])
            decision["postura"] = "mantener" if static else "avanzar"
            if static:
                decision["accion"] = "defender"
        return decision, ranks, "sujeto_lugar"


def fit():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import FeatureUnion, make_pipeline
    from sklearn.linear_model import LogisticRegression
    from yell.decision_data import read_data
    splits = read_data()
    train = {(row["encoded"], row["label"]) for row in splits["train"]}
    extras = json.loads((DIR / "frases.json").read_text(encoding="utf8"))
    reserved = {row["encoded"] for split in ("val", "test") for row in splits[split]}
    train.update((phrase, label) for label, phrases in extras.items() for phrase in phrases if phrase not in reserved)
    def train_binary(rows, positive):
        x, y = zip(*sorted((p, int(label in positive)) for p, label in rows))
        net = make_pipeline(FeatureUnion([
            ("palabras", TfidfVectorizer(ngram_range=(1, 2))),
            ("caracteres", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5))),
        ]), LogisticRegression(C=8, class_weight="balanced", random_state=421))
        return net.fit(x, y)
    gate = train_binary(train, MOVEMENT)
    stance = train_binary([(p, label) for p, label in train if label in MOVEMENT], STATIC)
    val = splits["val"]
    probs = gate.predict_proba([r["encoded"] for r in val])[:, 1]
    def utility(cut):
        return sum((1 if r["label"] in MOVEMENT else -3) if p >= cut else
                   (0 if r["label"] in MOVEMENT else 1) for r, p in zip(val, probs))
    threshold = max((.50, .55, .60, .65, .70, .75, .80), key=utility)
    target = DIR / "modelos/intencion.joblib"
    target.parent.mkdir(exist_ok=True)
    import tempfile
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as f:
        temp = Path(f.name)
    try:
        joblib.dump((gate, stance, threshold), temp, compress=3)
        temp.replace(target)
    finally:
        temp.unlink(missing_ok=True)
    return {"frases_normalizadas": len(train), "umbral_validacion": threshold}


if __name__ == "__main__":
    print(fit())
