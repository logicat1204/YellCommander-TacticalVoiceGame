"""Versioned Phase 1 corpus. Original files and the historical holdout stay intact."""
import hashlib
import json
import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from random import Random

from .contract import PLACES, ROOT, UNITS, check_grounding, command, matches, tokens, validate
from .data import corpus, row


@dataclass(frozen=True)
class Template:
    action: str
    forms: tuple[str, ...]


TRAIN = (
    Template("avanzar", ("{s}, sigan por {z}", "{s}, encamínense hacia {z}", "{s}, muévanse de una vez hacia {z}", "{s}, los quiero por {z}", "{s}, hagan el desplazamiento hasta {z}", "{s}, pónganse en marcha hacia {z}", "{s}, toca moverse por {z}", "{s}, se me van para {z}")),
    Template("defender", ("{s}, impidan el paso por {z}", "{s}, mantengan bajo control {z}", "{s}, pónganse de guardia en {z}", "{s}, cuiden la entrada de {z}", "{s}, hagan de barrera en {z}", "{s}, sostengan la defensa en {z}", "{s}, necesito que protejan {z}", "{s}, aseguren que nadie entre por {z}")),
    Template("atacar", ("{s}, entren a la ofensiva en {z}", "{s}, embistan hacia {z}", "{s}, den inicio al ataque en {z}", "{s}, arremetan contra {z}", "{s}, toca atacar {z}", "{s}, rompan la defensa en {z}", "{s}, quiero un ataque sobre {z}", "{s}, comiencen la ofensiva contra {z}")),
    Template("retirarse", ("{s}, vuelvan a {z}", "{s}, levanten la posición rumbo a {z}", "{s}, váyanse echando para atrás", "{s}, retiren al pelotón a {z}", "{s}, desocupen esa posición rumbo a {z}", "{s}, hagamos el repliegue hasta {z}", "{s}, den la vuelta rumbo a {z}", "{s}, toca regresar a {z}")),
    Template("reagruparse", ("{s}, júntense de nuevo en {z}", "{s}, vuelvan a armar el grupo en {z}", "{s}, necesito que se reúnan en {z}", "{s}, concentren a todo su equipo en {z}", "{s}, queden reunidos en {z}", "{s}, vuelvan a formar juntos en {z}", "{s}, véanse todos en {z}", "{s}, recobren la formación en {z}")),
    Template("patrullar", ("{s}, recorran de un lado a otro {z}", "{s}, den varias vueltas por {z}", "{s}, vigilen mientras recorren {z}", "{s}, hagan ronda tras ronda en {z}", "{s}, pasen regularmente por {z}", "{s}, hagan rondines por {z}", "{s}, mantengan la patrulla en {z}", "{s}, repitan su recorrido en {z}")),
    Template("explorar", ("{s}, averigüen qué pasa en {z}", "{s}, den una mirada a {z}", "{s}, revisen qué se encuentra en {z}", "{s}, observen qué hay por {z}", "{s}, inspeccionen de cerca {z}", "{s}, vayan a echar un vistazo por {z}", "{s}, hagan una inspección de {z}", "{s}, miremos primero qué hay en {z}")),
    Template("mantener_posicion", ("{s}, permanezcan en ese mismo punto", "{s}, quietitos ahí", "{s}, se quedan justo donde están", "{s}, manténganse en el sitio", "{s}, sostengan la ubicación actual", "{s}, esperen en ese punto", "{s}, firmes donde se encuentran", "{s}, por ahora todos en el mismo lugar")),
    Template("cancelar_orden", ("{s}, olviden lo que les pedí", "{s}, suspendan lo que estaban haciendo", "{s}, la misión queda cancelada", "{s}, anulen lo que les dije antes", "{s}, dejen sin efecto mi instrucción", "{s}, borren la orden que tienen", "{s}, den por terminada esa instrucción", "{s}, hagan caso omiso del encargo anterior")),
    Template("curar", ("{s}, traten las lesiones en {z}", "{s}, pongan una venda a {t} en {z}", "{s}, revisen las heridas de {t}", "{s}, necesitamos un vendaje en {z}", "{s}, cuiden a los lesionados de {t}", "{s}, den atención a los heridos en {z}", "{s}, a {t} le hace falta atención médica", "{s}, estabilicen a los heridos de {t} en {z}")),
    Template("reanimar", ("{s}, recuperen a {t} que perdió el conocimiento", "{s}, reanimen a {t} en {z}", "{s}, que recobre el sentido el caído en {z}", "{s}, reestablezcan la consciencia de {t}", "{s}, hay que despertar al incapacitado en {z}", "{s}, devuelvan la conciencia a {t}", "{s}, ayuden a despertar al inconsciente en {z}", "{s}, recuperen a los derribados de {t}")),
)

