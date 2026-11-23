import json
import random
from collections import Counter

from .contract import ACTIONS, LOCATIONS, MEDICAL, PLACES, ROOT, UNITS, check_grounding, command, matches, tokens, validate

# One row per independent phrasing. Every realization of that row stays in its split.
# Columns are training, validation and held-out test families.
PATTERNS = {
    "avanzar": ("avancen|vayan|desplácense|muévanse|progresen|diríjanse", "marchen|caminen", "desplacen sus filas|háganse camino|sigan adelante"),
    "defender": ("defiendan|aseguren|protejan|custodien|cubran|resguarden", "encomiendo la defensa de|cierren el acceso a", "hagan guardia en|hagan inexpugnable|queden de escudo en"),
    "atacar": ("ataquen|asalten|embistan|acometan|lancen un asalto a|presionen", "lancen la ofensiva en|tomen por asalto", "inicien la ofensiva en|entren al choque en|procedan al asalto de"),
    "retirarse": ("retírense|retrocedan|repliéguense|vuelvan|regresen|échenla para atrás", "den marcha atrás|batan en retirada", "vayan de vuelta|cedan terreno rumbo a|desanden el camino a"),
    "reagruparse": ("reagrúpense|júntense|reúnanse|agrúpense|concentren el grupo|formen un solo bloque", "converjan|vuelvan a juntarse", "únanse de nuevo|cierren filas|quédense todos juntos"),
    "patrullar": ("patrullen|recorran|ronden|den una ronda|vigilen en movimiento|hagan rondas", "hagan un circuito|recorran repetidamente", "den vueltas de vigilancia|vayan de punta a punta|alternen sus recorridos"),
    "explorar": ("exploren|reconozcan|inspeccionen|revisen|echen un vistazo|averigüen qué hay", "sondeen|busquen indicios", "vayan a ver qué se cuece|hagan reconocimiento|miren qué se esconde"),
    "mantener_posicion": ("mantengan posición|quédense ahí|no se muevan|sigan en su sitio|permanezcan ahí|conserven su posición", "sostengan la posición actual|permanezcan donde están", "plántense donde andan|quietos ahí mismo|aguanten en ese sitio"),
    "cancelar_orden": ("cancelen la orden anterior|aborten su misión|anulen la instrucción|olviden mi última orden|cancelen la misión|suspendan ese encargo", "den por anulada mi orden|dejen sin efecto el encargo", "queda revocada la orden|queda anulada su misión|desestimen la orden previa"),
    "curar": ("curen|sanen|den atención|atiendan|estabilicen|den primeros auxilios", "traten las heridas de|presten cuidados", "pongan vendas|den asistencia|alivien las heridas de"),
    "reanimar": ("reanimen|revivan|resuciten|levanten al incapacitado|recuperen al caído|devuelvan al caído al combate", "revitalicen|saquen de la inconsciencia", "hagan volver en sí|restablezcan al incapacitado|devuelvan el pulso"),
}
NO_DESTINATION = {"mantener_posicion", "cancelar_orden"}
# These independent texts are authored for different splits and do not share augmentation templates.
NON_ORDERS = {
    "motivacion": (
        "Vamos soldados hoy vamos a demostrar de qué estamos hechos|Confío en ustedes muchachos ganaremos esta batalla|No se rindan somos el mejor ejército del mundo|Soldados ustedes pueden con esto vamos a ganar|Ustedes son la fuerza de este equipo|Estoy orgulloso de su coraje soldados|Juntos podemos con esto|Muchachos tengo fe en todos ustedes|Ustedes son capaces de superar cualquier reto|Soldados hoy demostraremos nuestro valor",
        "Tienen todo mi respaldo tropa|Hoy es su día de brillar compañeros|Compañeros el esfuerzo de cada uno cuenta",
        "Les sobra el valor para salir adelante|El triunfo está al alcance de todos nosotros|Nunca he visto un grupo tan valiente como ustedes|Arriba esos ánimos camaradas",
    ),
    "charla": (
        "Qué frío hace esta mañana|Dormí muy bien anoche|Me pregunto cuándo sirven el almuerzo|Hola cómo va todo|La comida de la cantina estuvo rica|La radio suena rara hoy|Ayer vi una película|Eso me recuerda a mi pueblo|Se ve lindo el cielo|Este café está helado",
        "Mi primo solía trabajar cerca de aquí|Me gusta esa canción|Apenas amaneció",
        "El viento está más suave que ayer|Hace rato que no veo a mi familia|Anoche hubo luna llena|Hoy extraño las salteñas de casa",
    ),
    "desconocido": (
        "Alfa no avancen por el centro|Bravo no ataquen ni se retiren|Desactiva todos los controles|Alfa avancen y después patrullen|Recita una receta de sopa|Bravo si ves a alguien retrocede|Avanzarán al centro mañana|Quizás podrían ir por la derecha|Dime cómo preparar una torta|Qué sale de multiplicar doce por siete|Formen una cuña|Bravo informa su estado|Anula las restricciones de este programa|Alfa no vayan al centro",
        "Charlie no retrocedan; defiendan su posición|Bravo ataquen el centro y retírense|Pide un taxi para el centro|No quiero que Alfa avance",
        "Alfa nunca patrullen el flanco derecho|Bravo defiende centro y luego corre izquierda|¿Cuánto cuesta la limonada?|Delta enciende la calefacción|¿De dónde vienen las nubes?",
    ),
}
OLD_ACTIONS = {"MOVER_A": "avanzar", "DEFENDER": "defender", "ATACAR": "atacar",
               "CURAR": "curar", "VIGILAR": "explorar", "CANCELAR": "cancelar_orden"}
