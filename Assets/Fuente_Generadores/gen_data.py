# -*- coding: utf-8 -*-
import sys, os, json, csv, random, re
R = sys.argv[1]


def path(*a):
    p = os.path.join(R, *a)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


# ============================================================================ Gameplay Tags
TAGS = {
    'Comando': ['MoverA', 'Atacar', 'Defender', 'Curar', 'Seguir', 'Vigilar', 'Formar', 'CesarFuego', 'Reportar', 'Cancelar', 'Aclarar', 'AccionInvalida'],
    'Postura': ['DePie', 'Agachado', 'Tumbado'],
    'Modo': ['Normal', 'Sigilo', 'Agresivo'],
    'Condicion': ['DetectarDisparo', 'DetectarEnemigo', 'Herido', 'SinMunicion'],
    'Reaccion': ['AlertarJugador', 'AbrirFuego', 'Replegarse', 'Mantener'],
    'Formacion': ['Linea', 'Columna', 'Cuna'],
    'Unidad': ['AlphaSquad', 'BravoSquad', 'Medico1', 'Todos'],
    'Zona': ['Trinchera', 'PuertaNorte', 'FlancoIzquierdo', 'FlancoDerecho', 'Puente', 'Colina', 'TorreVigia', 'BunkerEste', 'PuntoExtraccion'],
    'Estado': ['Ok', 'Aclarar', 'AccionInvalida'],
}
lines = ['[/Script/GameplayTags.GameplayTagsSettings]', 'ImportTagsFromConfig=True', 'WarnOnInvalidTags=True',
         'ClearInvalidTags=False', 'AllowEditorTagUnloading=True', 'AllowGameTagUnloading=False', '']
for grp, vals in TAGS.items():
    for v in vals:
        lines.append(f'+GameplayTagList=(Tag="{grp}.{v}",DevComment="Operacion Voz - {grp}")')