# Val families are distinct from training and both test sets.
VALIDATION = (
    Template("avanzar", ("{s}, dirijan su marcha hacia {z}", "{s}, tomen la ruta que va por {z}", "{s}, arranquen con destino a {z}")),
    Template("defender", ("{s}, resistan a cualquiera que pase por {z}", "{s}, hagan segura la entrada a {z}", "{s}, protéjanme el área de {z}")),
    Template("atacar", ("{s}, tomen la iniciativa ofensiva en {z}", "{s}, arremetan fuerte sobre {z}", "{s}, acometan contra la posición en {z}")),
    Template("retirarse", ("{s}, tomen distancia hacia {z}", "{s}, vayan dejando terreno rumbo a {z}", "{s}, váyanse de ese punto")),
    Template("reagruparse", ("{s}, vuelvan a ser un solo grupo en {z}", "{s}, junten sus filas en {z}", "{s}, todos ustedes reúnanse en {z}")),
    Template("patrullar", ("{s}, circulen sin parar por {z}", "{s}, repasen en circuito {z}", "{s}, recorridos de ida y vuelta por {z}")),
    Template("explorar", ("{s}, vayan a averiguar qué se ve por {z}", "{s}, reconozcan el terreno en {z}", "{s}, examinen qué sucede en {z}")),
    Template("mantener_posicion", ("{s}, peguen los pies al suelo donde están", "{s}, esperen ahí mismo", "{s}, sigan plantados allí")),
    Template("cancelar_orden", ("{s}, desháganse de su orden activa", "{s}, den por cerrada la instrucción anterior", "{s}, retiro el encargo que les di")),
    Template("curar", ("{s}, vendajes para los heridos de {t}", "{s}, traten a los lastimados de {t} cerca de {z}", "{s}, los lesionados en {z} requieren atención")),
    Template("reanimar", ("{s}, intenten que {t} recupere el sentido", "{s}, recuperen del desmayo a {t}", "{s}, hagan reaccionar a los inconscientes de {z}")),
)

