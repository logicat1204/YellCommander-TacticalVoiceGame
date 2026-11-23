"""Dataset sintético de decisiones. La unidad de partición es la familia de paráfrasis."""
import json
from collections import defaultdict
from random import Random

from .contract import ROOT
from .decision import LABELS, features
from .phase1_data import TRAIN, VALIDATION, TEST, NON_ORDERS

DATA = ROOT / "Data" / "decisiones"
# Formas distintas de pedir cada acción en la partida. {s} es un destinatario vivo.
EXTRA = {
 "avanzar": ["{s}, andá a {z}", "{s} movete nomás a {z}", "necesito a {s} en {z}", "{s}, caé por {z}"],
 "atacar": ["{s}, metele presión a {z}", "{s} andá a atacar {z}", "{s}, quiero que tomés {z}"],
 "defender": ["{s}, cuidame {z}", "{s}, que nadie pase por {z}", "hacete cargo de cuidar {z}, {s}"],
 "retirarse": ["{s}, volvé a {z}", "pegá la vuelta hasta {z}, {s}", "{s}, replegate a {z}"],
 "reagruparse": ["{s}, júntense en {z}", "{s} reunite con los demás en {z}", "todos juntos en {z}, {s}"],
 "patrullar": ["{s}, date unas vueltas por {z}", "{s} hacé ronda por {z}", "{s}, recorré {z} de ida y vuelta"],
 "explorar": ["{s}, fijate qué hay en {z}", "{s} andá a echar un ojo a {z}", "revisame {z}, {s}"],
 "mantener_posicion": ["{s}, quedate en {z}", "{s}, de {z} nadie se mueve", "{s} esperame en {z}"],
 "cancelar_orden": ["{s}, anulá lo de {z}", "{s} cancelá la orden en {z}", "olvidá el encargo en {z}, {s}"],
 "curar": ["{s}, atendé a {t} en {z}", "{s}, dale una mano al herido en {z}", "{s}, curalo a {t} en {z}"],
 "reanimar": ["{s}, levantalo a {t} en {z}", "{s} reanimá al caído en {z}", "{s} ayudá a {t} a levantarse en {z}"],
 "charla": ["{s}, ¿vos creés que podemos ganar?", "{s}, ¿estás cuidando {z}?", "{s} no avances a {z}",
            "{s}, si mañana vamos a {z} te aviso", "{s}, defendé", "andá a {z}", "{s}, cómo va todo por {z}",
            "{s}, te acordás de {z}", "{s}, volvé", "qué frío que hace en {z}", "{s}, gracias por el aguante",
            "{s}, atacá {z} y después volvé a casa", "si aparece {t} en {z} me contás", "ayer vi a {s} en {z}"]
}
PLACES = {"flanco_izquierdo":"el flanco izquierdo", "flanco_derecho":"el lado derecho",
          "centro":"el medio","base_enemiga":"la base rival","base_aliada":"nuestra base"}
NAMES = {"train":["Alex","Juan","Ana","Rosa"],"val":["Elena","Diego"],"test":["Lucía","Mateo"]}


def build():
    forms = defaultdict(set)
    for group in (TRAIN, VALIDATION, TEST):
        for tmpl in group:
            for phrase in tmpl.forms:
                key = tmpl.action if "{z}" in phrase and "{s}" in phrase else "charla"
                forms[key].add(phrase)
    for key, phrases in EXTRA.items():
        forms[key].update(phrases)
    for group in NON_ORDERS.values():
        for phrases in group.values():
            forms["charla"].update(phrases)
    rng = Random(421)
    splits = {name: [] for name in NAMES}
    for label in LABELS:
        phrases = sorted(forms[label])
        rng.shuffle(phrases)
        train_end = min(len(phrases)-2, round(.70 * len(phrases)))
        val_end = min(len(phrases)-1, train_end + max(1,round(.15 * len(phrases))))
        for index, form in enumerate(phrases):
            split = "train" if index < train_end else "val" if index < val_end else "test"
            personal = NAMES[split]
            seen = set()
            for rep in range(10):
                zone = list(PLACES)[rep % 5]
                shown = personal[rep % len(personal)] if rep % 2 == 0 else ("Médico" if label in ("curar","reanimar") else "Bravo")
                target = next(n for n in reversed(personal) if n != shown)
                roster = {f"Alfa-{i+1}":{"nombre":n} for i,n in enumerate(personal)}
                aliases = {uid:[v["nombre"]] for uid,v in roster.items()} | {"Bravo":["bravo"],"Médico":["médico"]}
                here = zone if rep == 8 else None
                text = form.format(s=shown,t=target,z="acá" if here else PLACES[zone])
                if text in seen: continue
                seen.add(text)
                encoded, names, places = features(text,aliases,here)
                subject = next((uid for uid, info in roster.items() if info["nombre"] == shown),shown)
                patient = next(uid for uid,info in roster.items() if info["nombre"] == target)
                splits[split].append(dict(text=text, family=form, label=label, encoded=encoded,
                    subject=subject if label!="charla" else None, location=zone if label!="charla" else None,
                    target=patient if label!="charla" and "{t}" in form else None,
                    aliases=aliases, roster=roster, here=here))
    return splits


def export():
    splits = build()
    DATA.mkdir(parents=True,exist_ok=True)
    for name,rows in splits.items():
        (DATA/f"{name}.jsonl").write_text("".join(json.dumps(row,ensure_ascii=False)+"\n" for row in rows),encoding="utf8")
    return splits


def read_data():
    splits = {name:[json.loads(line) for line in (DATA/f"{name}.jsonl").read_text(encoding="utf8").splitlines() if line]
              for name in NAMES}
    seen = set()
    for name, rows in splits.items():
        families = {r["family"] for r in rows}
        if seen & families or {r["label"] for r in rows} != set(LABELS):
            raise ValueError(f"Revisa familias y cobertura de clases en {name}")
        seen.update(families)
        for row in rows:
            row["encoded"] = features(row["text"],row["aliases"],row["here"])[0]
    return splits