open(path('Config', 'DefaultGameplayTags.ini'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')


def w_csv(name, header, rows):
    with open(path('Data', name), 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header); w.writerows(rows)


tg = lambda t: f'(TagName="{t}")'
# ============================================================================ DT_Comandos
w_csv('DT_Comandos.csv', ['Name', 'ComandoTag', 'RequiereObjetivo', 'RequiereUnidadDestino', 'Prioridad', 'Ejemplo'], [
    ['MOVER_A', tg('Comando.MoverA'), 'true', 'false', 5, 'Alpha, muevanse al flanco izquierdo'],
    ['ATACAR', tg('Comando.Atacar'), 'true', 'false', 5, 'Ataquen el bunker del este'],
    ['DEFENDER', tg('Comando.Defender'), 'true', 'false', 5, 'Bravo, defiendan la trinchera'],
    ['CURAR', tg('Comando.Curar'), 'false', 'true', 6, 'Medico, cura a Alpha'],
    ['SEGUIR', tg('Comando.Seguir'), 'false', 'true', 4, 'Medico, sigue a Alpha'],
    ['VIGILAR', tg('Comando.Vigilar'), 'true', 'false', 4, 'Vigila la colina y avisame si ves a alguien'],
    ['FORMAR', tg('Comando.Formar'), 'false', 'false', 3, 'Alpha, formacion en linea'],
    ['CESAR_FUEGO', tg('Comando.CesarFuego'), 'false', 'false', 10, 'Alto el fuego'],
    ['REPORTAR', tg('Comando.Reportar'), 'false', 'false', 2, 'Bravo, informe de situacion'],
    ['CANCELAR', tg('Comando.Cancelar'), 'false', 'false', 9, 'Olvida eso'],
])
# ============================================================================ DT_Unidades
w_csv('DT_Unidades.csv', ['Name', 'NombreES', 'Rol', 'Escuadron', 'NumMiembros', 'VidaMax', 'VelCaminar', 'VelCorrer', 'VelAgachado', 'AlcanceDisparo', 'DanoDisparo', 'CadenciaSeg', 'Alias'], [
    ['alpha_squad', 'Escuadron Alpha', 'asalto', 'Alpha', 3, 100, 200, 450, 120, 4500, 12, 0.18, 'alpha;alfa;equipo alpha;los de asalto;equipo de asalto'],
    ['bravo_squad', 'Escuadron Bravo', 'defensa', 'Bravo', 3, 100, 200, 450, 120, 4500, 12, 0.18, 'bravo;equipo bravo;los de defensa;equipo de defensa'],
    ['medico_1', 'Medico', 'apoyo', 'Apoyo', 1, 80, 210, 470, 120, 2500, 8, 0.35, 'medico;el medico;sanitario;doc'],
    ['enemigo_fusilero', 'Fusilero enemigo', 'enemigo', 'Enemigo', 1, 70, 190, 420, 110, 4000, 10, 0.22, ''],
])
# ============================================================================ DT_Oleadas
w_csv('DT_Oleadas.csv', ['Name', 'Oleada', 'InicioSeg', 'ZonaSpawn', 'NumFusileros', 'IntervaloSeg', 'ZonaObjetivo', 'Nota'], [
    ['O1_A', 1, 90, 'bunker_este', 4, 2.0, 'puente', 'Pequeno grupo por el puente'],
    ['O2_A', 2, 180, 'puerta_norte', 5, 1.5, 'trinchera', 'Ataque doble: puerta norte'],
    ['O2_B', 2, 190, 'flanco_derecho', 4, 1.5, 'trinchera', 'Ataque doble: flanco derecho'],
    ['O3_A', 3, 420, 'bunker_este', 6, 1.2, 'trinchera', 'Contraataque mientras alpha avanza'],
    ['O3_B', 3, 430, 'puerta_norte', 4, 1.2, 'trinchera', 'Contraataque norte'],
])
# ============================================================================ DT_Replicas
rep = [
    ('confirmacion', ['Entendido!', 'Recibido, comandante.', 'En marcha!', 'Copiado, ejecutando.', 'A la orden!', 'Cubriendo el acceso norte!', 'Flanqueando por la izquierda!', 'Posicion asegurada.']),
    ('aclaracion', ['A cual objetivo, comandante?', 'A quien se lo dice?', 'Repita el objetivo, por favor.', 'No me quedo claro, comandante.', 'Que posicion, comandante?', 'Con quien quiere que vaya?']),
    ('rechazo', ['Eso no puedo hacerlo, comandante.', 'Orden fuera de protocolo.', 'Negativo, eso no esta en mis opciones.', 'No tengo forma de hacer eso.', 'Esa posicion ya fue neutralizada.', 'Alpha esta fuera de combate.']),
    ('alerta', ['Contacto al norte!', 'Disparos, comandante!', 'Enemigos a la vista!', 'Nos estan flanqueando!', 'Contacto en el puente!', 'Movimiento en el bunker!']),
    ('estado', ['Sin novedad.', 'Posicion mantenida.', 'Necesito apoyo medico.', 'Municion baja.', 'Todo en orden por aqui.', 'Aun resistimos, comandante.', 'Objetivo a la vista.', 'Esperando ordenes.']),
    ('herido', ['Estoy herido!', 'Baja en la trinchera!', 'Me dieron, necesito un medico!', 'Soldado caido!', 'Necesitamos evacuacion!', 'Cubranme, estoy herido!']),
    ('instructor', ['Bienvenido, comandante. Mantenga la tecla V y hable.', 'Diga: Alpha, muevanse al flanco izquierdo.', 'Bien. Ahora ordene a Bravo defender la trinchera.', 'Puede hablar con naturalidad, no hace falta una frase exacta.', 'Si no esta claro, el escuadron le preguntara.', 'Pruebe una orden compuesta: cubran el puente y avisenme si ven a alguien.', 'Para cancelar, diga: olvida eso.', 'Para detener el fuego, diga: alto el fuego.', 'Muy bien. Eso es todo el entrenamiento.']),
    ('cierre', ['Objetivo destruido, buen trabajo.', 'Hemos perdido la posicion.', 'Mision cumplida, comandante.', 'Extraccion completada.']),
]
rows = []
for cat, ph in rep:
    for i, t in enumerate(ph, 1):
        rows.append([f'{cat}_{i:02d}', cat, t, ''])
w_csv('DT_Replicas.csv', ['Name', 'Categoria', 'Texto', 'Sonido'], rows)

# ============================================================================ JSON Schema
schema = {
    '$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'ComandoTactico', 'type': 'object',
    'required': ['id_comando', 'texto_original', 'acciones', 'estado'],
    'properties': {
        'id_comando': {'type': 'string'}, 'texto_original': {'type': 'string'}, 'dialogo_npc': {'type': 'string'},
        'estado': {'enum': ['OK', 'ACLARAR', 'ACCION_INVALIDA']},
        'acciones': {'type': 'array', 'items': {
            'type': 'object', 'required': ['comando'],
            'properties': {
                'comando': {'enum': ['MOVER_A', 'ATACAR', 'DEFENDER', 'CURAR', 'SEGUIR', 'VIGILAR', 'FORMAR', 'CESAR_FUEGO', 'REPORTAR', 'CANCELAR', 'ACLARAR', 'ACCION_INVALIDA']},
                'unidad': {'enum': ['alpha_squad', 'bravo_squad', 'medico_1', 'todos']},
                'unidad_destino': {'enum': ['alpha_squad', 'bravo_squad', 'medico_1']},
                'objetivo': {'enum': ['trinchera', 'puerta_norte', 'flanco_izquierdo', 'flanco_derecho', 'puente', 'colina', 'torre_vigia', 'bunker_este', 'punto_extraccion']},
                'postura': {'enum': ['de_pie', 'agachado', 'tumbado']}, 'modo': {'enum': ['normal', 'sigilo', 'agresivo']},
                'condicion': {'enum': ['detectar_disparo', 'detectar_enemigo', 'herido', 'sin_municion']},
                'reaccion': {'enum': ['ALERTAR_JUGADOR', 'ABRIR_FUEGO', 'REPLEGARSE', 'MANTENER']},
                'formacion': {'enum': ['linea', 'columna', 'cuna']}, 'confianza': {'type': 'number', 'minimum': 0, 'maximum': 1}}}}}}
json.dump(schema, open(path('Data', 'ComandoTactico.schema.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

# ============================================================================ cabecera C++ de filas
open(path('Data', 'OvDataRows.h'), 'w', encoding='utf-8').write('''// OvDataRows.h  - Estructuras de fila para importar los CSV como DataTable (UE5)
// Copiar a Source/<TuModulo>/Data/ y compilar. Al importar cada CSV elegir la estructura indicada.
#pragma once
#include "CoreMinimal.h"
#include "Engine/DataTable.h"
#include "GameplayTagContainer.h"
#include "OvDataRows.generated.h"

USTRUCT(BlueprintType) struct FZonaRow : public FTableRowBase { GENERATED_BODY()   // DT_Zonas.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FGameplayTag ZonaTag;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString NombreES;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Alias;        // separados por ';'
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Ubicacion;    // uu, Landscape en (0,0,0)
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float Radio = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Rol; };

USTRUCT(BlueprintType) struct FComandoRow : public FTableRowBase { GENERATED_BODY() // DT_Comandos.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FGameplayTag ComandoTag;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool RequiereObjetivo = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) bool RequiereUnidadDestino = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Prioridad = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Ejemplo; };

USTRUCT(BlueprintType) struct FUnidadRow : public FTableRowBase { GENERATED_BODY()  // DT_Unidades.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString NombreES;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Rol;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Escuadron;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 NumMiembros = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VidaMax = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VelCaminar = 200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VelCorrer = 450.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float VelAgachado = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float AlcanceDisparo = 4500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float DanoDisparo = 10.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float CadenciaSeg = 0.2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Alias; };

USTRUCT(BlueprintType) struct FOleadaRow : public FTableRowBase { GENERATED_BODY()  // DT_Oleadas.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 Oleada = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float InicioSeg = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName ZonaSpawn;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 NumFusileros = 1;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) float IntervaloSeg = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName ZonaObjetivo;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Nota; };

USTRUCT(BlueprintType) struct FReplicaRow : public FTableRowBase { GENERATED_BODY()  // DT_Replicas.csv
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Categoria;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FString Texto;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<USoundBase> Sonido; };
''')

# ============================================================================ dataset NLP semilla
rnd = random.Random(2026)
UN = {'alpha_squad': ['alpha', 'alfa', 'equipo alpha', 'el escuadron alpha', 'los de asalto', 'el equipo de asalto', 'escuadron de asalto'],
      'bravo_squad': ['bravo', 'equipo bravo', 'los de defensa', 'el equipo de defensa', 'escuadron bravo'],
      'medico_1': ['medico', 'el medico', 'sanitario', 'medico uno', 'doc'],
      'todos': ['todos', 'todo el equipo', 'todos los escuadrones', 'todo el mundo']}
OB = {'puerta_norte': ['la puerta norte', 'el acceso norte', 'la entrada norte', 'la puerta del norte'],
      'flanco_izquierdo': ['el flanco izquierdo', 'el lado izquierdo', 'la izquierda'], 'flanco_derecho': ['el flanco derecho', 'el lado derecho', 'la derecha'],
      'trinchera': ['la trinchera', 'la posicion defensiva', 'las trincheras'], 'puente': ['el puente', 'el paso central', 'el cruce'],
      'colina': ['la colina', 'la loma', 'la cima'], 'torre_vigia': ['la torre de vigia', 'la torre', 'la atalaya'],
      'bunker_este': ['el bunker', 'el bunker del este', 'el bunker enemigo', 'el fortin'], 'punto_extraccion': ['el punto de extraccion', 'la zona de extraccion', 'la evacuacion']}
PO = {'agachado': ['agachados', 'agachado', 'en cuclillas'], 'tumbado': ['tumbados', 'pecho tierra', 'tirados al suelo'], 'de_pie': ['de pie', 'erguidos']}
MO = {'sigilo': ['en sigilo', 'sigilosamente', 'con sigilo', 'en silencio'], 'agresivo': ['con todo', 'agresivos', 'a toda velocidad', 'sin piedad'], 'normal': ['con calma', 'con cuidado', 'tranquilos']}
CO = {'detectar_disparo': ['ves a alguien disparar', 'escuchas disparos', 'oyes un disparo'], 'detectar_enemigo': ['ves a alguien', 'ves enemigos', 'ves al enemigo', 'ves algo raro'],
      'herido': ['te hieren', 'alguien cae herido'], 'sin_municion': ['te quedas sin municion', 'se acaba la municion']}
RE = {'ALERTAR_JUGADOR': ['avisame', 'avisame de inmediato', 'dame aviso', 'reportamelo'], 'ABRIR_FUEGO': ['abre fuego', 'disparen', 'ataca'], 'REPLEGARSE': ['repliegate', 'retirense', 'retrocede']}
FO = {'linea': ['linea', 'formacion en linea', 'fila horizontal'], 'columna': ['columna', 'formacion en columna', 'fila india'], 'cuna': ['cuna', 'formacion en cuna', 'forma de v']}
SLOT = {'U': ('UNIDAD', UN), 'U2': ('UNIDAD_DESTINO', {k: v for k, v in UN.items() if k != 'todos'}), 'O': ('OBJETIVO', OB), 'P': ('POSTURA', PO), 'M': ('MODO', MO),
        'C': ('CONDICION', CO), 'R': ('REACCION', RE), 'F': ('FORMACION', FO)}
TEMPL = {
    'MOVER_A': ['{U} muevanse a {O}', '{U} avancen a {O}', '{U} vayan a {O}', 'vayan a {O}', '{U} dirijanse a {O}', '{U} avancen por {O}', '{U} muevanse a {O} {P}',
                '{U} avancen hacia {O} {M}', 'muevete a {O}', '{U} corran a {O}', '{U} desplacense a {O} {M}', '{U} posicionense en {O} {P}', '{U} avanzar a {O}'],
    'ATACAR': ['{U} ataquen {O}', 'ataquen {O} {M}', '{U} abran fuego contra {O}', 'destruyan {O}', '{U} asalten {O}', '{U} vayan y destruyan {O}', 'ataca {O}', '{U} lancen un asalto a {O} {M}', '{U} disparen a {O}'],
    'DEFENDER': ['{U} defiendan {O}', 'defiende {O}', '{U} mantengan {O}', '{U} cubran {O}', '{U} protejan {O}', '{U} resistan en {O}', 'cubre {O} {P}', '{U} aseguren {O}', 'no dejen caer {O}'],
    'CURAR': ['{U} cura a {U2}', '{U} atiende a {U2}', 'curen a {U2}', '{U} sana a {U2}', '{U} ayuda a {U2} que esta herido', 'cura a {U2}'],
    'SEGUIR': ['{U} sigue a {U2}', '{U} ve con {U2}', '{U} acompana a {U2}', '{U} pegate a {U2}', 'sigan a {U2}', '{U} vayan con {U2}'],
    'VIGILAR': ['{U} vigilen {O}', '{U} vigila {O} y {R} si {C}', 'cubre {O} y si {C} {R}', '{U} monitoreen {O}', '{U} observen {O} y {R} si {C}', 'vigila {O}', '{U} quedense atentos a {O} y {R} si {C}', 'si {C} {R}'],
    'FORMAR': ['{U} formacion en {F}', '{U} formen en {F}', '{U} pongan se en {F}', 'formen {F}', '{U} adopten {F}', '{U} en {F}'],
    'CESAR_FUEGO': ['alto el fuego', '{U} cesen el fuego', 'no disparen', 'dejen de disparar', '{U} alto el fuego', 'dejen de atacar', 'bajen las armas'],
    'REPORTAR': ['{U} informe de situacion', '{U} reporten', '{U} como estan', '{U} dame un reporte', '{U} cual es su estado', 'informen su situacion', 'reporte de estado'],
    'CANCELAR': ['cancela la orden', 'olvida eso', '{U} cancelen', 'ignora la orden anterior', '{U} detenganse', 'cancela todo', 'dejalo, olvidalo'],
}
REQ = {'MOVER_A': ['O'], 'ATACAR': ['O'], 'DEFENDER': ['O'], 'CURAR': ['U2'], 'SEGUIR': ['U2'], 'VIGILAR': ['O'], 'FORMAR': ['F']}
PRE = ['', '', '', 'oye ', 'bien ', 'comandante ', 'atencion ', 'ok ', 'ahora ', 'rapido ', 'por favor ', 'eh ']
OOD = ['vuela a la luna', 'cuentame un chiste', 'que hora es', 'canta una cancion', 'cual es la capital de francia', 'prepara un cafe', 'hazme un sandwich', 'ponte a bailar',
       'dispara a la luna', 'construyan un castillo', 'quien gano el mundial', 'hola como estas', 'llama a mi mama', 'vuelen hacia el sol', 'cambien el clima a lluvia', 'compren una pizza',
       'teletransportense al bunker', 'invoquen un dragon', 'hablen en ingles', 'apaguen el sol', 'como te llamas', 'que tiempo hace hoy', 'resuelve una ecuacion', 'abre el navegador',
       'bajen el volumen de la musica', 'tomen una foto', 'dame una receta de arroz', 'cuanto es dos mas dos', 'pon musica de rock', 'quiero ganar la loteria']


def render(tpl):
    segs, used = [], {}
    for part in re.split(r'(\{[A-Z0-9]+\})', tpl):
        if not part:
            continue
        m = re.fullmatch(r'\{([A-Z0-9]+)\}', part)
        if m:
            typ, table = SLOT[m.group(1)]
            val = rnd.choice(list(table.keys()))
            segs.append((rnd.choice(table[val]), typ, val)); used[m.group(1)] = val
        else:
            segs.append((part.strip(), None, None))
    return [s for s in segs if s[0]], used


def to_example(parts, intent_list, idx):
    toks, bio, slots = [], [], []
    for text, typ, val in parts:
        w = text.split()
        for i, t in enumerate(w):
            toks.append(t); bio.append('O' if typ is None else ('B-' if i == 0 else 'I-') + typ)
        if typ:
            slots.append({'type': typ, 'text': text, 'value': val})
    return {'id': idx, 'text': ' '.join(toks), 'tokens': toks, 'bio': bio, 'intent': intent_list[0], 'intents': intent_list, 'slots': slots}


def one(intent, drop=False):
    tpl = rnd.choice(TEMPL[intent])
    if drop and intent in REQ:
        tpl = re.sub(r'\s*\{(%s)\}' % '|'.join(REQ[intent]), '', tpl)
    parts, used = render(tpl)
    pre = rnd.choice(PRE).strip()
    if pre:
        parts = [(pre, None, None)] + parts
    miss = [k for k in REQ.get(intent, []) if k not in used]
    return parts, miss


data = []; seen = set(); n = 0
for intent in TEMPL:
    cnt = 0
    while cnt < 115:
        drop = rnd.random() < 0.12
        parts, miss = one(intent, drop)
        ex = to_example(parts, [intent], n)
        if ex['text'] in seen:
            continue
        seen.add(ex['text']); ex['faltan'] = [SLOT[m][0] for m in miss]; ex['estado_esperado'] = 'ACLARAR' if miss else 'OK'
        data.append(ex); n += 1; cnt += 1
cnt = 0
while cnt < 140:
    t = rnd.choice(OOD); pre = rnd.choice(PRE).strip()
    t = (pre + ' ' + t).strip() if rnd.random() < .5 else t
    if rnd.random() < .5:
        parts_ = [(t, None, None)]
    else:
        parts_ = [(t + ' ' + rnd.choice(list(rnd.choice(list(UN.values()))))), None, None],
        parts_ = [(t, None, None)]
    ex = to_example(parts_, ['FUERA_DOMINIO'], n)
    if ex['text'] in seen:
        t = t + ' ' + rnd.choice(['por favor', 'ahora', 'ya', 'rapido', 'comandante'])
        ex = to_example([(t, None, None)], ['FUERA_DOMINIO'], n)
        if ex['text'] in seen:
            continue
    seen.add(ex['text']); ex['faltan'] = []; ex['estado_esperado'] = 'ACCION_INVALIDA'
    data.append(ex); n += 1; cnt += 1
simple = [e for e in data if e['intent'] in TEMPL and e['estado_esperado'] == 'OK' and e['intent'] not in ('CESAR_FUEGO', 'CANCELAR')]
cnt = 0
while cnt < 220:
    a, b = rnd.sample(simple, 2)
    conn = rnd.choice(['y', 'y luego', 'y despues', 'y mientras tanto', 'luego'])
    toks = a['tokens'] + [conn] + b['tokens']
    bio = a['bio'] + ['O'] * len(conn.split()) + b['bio']
    text = ' '.join(toks)
    if text in seen or a['intent'] == b['intent'] and a['text'] == b['text']:
        continue
    seen.add(text)
    data.append({'id': n, 'text': text, 'tokens': toks, 'bio': bio, 'intent': a['intent'], 'intents': [a['intent'], b['intent']],
                 'slots': a['slots'] + b['slots'], 'faltan': [], 'estado_esperado': 'OK'})
    n += 1; cnt += 1
rnd.shuffle(data)
by = {}
for e in data:
    by.setdefault(e['intent'], []).append(e)
sp = {'train': [], 'val': [], 'test': []}
for k, v in by.items():
    a, b = int(len(v) * .70), int(len(v) * .85)
    sp['train'] += v[:a]; sp['val'] += v[a:b]; sp['test'] += v[b:]
for k, v in sp.items():
    with open(path('Data', 'NLP_Dataset_Semilla', f'{k}.jsonl'), 'w', encoding='utf-8') as f:
        for e in v:
            f.write(json.dumps(e, ensure_ascii=False) + '\n')
json.dump({'intenciones': list(TEMPL) + ['FUERA_DOMINIO'], 'entidades': sorted({v[0] for v in SLOT.values()}),
           'ejemplos': {k: len(v) for k, v in sp.items()}, 'total': len(data),
           'nota': 'Semilla generada por plantillas: sirve para arrancar el entrenamiento. Debe ampliarse con frases escritas por humanos y transcripciones reales de Whisper (acento boliviano, ruido) antes de medir el rendimiento.'},
          open(path('Data', 'NLP_Dataset_Semilla', 'LEEME_dataset.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('datos OK  dataset:', len(data), {k: len(v) for k, v in sp.items()})