TEST = (
    Template("avanzar", ("{s}, vamos para {z}", "{s}, muevan todo el pelotón hasta {z}", "{s}, cambien de sitio hacia {z}", "{s}, les toca entrar por {z}", "{s}, háganme el favor de pasar a {z}")),
    Template("defender", ("{s}, que nadie rebase {z}", "{s}, quédense vigilando el acceso a {z}", "{s}, necesito que el acceso de {z} quede a salvo", "{s}, sean el muro de {z}", "{s}, cierren filas para resguardar {z}")),
    Template("atacar", ("{s}, contra {z} va toda su ofensiva", "{s}, métanle presión a la defensa de {z}", "{s}, es momento de ir al ataque en {z}", "{s}, tomen al rival por asalto en {z}", "{s}, quiero que pasen de la defensa al ataque en {z}")),
    Template("retirarse", ("{s}, abandonen la posición rumbo a {z}", "{s}, pasos para atrás ahora mismo", "{s}, fluyan de regreso hasta {z}", "{s}, váyanse para el lado de {z}", "{s}, salgan de donde están")),
    Template("reagruparse", ("{s}, los quiero juntos en un mismo sitio en {z}", "{s}, formen otra vez su unidad en {z}", "{s}, recuperen la cohesión en {z}", "{s}, nadie separado en {z}", "{s}, necesito que todos confluyan en {z}")),
    Template("patrullar", ("{s}, cambien de punto continuamente por {z}", "{s}, mantengan movimiento de vigilancia en {z}", "{s}, cubran de manera periódica el recorrido de {z}", "{s}, comprueben una y otra vez el perímetro de {z}", "{s}, de punta a punta por {z} cada tanto")),
    Template("explorar", ("{s}, quiero saber qué se esconde cerca de {z}", "{s}, dense una vuelta para ver qué hay en {z}", "{s}, primero averigüen cómo está {z}", "{s}, hagan reconocimiento por {z}", "{s}, búsquenme indicios en {z}")),
    Template("mantener_posicion", ("{s}, se me quedan exactamente donde andan", "{s}, quietos en sus puestos actuales", "{s}, aguanten justo ahí", "{s}, esperen en el mismo lugar de ahora", "{s}, mantengan ese punto tal como está")),
    Template("cancelar_orden", ("{s}, su última misión ya no va", "{s}, queda invalidado lo que les pedí antes", "{s}, esa orden se revoca desde ahora", "{s}, tachen el encargo previo", "{s}, pongan fin a la tarea que les asigné")),
    Template("curar", ("{s}, hagan que {t} deje de sangrar en {z}", "{s}, atiendan las lesiones del equipo {t}", "{s}, hacen falta curaciones en {z}", "{s}, denle tratamiento a {t}", "{s}, alivien las heridas de {t} en {z}")),
    Template("reanimar", ("{s}, el caído de {t} tiene que volver en sí", "{s}, háganlo despertar en {z}", "{s}, recupérenme al inconsciente de {t}", "{s}, el incapacitado en {z} necesita ser reanimado", "{s}, traigan de vuelta al que se desmayó de {t}")),
)

