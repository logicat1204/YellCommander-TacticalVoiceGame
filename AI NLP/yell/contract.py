import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "Data" / "command-v1.schema.json").read_text(encoding="utf-8"))
INTENTS = SCHEMA["properties"]["intent"]["enum"]
ACTIONS = SCHEMA["properties"]["action"]["enum"]
LOCATIONS = SCHEMA["properties"]["location"]["anyOf"][1]["properties"]["id"]["enum"]
MEDICAL = {"curar", "reanimar"}
UNITS = {
    "Alfa": ["alfa", "alpha", "escuadron de asalto", "peloton de ataque", "los de asalto", "equipo de asalto"],
    "Bravo": ["bravo", "los de defensa", "equipo de defensa"],
    "Charlie": ["charlie", "chárli"],
    "Delta": ["delta"],
    "Eco": ["eco", "echo"],
    "Médico": ["medico", "medicos", "medico uno", "equipo medico", "sanitario", "sanitarios", "doc"],
}
PLACES = dict(zip(LOCATIONS, (
    ["flanco izquierdo", "lado izquierdo", "izquierda"],
    ["centro", "ruta central", "paso central", "flanco central", "flanco del centro", "flanco del medio",
     "medio al centro", "medio", "puente", "el cruce"],
    ["flanco derecho", "lado derecho", "derecha"],
    ["base aliada", "nuestra base", "la base", "cuartel aliado"],
    ["la base enemiga", "base enemiga", "la base enemigo", "base enemigo", "la base del enemigo", "base del enemigo",
     "la base contraria", "base contraria", "la base rival", "base rival", "la base adversaria",
     "el nucleo enemigo", "nucleo rival", "cuartel enemigo", "bunker enemigo", "bunker este", "cuartel rival"],
)))


def tokens(text):
    folded = unicodedata.normalize("NFKD", text.casefold())
    return re.findall(r"[a-z0-9]+", folded.encode("ascii", "ignore").decode("ascii"))


def matches(text, aliases):
    words = tokens(text)
    lookup = [(tokens(alias), name) for name, variants in aliases.items() for alias in [name, *variants]]
    hits = []
    cursor = 0
    while cursor < len(words):
        choices = [(len(phrase), name) for phrase, name in lookup
                   if phrase and words[cursor:cursor + len(phrase)] == phrase]
        if not choices:
            cursor += 1
            continue
        width = max(size for size, _ in choices)
        hits.extend((cursor, cursor + width, name) for size, name in sorted(set(choices)) if size == width)
        cursor += width
    return hits


def unit(name):
    if not name:
        return None
    return {"type": "soldado" if re.search(r"-[1-5]$", name) else "peloton", "name": name}


def command(intent="desconocido", subject=None, action=None, location=None, target=None, confidence=None):
    return dict(version=1, intent=intent, subject=unit(subject), action=action,
                location={"id": location} if location else None, target=unit(target), model_confidence=confidence)


def validate(value):
    """Validate the fixed v1 wire shape and its cross-field invariants."""
    if not isinstance(value, dict) or set(value) != set(SCHEMA["required"]):
        raise ValueError("Campos incompatibles con el contrato v1")
    if type(value["version"]) is not int or value["version"] != 1:
        raise ValueError("Versión de orden desconocida")
    if value["intent"] not in INTENTS or value["action"] not in ACTIONS:
        raise ValueError("Intención o acción fuera del catálogo")
    for field in ("subject", "target"):
        item = value[field]
        if item is not None and (not isinstance(item, dict) or set(item) != {"type", "name"}
                                 or item["type"] not in ("peloton", "soldado")
                                 or not isinstance(item["name"], str) or not 0 < len(item["name"].strip()) <= 64):
            raise ValueError(f"Entidad inválida en {field}")
    place = value["location"]
    if place is not None and (not isinstance(place, dict) or set(place) != {"id"} or place["id"] not in LOCATIONS):
        raise ValueError("Ubicación inválida")
    score = value["model_confidence"]
    if score is not None and (type(score) not in (int, float) or not 0 <= score <= 1):
        raise ValueError("Confianza inválida")
    if value["intent"] != "orden" and any(value[key] is not None for key in ("action", "location", "target")):
        raise ValueError("Una intención no táctica contiene campos de ejecución")
    if value["intent"] in ("charla", "desconocido") and value["subject"] is not None:
        raise ValueError("Un resultado de charla o abstención contiene un destinatario")
    if value["target"] is not None and value["action"] not in MEDICAL:
        raise ValueError("Solo las órdenes médicas aceptan un objetivo aliado")
    return value


def check_grounding(text, value, aliases):
    """Only use supported entities spoken by the player. Decline risky clause shapes."""
    validate(value)
    folded = " ".join(tokens(text))
    unit_hits = matches(text, aliases)
    named = list(dict.fromkeys(hit[2] for hit in unit_hits))
    vocative, separator, _ = text.partition(",")
    permitted_vocative = {"peloton", "equipo", "escuadron", "los", "las", "de", "del", "por", "favor",
                          "soldados", "muchachos", "tropa", "oye", "oigan", "atencion", "ahora", "bien", "ok", "eh"}
    if value["intent"] == "orden" and (
        re.search(r"\b(?:no|nunca|jamas|excepto|si|cuando|luego|despues|pero|ni|dejen de|eviten|prohibido)\b", folded)
        or re.search(r"[;?]|\b[ye]\b", text.casefold())
        or text.count(",") > 1
    ):
        return command(), "La orden contiene una negación, pregunta o más de una instrucción. Repítala por separado."
    if value["intent"] not in ("orden", "motivacion"):
        return value, ""
    places = {hit[2] for hit in matches(text, PLACES)}
    subject, target, place = value["subject"], value["target"], value["location"]
    if value["intent"] == "orden" and separator:
        prefix_tokens, prefix_units = tokens(vocative), matches(vocative, aliases)
        covered = {index for start, stop, _ in prefix_units for index in range(start, stop)}
        if any(index not in covered and word not in permitted_vocative for index, word in enumerate(prefix_tokens)):
            return command(), "Identifique un pelotón válido y emita una orden por transmisión."
    if value["action"] == "retirarse" and not place and re.search(r"\b(?:a|al|hacia|hasta|por|en)\b", folded):
        return command(), "No se reconoció el destino indicado para la retirada."
    if (subject and (not named or unit(named[0]) != subject)
            or target and (named[1:] != [target["name"]] or unit(named[1]) != target)
            or len(named) > 1 and not target
            or len(places) > 1 or place and place["id"] not in places
            or value["intent"] == "orden" and (bool(named) != bool(subject) or bool(places) != bool(place))
            or value["intent"] == "motivacion" and named and not subject):
        return command(), "Los destinatarios o destinos requieren aclaración."
    return value, ""
