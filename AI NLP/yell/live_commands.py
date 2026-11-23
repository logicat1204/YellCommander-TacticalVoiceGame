"""Órdenes breves del juego. Una coincidencia debe consumir toda la frase."""
import re

from .contract import PLACES, command, matches, tokens

MOVE = r"(?:avancen?|avanzar|avancem|adelanten|vayan?|vamos|muevanse|dirijanse|marchen)"
FORWARD = r"(?:(?:hacia |para |pa |mas )?(?:adelante|delante|el frente|al frente))"
ATTACK = r"(?:ataquen?|atacad|ataca|atacar|asalten|asaltar|destruyan|destruir|capturen|capturar)"
DEST = r"(?:(?:a|al|por|hacia|hasta|en|contra) )?(?:(?:la|el) )?zona"
ASSAULT = rf"(?:{MOVE}(?: {FORWARD})? (?:a |para |y )?)?{ATTACK}"
RULES = (
    ("atacar", rf"(?:{ASSAULT}|{MOVE} hacia el ataque|al ataque|a atacar)(?: {DEST}| a (?:los enemigos?|los rivales|las tropas enemigas))?"),
    ("avanzar", rf"(?:{MOVE}(?: {FORWARD}(?: {DEST})?| {DEST})|{FORWARD}|(?:al|a la) zona)"),
    ("defender", rf"(?:defiendan|defended|protejan|cuiden|cubran) {DEST}"),
    ("retirarse", rf"(?:retirense|retrocedan|replieguense|vuelvan|vuelve|regresen|regresa|regrese) {DEST}"),
    ("curar", rf"(?:vayan a curar|vayan a atender|curen|atiendan) {DEST}"),
    ("explorar", rf"(?:exploren|revisen|inspeccionen|echen un vistazo a) {DEST}"),
    ("patrullar", rf"(?:patrullen|hagan una ronda por|recorran de ida y vuelta) {DEST}"),
)

# Variantes observadas en las transcripciones locales. Solo se usan en el
# vocativo de una orden oral completa y con el pelotón presente en la partida.
SPOKEN_CALLSIGNS = {"brabo": "Bravo", "drabo": "Bravo", "trabo": "Bravo",
                    "rabo": "Bravo", "labo": "Bravo", "alfaba": "Alfa"}


def repair_spoken_order(text, aliases, squads):
    match = re.fullmatch(r"(?:[yY]\s+)?([\w]+)([\s,]+.+)", text.strip(), re.DOTALL)
    if not match:
        return None
    word, tail = match.groups()
    names = {name.casefold(): name for name in squads}
    name = names.get(word.casefold()) or SPOKEN_CALLSIGNS.get(word.casefold())
    if name not in squads or len(matches(text, aliases)) > 1:
        return None
    repaired = name + tail
    result = direct_order(repaired, aliases)
    if result and result["subject"] and result["subject"]["name"] == name:
        return result
    return None


def negated_order(text, aliases):
    # Keep colloquial negatives and conversation available to the model.
    positive, count = re.subn(r"\bno\s+(?=(?:ataquen?|avancen?|vayan|defiendan|regresen)\b)", "",
                              text, flags=re.IGNORECASE)
    return count == 1 and direct_order(positive, aliases) is not None


def direct_order(text, aliases):
    if any(mark in text for mark in "¿?;:") or text.count(",") > 1:
        return None
    words = tokens(text)
    units = matches(text, aliases)
    places = matches(text, PLACES)
    if len(units) > 1 or len(places) > 1:
        return None
    subject = units[0][2] if units else None
    location = places[0][2] if places else None
    spans = [(a, b, "unidad") for a, b, _ in units] + [(a, b, "zona") for a, b, _ in places]
    for start, end, marker in sorted(spans, reverse=True):
        words[start:end] = [marker]
    phrase = " ".join(words)
    phrase = re.sub(r"^(?:(?:peloton|equipo|escuadron) )?unidad ", "", phrase)
    phrase = phrase.removeprefix("por favor ").removesuffix(" por favor")
    phrase = re.sub(r"^(?:quiero que|necesito que|les ordeno que) ", "", phrase)
    # Tokens written literally must never impersonate a resolved entity.
    if ("zona" in words) != bool(places) or ("unidad" in words) != bool(units):
        return None
    for action, pattern in RULES:
        if re.fullmatch(pattern, phrase):
            return command("orden", subject, action, location or "base_enemiga")
    return None