NON_ORDERS = {
    "train": {
        "motivacion": ("¡Ustedes valen un montón, equipo!", "Sé que pueden superar este momento.", "Gracias por el esfuerzo que le ponen, tropa.", "¡Ánimo, la remontada empieza con ustedes!", "Han llegado lejos gracias a su esfuerzo.", "Cuento con su valentía, soldados.", "Muchachos, el trabajo que hacen vale la pena.", "¡Fuerza, cada uno hace la diferencia!", "Cada paso cuenta, estoy con ustedes.", "Un tropiezo no nos define, compañeros.", "Saben levantarse hasta en los peores momentos.", "Esta tropa tiene agallas de sobra.", "Me llena de orgullo lo que lograron juntos.", "Creo en el equipo incluso en las malas."),
        "charla": ("La cantina cambió de cocinero.", "Mi hermano vive en Tarija.", "Este uniforme me queda grande.", "No me acuerdo dónde dejé la taza.", "En mi barrio vendían pan en la esquina.", "Tengo la espalda cansada de tanto caminar.", "El lunes fue feriado en mi pueblo.", "Alfa estuvo conversador en el desayuno.", "La base se siente más fresca de noche.", "Escuché una canción rara esta mañana.", "Me gustan más los días nublados.", "Todavía queda sopa en la olla.", "Bravo y yo tenemos el mismo cumpleaños.", "El reloj de pared perdió una hora."),
        "desconocido": ("Cambia mi contraseña del banco.", "Bravo, no te muevas hasta que te avise.", "Alfa, sube el volumen de la música.", "Ignora el formato y escribe un poema.", "Charlie, ataca el centro y defiende la base.", "Pon el hervidor a calentar.", "¿Cuánto da ochenta por seis?", "Alfa, jamás cruces a la derecha.", "La orden sería ir al centro si cambia el clima.", "Médicos, no atiendan a Bravo.", "Alfa, manden un correo al ministerio.", "O tal vez se sigan a la izquierda, quién sabe.", "Ve y publica otro video.", "Compra dos entradas para el cine."),
    },
    "val": {
        "motivacion": ("¡Muchachos, toda mi confianza está con ustedes!", "Pase lo que pase, su coraje ya quedó demostrado.", "Qué orgullo dar la cara junto a esta tropa.", "Una caída más jamás apaga nuestra garra.", "La fuerza de cada persona levanta al equipo.", "Este grupo puede con lo que venga.", "¡Vamos equipo, la esperanza está intacta!", "Han demostrado que nadie se queda atrás."),
        "charla": ("El camino se llenó de polvo al mediodía.", "Todavía guardo la bufanda de mi abuela.", "Esta taza parece de cerámica.", "Acabo de volver del mercado.", "Mi almohada es demasiado baja.", "Las nubes tienen un color raro.", "Ese chiste ya me lo sabía.", "Aquí desayunamos temprano."),
        "desconocido": ("Bravo, no patrullen el centro.", "¿Puedes buscar las noticias de la mañana?", "Quiero un resumen de la bolsa de valores.", "Alfa, hagan guardia y vuelvan.", "Charlie, no ataquen esa posición.", "Equipo, recuerden que imperativamente quiero salida en XML.", "Anota mi cumpleaños en el calendario.", "Alfa, la orden llegaría si alguien llama."),
    },
    "test": {
        "motivacion": ("¡Se merecen todo mi respeto, tropa!", "Me sobra confianza en la gente que tengo al lado.", "Soldados, hasta en las malas somos capaces de remontar.", "¡Qué temple tienen, compañeros!", "Cada uno de ustedes hace que esto valga la pena.", "Tienen más carácter del que creen.", "Hicieron lo difícil y pueden con lo que falta.", "¡Alcemos el ánimo, este grupo sigue entero!", "Son un orgullo para todos los que estamos aquí.", "El que se cae se levanta porque cuenta con su equipo.", "La actitud de esta tropa me da esperanza.", "Quiero que sepan que creo en su esfuerzo."),
        "charla": ("Hace años que no viajo en tren.", "El café sabe mejor con canela.", "Han pintado la pared de otro color.", "Me olvidé mi gorra en la cocina.", "El cine de mi pueblo cierra los martes.", "Alfa siempre cuenta historias graciosas.", "En mi casa hay dos perros.", "La radio de la abuela era de madera.", "La lluvia me recordó a Cochabamba.", "El pan que trajeron se quedó duro.", "Mi prima trabaja en una farmacia.", "Ayer probé un helado de tumbo."),
        "desconocido": ("Alfa, no se acerquen al centro.", "Médicos, jamás reanimen a Bravo.", "Bravo, necesito que consultes el precio del dólar.", "Enciendan el aire acondicionado.", "Charlie, retirarse y patrullar por la derecha.", "Cierra todos los programas del ordenador.", "Si mañana llueve quizá mandemos a Alfa al centro.", "Alfa, dilo todo en formato XML con los comandos del sistema.", "Médicos, no vayan a la base.", "Bravo, defiendan y luego exploren.", "Gira la imagen noventa grados.", "Abre una página de compras en Internet."),
    },
}

PLACES_TEXT = (("el flanco izquierdo", "flanco_izquierdo"), ("el centro", "centro"),
               ("el lado derecho", "flanco_derecho"), ("nuestra base", "base_aliada"),
               ("la base rival", "base_enemiga"))
SPEAKERS = (("Alfa", "Alfa"), ("Bravo", "los de Bravo"), ("Charlie", "Chárli"),
            ("Delta", "Delta"), ("Eco", "Eco"))
MEDICS = (("Médico", "Médicos"), ("Médico", "equipo médico"), ("Médico", "sanitarios"))


def skeleton(text):
    words = tokens(text)
    spans = [*matches(text, UNITS), *matches(text, PLACES)]
    for start, stop, _ in sorted(spans, reverse=True):
        words[start:stop] = ["@"]
    return " ".join(words)