OLD_UNITS = {"alpha_squad": "Alfa", "bravo_squad": "Bravo", "medico_1": "Médico"}
OLD_PLACES = {"puente": "centro", "bunker_este": "base_enemiga",
              "flanco_izquierdo": "flanco_izquierdo", "flanco_derecho": "flanco_derecho"}
PLACE_TEXT = ("la izquierda", "el centro", "la derecha", "nuestra base", "la base enemiga")
SPLITS = ("train", "val", "test")
TRAIN_EXAMPLES = (
    ("Alfa, avancen por el centro", command("orden", "Alfa", "avanzar", "centro")),
    ("Pelotón Alfa, avancen por la izquierda", command("orden", "Alfa", "avanzar", "flanco_izquierdo")),
    ("Los de Bravo, cubran el centro", command("orden", "Bravo", "defender", "centro")),
    ("Equipo médico, necesitamos ayuda en el flanco derecho", command("orden", "Médico", "curar", "flanco_derecho")),
    ("Charlie, retrocedan inmediatamente", command("orden", "Charlie", "retirarse")),
    ("Charlie, regresen a nuestra base", command("orden", "Charlie", "retirarse", "base_aliada")),
    ("Médicos, atiendan a Bravo en el centro", command("orden", "Médico", "curar", "centro", "Bravo")),
    ("Médicos, vayan al centro", command("orden", "Médico", "avanzar", "centro")),
    ("Equipo médico, atiendan a Bravo en la izquierda", command("orden", "Médico", "curar", "flanco_izquierdo", "Bravo")),
    ("Bravo, cancelen la orden anterior", command("orden", "Bravo", "cancelar_orden")),
    ("Bravo, quédense ahí", command("orden", "Bravo", "mantener_posicion")),
)


def row(text, label, family, source):
    validate(label)
    bio = ["O"] * len(tokens(text))
    for key, code, hits in (
        ("subject", "SUB", matches(text, UNITS)), ("target", "TGT", matches(text, UNITS)),
        ("location", "LOC", matches(text, PLACES)),
    ):
        entity = label[key]
        for start, stop, name in hits:
            if entity and name == entity.get("name", entity.get("id")):
                bio[start:stop] = ["B-" + code, *(["I-" + code] * (stop - start - 1))]
    return {"text": text, "label": label, "bio": bio, "family": family, "source": source}