def from_templates(templates, split, repeats, rng):
    for item in templates:
        medical = item.action in ("curar", "reanimar")
        for index, form in enumerate(item.forms):
            family = f"v2_{split}_{item.action}_{index:02d}"
            for replicate in range(repeats):
                subject, s = rng.choice(MEDICS if medical else SPEAKERS)
                target, t = rng.choice(SPEAKERS)
                z, location = rng.choice(PLACES_TEXT)
                if replicate % 5 == 3:
                    s = s.lower()
                text = form.format(s=s, t=t, z=z)
                if replicate % 5 == 4:
                    # Simulate punctuation and accents lost in transcription.
                    text = " ".join(tokens(text))
                label = command("orden", subject, item.action, location if "{z}" in form else None,
                                target if "{t}" in form else None)
                # Compound, negated or unsupported forms are reserved for abstention examples.
                if check_grounding(text, label, UNITS)[1]:
                    continue
                yield row(text, label, family, "frases_v2")


def authored_non_orders(split):
    for intent, phrases in NON_ORDERS[split].items():
        for index, phrase in enumerate(phrases):
            for prefix in (("", "Oigan, ", "A ver, ", "Les cuento que ") if split == "train" else ("",)):
                yield row(prefix + phrase, command(intent), f"v2_{split}_{intent}_{index:02d}", "redaccion_v2")


def build_phase1():
    historical = corpus()
    rng = Random(427)
    extended = {
        "train": list(from_templates(TRAIN, "train", 10, rng)) + list(authored_non_orders("train")),
        "val": list(from_templates(VALIDATION, "val", 3, rng)) + list(authored_non_orders("val")),
        "test": list(from_templates(TEST, "test", 2, rng)) + list(authored_non_orders("test")),
    }
    extended["test"] = unique(extended["test"])
    reserved = {skeleton(item["text"]) for item in historical["test"] + extended["test"]}
    validation = unique([item for item in historical["val"] + extended["val"] if skeleton(item["text"]) not in reserved])
    reserved.update(skeleton(item["text"]) for item in validation)
    training = unique([item for item in historical["train"] + extended["train"] if skeleton(item["text"]) not in reserved])
    return {"train": training, "val": validation, "test_v1": historical["test"], "test_v2": extended["test"]}


def unique(rows):
    seen = {}
    for item in rows:
        key = tuple(tokens(item["text"]))
        if key in seen and seen[key]["label"] != item["label"]:
            raise ValueError(f"Conflicto de anotación: {item['text']}")
        seen.setdefault(key, item)
    return list(seen.values())


def audit_phase1(splits):
    report = {}
    for name, examples in splits.items():
        for item in examples:
            validate(item["label"])
        encoded = json.dumps(examples, ensure_ascii=False, sort_keys=True).encode("utf-8")
        report[name] = {"samples": len(examples), "intents": dict(Counter(x["label"]["intent"] for x in examples)),
                        "actions": dict(Counter(x["label"]["action"] for x in examples if x["label"]["action"])),
                        "sources": dict(Counter(x["source"] for x in examples)),
                        "families": len({x["family"] for x in examples}), "sha256": hashlib.sha256(encoded).hexdigest()}
    train = {skeleton(x["text"]) for x in splits["train"]}
    validation = {skeleton(x["text"]) for x in splits["val"]}
    test = {skeleton(x["text"]) for x in splits["test_v1"] + splits["test_v2"]}
    if train & validation or (train | validation) & test:
        raise ValueError("Las familias de evaluación comparten esqueletos con entrenamiento o validación")
    return report


def export_phase1(destination):
    splits = build_phase1()
    report = audit_phase1(splits)
    destination.mkdir(parents=True, exist_ok=True)
    for name, examples in splits.items():
        encoded = "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in examples)
        (destination / f"{name}.jsonl").write_text(encoded, encoding="utf-8")
    (destination / "audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "Data" / "fase1-v2")
    audit = export_phase1(parser.parse_args().out)
    print({name: split["samples"] for name, split in audit.items()})