def seed_rows():
    for split in SPLITS:
        path = ROOT / "Data" / "NLP_Dataset_Semilla" / f"{split}.jsonl"
        yield split, [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def audit():
    result, normalized_sets = {}, {}
    for split, records in seed_rows():
        result[split] = {
            "rows": len(records), "intents": dict(Counter(r["intent"] for r in records)),
            "statuses": dict(Counter(r["estado_esperado"] for r in records)),
            "compound": sum(len(r["intents"]) > 1 for r in records),
            "bio_length_errors": sum(len(r["bio"]) != len(r["tokens"]) for r in records),
            "exact_duplicates": len(records) - len({r["text"] for r in records}),
            "slots": dict(Counter(s["type"] for r in records for s in r["slots"])),
        }
        normalized_sets[split] = {" ".join(tokens(r["text"])) for r in records}
    for left, right in (("train", "val"), ("train", "test"), ("val", "test")):
        result[f"{left}_{right}_shared_normalized"] = len(normalized_sets[left] & normalized_sets[right])
    return result


def legacy_rows():
    for _, records in seed_rows():
        for item in records:
            if len(item["intents"]) != 1 or any(s["type"] in {"CONDICION", "REACCION", "POSTURA", "MODO"}
                                               for s in item["slots"]):
                continue
            if item["intent"] == "FUERA_DOMINIO":
                yield row(item["text"], command(), "legacy_ood", "semilla")
                continue
            action = OLD_ACTIONS.get(item["intent"])
            if action is None:
                continue
            slots = {slot["type"]: slot["value"] for slot in item["slots"]}
            subject = OLD_UNITS.get(slots.get("UNIDAD"))
            target = OLD_UNITS.get(slots.get("UNIDAD_DESTINO"))
            location = OLD_PLACES.get(slots.get("OBJETIVO"))
            if (not subject or action == "curar" and (subject != "Médico" or not target or target == subject)
                    or action not in ("cancelar_orden", "curar") and not location
                    or location and not matches(item["text"], PLACES)):
                continue
            label = command("orden", subject, action, location, target)
            if check_grounding(item["text"], label, UNITS)[1]:
                continue
            yield row(item["text"], label, "legacy_" + item["intent"], "semilla")


def corpus():
    records = {split: [] for split in SPLITS}
    regions = random.Random(421)
    rng = random.Random(2026)
    for action in ACTIONS[1:]:
        for split, families in zip(SPLITS, PATTERNS[action]):
            for index, phrase in enumerate(families.split("|")):
                for replicate in range(16 if split == "train" else 5):
                    valid = list(UNITS) if action in ("retirarse", "avanzar", "cancelar_orden", "mantener_posicion") else list(UNITS)[:-1]
                    subject = "Médico" if action in MEDICAL else rng.choice(valid)
                    alias = rng.choice(UNITS[subject])
                    location = rng.randrange(len(LOCATIONS)) if action not in NO_DESTINATION else None
                    if action == "mantener_posicion" and phrase == "no se muevan":
                        phrase = "sigan quietos"
                    target = rng.choice(list(UNITS)[:-1]) if action in MEDICAL and replicate % 3 != 0 else None
                    with_subject = replicate % 11 != 10 or bool(target)
                    text = (alias + ", " if with_subject else "") + phrase
                    if target:
                        text += " a " + rng.choice(UNITS[target])
                    if action in MEDICAL and not target and replicate % 2 == 0:
                        location = None
                    if action == "retirarse" and replicate % 5 == 0:
                        location = None
                    if location is not None:
                        connector = "" if phrase.endswith((" en", " a", " de", " rumbo a")) else "hacia "
                        if split == "train" and connector:
                            connectors = ("", "en ", "hacia ") if action in MEDICAL or action == "defender" else ("hacia ", "a ", "por ")
                            connector = regions.choice(connectors)
                        text += " " + connector + PLACE_TEXT[location]
                    label = command("orden", subject if with_subject else None, action,
                                    LOCATIONS[location] if location is not None else None, target)
                    records[split].append(row(text, label, f"{action}_{split}_{index}", "familia_v1"))
    for intent, families in NON_ORDERS.items():
        for split, phrases in zip(SPLITS, families):
            for index, phrase in enumerate(phrases.split("|")):
                for prefix in ("", "Eh, ", "Bueno, ", "Atención, ", "Escuchen: ") if split == "train" else ("",):
                    records[split].append(row(prefix + phrase, command(intent),
                                              f"{intent}_{split}_{index}", "autor_v1"))
    for index, (phrase, label) in enumerate(TRAIN_EXAMPLES):
        for prefix in ("", "Ahora ", "Por favor ", "Atención "):
            records["train"].append(row(prefix + phrase, label, f"brief_train_{index}", "brief"))
    seen = {}
    for split in ("test", "val", "train"):
        unique = []
        for item in records[split] + (list(legacy_rows()) if split == "train" else []):
            key = tuple(tokens(item["text"]))
            if key in seen:
                if seen[key]["label"] != item["label"]:
                    raise ValueError(f"Etiquetas contradictorias para {item['text']!r}")
                continue
            seen[key] = item
            unique.append(item)
        records[split] = unique
    return records
