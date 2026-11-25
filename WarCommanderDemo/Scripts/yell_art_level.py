"""Build /Game/Yell/Art/Levels/ValleAlfa_Presentacion.

The gameplay arena is generated in C++ at BeginPlay, so this level is a
*visual copy*: every arena piece is placed at the exact coordinates used by
YellArena.cpp, in two mutually exclusive folders:

  Arena_Proxy  -> flat coloured blocks, i.e. the "before" look
  Arena_Art    -> the imported Operacion Voz meshes and materials

Folders Art_Showcase_* hold the asset galleries outside the arena footprint.
Cameras are named so the capture script can find them.

Run headless with -run=pythonscript.
"""
import json
import math
import os
import traceback

import unreal

ART = "/Game/Yell/Art"
LEVEL = ART + "/Levels/ValleAlfa_Presentacion"
PROJECT = unreal.Paths.project_dir()
REPORT = os.path.join(PROJECT, "Saved", "yell_art_level.txt")
MANIFEST = os.path.join(PROJECT, "Saved", "yell_level_manifest.json")

LINES = []
MANIFEST_DATA = []

AES = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

BASE_X = 3450.0
LANE = 1440.0
PAD_TOP = 250.0


def log(text):
    LINES.append(str(text))


def load(path):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        log("MISSING ASSET " + path)
    return asset


def material(path):
    return load(ART + "/Materials/Instances/" + path)


CUBE = "/Engine/BasicShapes/Cube.Cube"
CYL = "/Engine/BasicShapes/Cylinder.Cylinder"
PLANE = "/Engine/BasicShapes/Plane.Plane"


def record(label, kind, loc, rot, scale, folder):
    MANIFEST_DATA.append({
        "label": label,
        "kind": kind,
        "location": [round(loc[0], 2), round(loc[1], 2), round(loc[2], 2)],
        "rotation": [round(rot[0], 2), round(rot[1], 2), round(rot[2], 2)],
        "scale": [round(scale[0], 4), round(scale[1], 4), round(scale[2], 4)],
        "folder": folder,
    })


def spawn(label, mesh, loc, rot=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0),
          mat=None, folder="Arena_Art", collision=False):
    if isinstance(rot, unreal.Rotator):
        rotator = rot
        rot_tuple = (rot.pitch, rot.yaw, rot.roll)
    else:
        rotator = unreal.Rotator(pitch=rot[0], yaw=rot[1], roll=rot[2])
        rot_tuple = rot
    actor = AES.spawn_actor_from_class(unreal.StaticMeshActor,
                                       unreal.Vector(loc[0], loc[1], loc[2]),
                                       rotator)
    actor.set_actor_label(label)
    actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
    try:
        actor.set_folder_path(folder)
    except Exception:
        pass
    comp = actor.static_mesh_component
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    comp.set_static_mesh(mesh)
    if mat is not None:
        comp.set_material(0, mat)
    if not collision:
        comp.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    record(label, mesh.get_name(), loc, rot_tuple, scale, folder)
    return actor


def block(label, size, loc, mat, folder="Arena_Art", rot=(0.0, 0.0, 0.0), mesh=None):
    """Mirror of AYellBattle::Block(): size in cm, pivot at the block centre."""
    scale = (size[0] / 100.0, size[1] / 100.0, size[2] / 100.0)
    return spawn(label, mesh or load(CUBE), loc, rot, scale, mat, folder)


def sign(label, text, loc, color, size, face_to=None, folder="Arena_Art"):
    """TextRenderActor whose readable side points at face_to.

    A TextRenderActor with rotation 0 reads along +Y and faces +X, so the yaw
    must point its +X at the viewer.  face_to may also be a legacy yaw number
    (0 = readable from -X).
    """
    if isinstance(face_to, (int, float)):
        yaw = float(face_to) + 180.0
    elif face_to is None:
        yaw = 180.0
    else:
        yaw = math.degrees(math.atan2(face_to[1] - loc[1], face_to[0] - loc[0]))
    actor = AES.spawn_actor_from_class(unreal.TextRenderActor,
                                       unreal.Vector(loc[0], loc[1], loc[2]),
                                       unreal.Rotator(pitch=0.0, yaw=yaw, roll=0.0))
    actor.set_actor_label(label)
    try:
        actor.set_folder_path(folder)
    except Exception:
        pass
    comp = actor.get_component_by_class(unreal.TextRenderComponent)
    comp.set_editor_property("text", text)
    comp.set_editor_property("text_render_color", color)
    comp.set_editor_property("world_size", size)
    try:
        comp.set_editor_property("horizontal_alignment",
                                 unreal.HorizontalTextAligment.EHTA_CENTER)
    except Exception:
        pass
    try:
        comp.set_editor_property("vertical_alignment",
                                 unreal.VerticalTextAligment.EVRTA_TEXT_CENTER)
    except Exception:
        pass
    record(label, "TextRender", loc, (0.0, yaw, 0.0), (1.0, 1.0, 1.0), folder)
    return actor


def camera(label, loc, look_at=None, rot=None, fov=75.0):
    if rot is None:
        rot = unreal.MathLibrary.find_look_at_rotation(
            unreal.Vector(loc[0], loc[1], loc[2]),
            unreal.Vector(look_at[0], look_at[1], look_at[2]))
    actor = AES.spawn_actor_from_class(unreal.CameraActor,
                                       unreal.Vector(loc[0], loc[1], loc[2]), rot)
    actor.set_actor_label(label)
    try:
        actor.set_folder_path("Camaras")
    except Exception:
        pass
    comp = actor.get_component_by_class(unreal.CameraComponent)
    comp.set_editor_property("field_of_view", fov)
    record(label, "Camera", loc, (rot.pitch, rot.yaw, rot.roll), (1.0, 1.0, 1.0), "Camaras")
    return actor


# ------------------------------------------------------------------ layout

LANE_Y = (-LANE, 0.0, LANE)
COVER_Y = {}
for lane_y in LANE_Y:
    for index in range(5):
        COVER_Y[(lane_y, index)] = lane_y + (-280.0 if index % 2 == 0 else 280.0)


def build_proxy():
    f = "Arena_Proxy"
    turf = material("Teams/MI_Proxy_Cesped")
    road = material("Teams/MI_Proxy_Camino")
    wall = material("Teams/MI_Proxy_Muro")
    ally = material("Teams/MI_Proxy_Aliado")
    rival = material("Teams/MI_Proxy_Rival")
    gold = material("Teams/MI_Proxy_Oro")

    block("Proxy_Suelo", (8500, 4950, 180), (0, 0, -90), turf, f)
    for side in (-1.0, 1.0):
        block("Proxy_Muro_Y%d" % side, (8420, 100, 280), (0, side * 2420, 140), wall, f)
        block("Proxy_Muro_X%d" % side, (100, 4810, 280), (side * 4150, 0, 140), wall, f)
        block("Proxy_Pista_X%d" % side, (1220, 4770, 4), (side * 2900, 0, 2), road, f)
        block("Proxy_Pista_C%d" % side, (250, 4600, 4), (side * 980, 0, 2), road, f)
    for lane_index, y in enumerate(LANE_Y):
        block("Proxy_Carril_%d" % lane_index, (7900, 765, 4), (0, y, 2), road, f)
        for side in (-1.0, 1.0):
            block("Proxy_Borde_%d_%d" % (lane_index, side), (7900, 22, 5),
                  (0, y + side * 400, 4), gold, f)
            block("Proxy_Poste_%d_%d" % (lane_index, side), (105, 152, 120),
                  (-1420, y + side * 430, 60), wall, f)
            block("Proxy_Poste_%d_%d_b" % (lane_index, side), (105, 152, 120),
                  (1420, y + side * 430, 60), wall, f)
        for index in range(5):
            block("Proxy_Cobertura_%d_%d" % (lane_index, index), (175, 235, 158),
                  ((index - 2) * 520.0, COVER_Y[(y, index)], 79), wall, f)
    for y in (-720.0, 720.0):
        block("Proxy_Barricada_%d" % y, (1360, 206, 320), (0, y, 160), wall, f)
        block("Proxy_Barricada_Tapa_%d" % y, (1450, 250, 35), (0, y, 320), gold, f)
    for team in (0, 1):
        tint = ally if team == 0 else rival
        core = (BASE_X * (-1 if team == 0 else 1), 0.0, 150.0)
        block("Proxy_Base_%d" % team, (600, 700, 66),
              (core[0], core[1], core[2] - 117), wall, f)
        block("Proxy_Nucleo_%d" % team, (360, 470, 220), core, tint, f)
        block("Proxy_Nucleo_Tapa_%d" % team, (330, 440, 38),
              (core[0], core[1], core[2] + 130), gold, f)
        block("Proxy_Nucleo_Poste_%d" % team, (42, 42, 170),
              (core[0], core[1], core[2] + 220), tint, f, mesh=load(CYL))
        terminal_x = -3040.0 if team == 0 else 3040.0
        block("Proxy_Terminal_%d" % team, (95, 135, 120),
              (terminal_x, -700, 60), tint, f)
        block("Proxy_Terminal_Tapa_%d" % team, (110, 145, 18),
              (terminal_x, -700, 128), gold, f)
    for lane_index, (y, name) in enumerate(zip(LANE_Y, ("IZQUIERDA", "CENTRO", "DERECHA"))):
        sign("Proxy_Rotulo_%d" % lane_index, name, (-1490, y, 235),
             unreal.Color(194, 120, 26, 255), 65.0, 0.0, f)
    sign("Proxy_Rotulo_Aliada", "BASE ALIADA", (-3200, 0, 355),
         unreal.Color(13, 122, 153, 255), 55.0, 0.0, f)
    sign("Proxy_Rotulo_Rival", "BASE RIVAL", (3200, 0, 355),
         unreal.Color(171, 33, 14, 255), 55.0, 0.0, f)

    log("PROXY pieces " + str(len([m for m in MANIFEST_DATA if m["folder"] == f])))


def build_art_arena():
    f = "Arena_Art"
    suelo = material("Tileable/MI_Suelo_Arena")
    camino = material("Tileable/MI_Camino_Arena")
    plinto = material("Tileable/MI_Plinto")
    roca = material("Tileable/MI_Roca")
    saco = material("Tileable/MI_Saco")
    oro = material("Teams/MI_Terminal_Aliado")
    ally = material("Teams/MI_Base_Aliada")
    rival = material("Teams/MI_Base_Rival")
    nucleo_a = material("Teams/MI_Nucleo_Aliado")
    nucleo_r = material("Teams/MI_Nucleo_Rival")
    term_a = material("Teams/MI_Terminal_Aliado")
    term_r = material("Teams/MI_Terminal_Rival")

    muro_roca = load(ART + "/Models/Static/SM_Rocas_PuertaNorte_Muro")
    saco_alto = load(ART + "/Models/Static/SM_Sacos_Muro_2m_Alto")

    # floor + lanes
    block("Arte_Suelo", (8500, 4950, 180), (0, 0, -90), suelo, f)
    for lane_index, y in enumerate(LANE_Y):
        block("Arte_Carril_%d" % lane_index, (7900, 765, 4), (0, y, 2), camino, f)
        for side in (-1.0, 1.0):
            block("Arte_Borde_%d_%d" % (lane_index, side), (7900, 22, 5),
                  (0, y + side * 400, 4), oro, f)
            block("Arte_Poste_%d_%d" % (lane_index, side), (105, 152, 120),
                  (-1420, y + side * 430, 60), plinto, f)
            block("Arte_Poste_%d_%d_b" % (lane_index, side), (105, 152, 120),
                  (1420, y + side * 430, 60), plinto, f)

    # perimeter: rock wall modules, length 1362.6 cm each
    span = 1362.6
    for side in (-1.0, 1.0):
        for i in range(6):
            x = (i - 2.5) * span
            spawn("Arte_Muro_Y%d_%d" % (side, i), muro_roca, (x, side * 2420, 0),
                  (0, 0, 0), (1, 1, 1), roca, f)
        for i in range(4):
            y = (i - 1.5) * span
            spawn("Arte_Muro_X%d_%d" % (side, i), muro_roca, (side * 4150, y, 0),
                  (0, 90, 0), (1, 1, 1), roca, f)

    # cover: sandbag parapet 199 x 62 cm, two bags high = 158 cm
    # (gameplay cover box is 175 x 235 x 158, same centre)
    for lane_index, y in enumerate(LANE_Y):
        for index in range(5):
            cx = (index - 2) * 520.0
            cy = COVER_Y[(y, index)]
            for depth_row in range(2):
                for level in range(2):
                    spawn("Arte_Cobertura_%d_%d_%d_%d" % (lane_index, index, depth_row, level),
                          saco_alto, (cx, cy + (depth_row - 0.5) * 31.0, level * 79.4),
                          (0, 0, 0), (1, 1, 1), saco, f)

    # central barricades: 7 modules x 2 rows x 4 levels = 1396 x 62 x 318 cm
    for y in (-720.0, 720.0):
        for column in range(7):
            for depth_row in range(2):
                for level in range(4):
                    spawn("Arte_Barricada_%d_%d_%d_%d" % (y, column, depth_row, level), saco_alto,
                          ((column - 3) * 199.4, y + (depth_row - 0.5) * 31.0, level * 79.4),
                          (0, 0, 0), (1, 1, 1), saco, f)

    # cores + terminals keep the gameplay volumes clear, only the skin changes
    for team in (0, 1):
        tint = ally if team == 0 else rival
        glow = nucleo_a if team == 0 else nucleo_r
        core = (BASE_X * (-1 if team == 0 else 1), 0.0, 150.0)
        block("Arte_Base_%d" % team, (600, 700, 66),
              (core[0], core[1], core[2] - 117), plinto, f)
        block("Arte_Nucleo_%d" % team, (360, 470, 220), core, tint, f)
        block("Arte_Nucleo_Tapa_%d" % team, (330, 440, 38),
              (core[0], core[1], core[2] + 130), oro, f)
        block("Arte_Nucleo_Poste_%d" % team, (42, 42, 170),
              (core[0], core[1], core[2] + 220), glow, f, mesh=load(CYL))
        terminal_x = -3040.0 if team == 0 else 3040.0
        term = term_a if team == 0 else term_r
        block("Arte_Terminal_%d" % team, (95, 135, 120),
              (terminal_x, -700, 60), plinto, f)
        block("Arte_Terminal_Tapa_%d" % team, (110, 145, 18),
              (terminal_x, -700, 128), term, f)

    for lane_index, (y, name) in enumerate(zip(LANE_Y, ("IZQUIERDA", "CENTRO", "DERECHA"))):
        sign("Arte_Rotulo_%d" % lane_index, name, (-1490, y, 235),
             unreal.Color(245, 173, 77, 255), 65.0, 0.0, f)
    sign("Arte_Rotulo_Aliada", "BASE ALIADA", (-3200, 0, 355),
         unreal.Color(69, 224, 232, 255), 55.0, 0.0, f)
    sign("Arte_Rotulo_Rival", "BASE RIVAL", (3200, 0, 355),
         unreal.Color(252, 89, 59, 255), 55.0, 0.0, f)

    log("ART arena pieces " + str(len([m for m in MANIFEST_DATA if m["folder"] == f])))


def plane_rot(normal):
    """Rotation whose local +Z (the Plane mesh normal) points along `normal`."""
    try:
        return unreal.MathLibrary.make_rot_from_z(
            unreal.Vector(normal[0], normal[1], normal[2]))
    except Exception:
        return unreal.Rotator(pitch=-90.0, yaw=0.0, roll=0.0)


def pad(label, cx, cy, width, depth):
    block(label, (width, depth, 260), (cx, cy, PAD_TOP - 130),
          material("Tileable/MI_Plinto"), "Art_Showcase_Plinths")
    sign(label + "_Rotulo", label.replace("Art_Plinto_", "").replace("_", " "),
         (cx, cy - depth / 2 + 120, PAD_TOP + 320),
         unreal.Color(219, 240, 240, 255), 48.0, (0, 0), "Art_Showcase_Plinths")


def build_showcase():
    f = "Art_Showcase_Terreno"
    terreno = load(ART + "/Models/Terrain/SM_Terreno_ValleAlfa")
    if terreno:
        spawn("Arte_Terreno_ValleAlfa", terreno, (0, 0, 0), (0, 0, 0), (1, 1, 1),
              material("Terrain/MI_Terreno_ValleAlfa"), f)

    # ---------------- trench gallery
    f = "Art_Showcase_Trinchera"
    pad("Art_Plinto_Trinchera", -5200, -1500, 2400, 2400)
    recta = load(ART + "/Models/Static/SM_Trinchera_Recta_4m")
    esquina = load(ART + "/Models/Static/SM_Trinchera_Esquina")
    final = load(ART + "/Models/Static/SM_Trinchera_Final")
    tierra = material("Tileable/MI_Tierra")
    spawn("Trinchera_Recta_1", recta, (-6200, -1500, PAD_TOP), (0, 0, 0), (1, 1, 1), tierra, f)
    spawn("Trinchera_Recta_2", recta, (-5800, -1500, PAD_TOP), (0, 0, 0), (1, 1, 1), tierra, f)
    spawn("Trinchera_Esquina", esquina, (-5400, -1500, PAD_TOP), (0, 0, 0), (1, 1, 1), tierra, f)
    spawn("Trinchera_Recta_3", recta, (-5400, -1100, PAD_TOP), (0, 90, 0), (1, 1, 1), tierra, f)
    spawn("Trinchera_Final", final, (-5400, -700, PAD_TOP), (0, 90, 0), (1, 1, 1), tierra, f)
    sign("Trinchera_Rotulo", "TRINCHERA MODULAR 4 m", (-5200, -2500, PAD_TOP + 260),
         unreal.Color(219, 240, 240, 255), 42.0, (0, 0), f)

    # ---------------- sandbag gallery
    f = "Art_Showcase_Sacos"
    pad("Art_Plinto_Sacos", -5200, 900, 2400, 1800)
    alto = load(ART + "/Models/Static/SM_Sacos_Muro_2m_Alto")
    bajo = load(ART + "/Models/Static/SM_Sacos_Muro_2m_Bajo")
    esquina_saco = load(ART + "/Models/Static/SM_Sacos_Esquina_Bajo")
    saco = load(ART + "/Models/Static/SM_Saco_Arena")
    sacomat = material("Tileable/MI_Saco")
    for i in range(3):
        spawn("Saco_Alto_%d" % i, alto, (-6100 + i * 200, 600, PAD_TOP), (0, 0, 0), (1, 1, 1), sacomat, f)
    for i in range(3):
        spawn("Saco_Bajo_%d" % i, bajo, (-6100 + i * 200, 900, PAD_TOP), (0, 0, 0), (1, 1, 1), sacomat, f)
    spawn("Saco_Esquina", esquina_saco, (-5300, 600, PAD_TOP), (0, 0, 0), (1, 1, 1), sacomat, f)
    for i in range(6):
        x = -4900 + (i % 3) * 130
        y = 800 + (i // 3) * 120
        z = PAD_TOP + (i % 2) * 17.8
        spawn("Saco_Suelto_%d" % i, saco, (x, y, z), (0, i * 27.0, 0), (1, 1, 1), sacomat, f)
    sign("Sacos_Rotulo", "SACOS DE ARENA", (-5200, 2000, PAD_TOP + 260),
         unreal.Color(219, 240, 240, 255), 42.0, (0, 0), f)

    # ---------------- soldiers + weapons gallery
    f = "Art_Showcase_Soldados"
    pad("Art_Plinto_Soldados", -5200, 3200, 2600, 1900)
    aliado = load(ART + "/Models/Characters/SK_Soldado_Aliado_TPose")
    medico = load(ART + "/Models/Characters/SK_Soldado_Medico_TPose")
    enemigo = load(ART + "/Models/Characters/SK_Soldado_Enemigo_TPose")
    spawn("Soldado_Alpha", aliado, (-5900, 3200, PAD_TOP), (0, 0, 0), (1, 1, 1),
          material("Teams/MI_Soldado_Alpha"), f)
    spawn("Soldado_Bravo", aliado, (-5650, 3200, PAD_TOP), (0, 180, 0), (1, 1, 1),
          material("Teams/MI_Soldado_Bravo"), f)
    spawn("Soldado_Medico", medico, (-5400, 3200, PAD_TOP), (0, 0, 0), (1, 1, 1),
          material("Teams/MI_Soldado_Medico"), f)
    spawn("Soldado_Enemigo", enemigo, (-5150, 3200, PAD_TOP), (0, 180, 0), (1, 1, 1),
          material("Teams/MI_Soldado_Enemigo"), f)
    # 180 cm reference post next to the first soldier
    block("Regla_180cm", (6, 6, 180), (-6100, 3200, PAD_TOP + 90),
          material("Teams/MI_Proxy_Oro"), f)
    sign("Regla_180cm_Rotulo", "180 cm", (-6100, 3200, PAD_TOP + 215),
         unreal.Color(245, 173, 77, 255), 30.0, (0, 0), f)
    # weapon plinth
    block("Plinto_Armas", (760, 420, 80), (-4800, 3200, PAD_TOP + 40),
          material("Tileable/MI_Plinto"), f)
    spawn("Arma_Rifle", load(ART + "/Models/Static/SM_Rifle_Asalto"),
          (-4800, 3200, PAD_TOP + 110), (0, 90, 0), (1, 1, 1),
          material("Teams/MI_Armas"), f)
    spawn("Arma_Pistola", load(ART + "/Models/Static/SM_Pistola"),
          (-4800, 3050, PAD_TOP + 95), (0, 90, 0), (1, 1, 1),
          material("Teams/MI_Armas"), f)
    sign("Soldados_Rotulo", "SOLDADOS 1,80 m  (T-POSE, SIN ESQUELETO)", (-5200, 4200, PAD_TOP + 260),
         unreal.Color(219, 240, 240, 255), 40.0, (0, 0), f)

    # ---------------- bunker gallery
    f = "Art_Showcase_Bunker"
    pad("Art_Plinto_Bunker", 5500, -1500, 2400, 2600)
    concreto = material("Tileable/MI_Concreto")
    for i, (name, mesh_name, y) in enumerate([
            ("Intacto", "SM_Bunker_Enemigo_Intacto", -2300),
            ("Danado", "SM_Bunker_Enemigo_Danado", -1500),
            ("Destruido", "SM_Bunker_Enemigo_Destruido", -700)]):
        spawn("Bunker_" + name, load(ART + "/Models/Static/" + mesh_name),
              (5500, y, PAD_TOP), (0, -90, 0), (1, 1, 1), concreto, f)
    sign("Bunker_Rotulo", "BUNKER ENEMIGO - 3 ESTADOS", (5500, -150, PAD_TOP + 620),
         unreal.Color(219, 240, 240, 255), 40.0, (0, 0), f)

    # ---------------- rock gallery
    f = "Art_Showcase_Rocas"
    pad("Art_Plinto_Rocas", 5500, 1600, 2600, 2200)
    roca_mat = material("Tileable/MI_Roca")
    spawn("Roca_01", load(ART + "/Models/Static/SM_Rocas_PuertaNorte_01"),
          (6100, 900, PAD_TOP), (0, 0, 0), (1, 1, 1), roca_mat, f)
    spawn("Roca_02", load(ART + "/Models/Static/SM_Rocas_PuertaNorte_02"),
          (5900, 1700, PAD_TOP), (0, 45, 0), (1, 1, 1), roca_mat, f)
    spawn("Roca_03", load(ART + "/Models/Static/SM_Rocas_PuertaNorte_03"),
          (6200, 2300, PAD_TOP), (0, 120, 0), (1, 1, 1), roca_mat, f)
    spawn("Roca_Muro", load(ART + "/Models/Static/SM_Rocas_PuertaNorte_Muro"),
          (5000, 2000, PAD_TOP), (0, 90, 0), (1, 1, 1), roca_mat, f)
    sign("Rocas_Rotulo", "PUERTA NORTE - ROCAS", (5500, 2700, PAD_TOP + 400),
         unreal.Color(219, 240, 240, 255), 40.0, (0, 0), f)

    # ---------------- HUD board (facing -Y, camera looks +Y)
    f = "Art_Showcase_HUD"
    pad("Art_Plinto_HUD", 0, -3600, 3200, 1800)
    block("HUD_Panel", (2400, 40, 1429), (0, -4300, PAD_TOP + 720),
          material("HUD/MI_Cartel_HUD"), f)
    sign("HUD_Rotulo", "HUD 1210x720 (referencia de arte)", (0, -4200, PAD_TOP + 1560),
         unreal.Color(219, 240, 240, 255), 40.0, (0, 0), f)
    # Sample HUD readout in the level.  The game agent only has to replace these
    # three lines with values read from its own exposed properties/events.
    for i, line in enumerate([
            "SOLDADO   Sgto. Rojas      ESCUADRA  Alfa-2      ESTADO  Herido",
            "ORDEN     Defender sector C        DESTINATARIOS  4 / 4 (misma orden)",
            "MIC       abierto        RADIO  3.2 s        SELECCION  individual"]):
        sign("HUD_Muestra_%d" % i, line, (0, -4150, PAD_TOP + 470 - i * 130),
             unreal.Color(69, 224, 232, 255), 26.0, (0, 0), f)

    # ---------------- VFX gallery
    f = "Art_Showcase_VFX"
    pad("Art_Plinto_VFX", 0, 3600, 2600, 1800)
    for i, (name, mat_name, x) in enumerate([
            ("Fogonazo", "VFX/MI_VFX_Fogonazo", -800),
            ("Humo", "VFX/MI_VFX_Humo", -300),
            ("Polvo", "VFX/MI_VFX_Polvo", 200),
            ("Chispas", "VFX/MI_VFX_Chispas", 700),
            ("Circulo", "VFX/MI_VFX_Circulo", 1100)]):
        spawn("VFX_" + name, load(CUBE), (x, 3400, PAD_TOP + 200), unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0),
              (5.0, 0.05, 5.0), material(mat_name), f)
    sign("VFX_Rotulo", "VFX - POLVO / CONFIRMACION / IMPACTO", (0, 3000, PAD_TOP + 500),
         unreal.Color(219, 240, 240, 255), 40.0, (0, 0), f)


def build_environment():
    sun = AES.spawn_actor_from_class(unreal.DirectionalLight,
                                     unreal.Vector(0, 0, 900),
                                     unreal.Rotator(-57, -34, 0))
    sun.set_actor_label("Sol")
    try:
        sun.set_folder_path("Iluminacion")
    except Exception:
        pass
    comp = sun.get_component_by_class(unreal.DirectionalLightComponent)
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_intensity(7.0)
    comp.set_editor_property("atmosphere_sun_light", True)

    sky_atmo = AES.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0),
                                          unreal.Rotator(0, 0, 0))
    sky_atmo.set_actor_label("Atmosfera")
    try:
        sky_atmo.set_folder_path("Iluminacion")
    except Exception:
        pass

    sky = AES.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 400),
                                     unreal.Rotator(0, 0, 0))
    sky.set_actor_label("LuzCielo")
    try:
        sky.set_folder_path("Iluminacion")
    except Exception:
        pass
    light = sky.get_component_by_class(unreal.SkyLightComponent)
    light.set_mobility(unreal.ComponentMobility.MOVABLE)
    light.set_intensity(2.5)
    light.set_editor_property("real_time_capture", True)

    # Locked exposure range so the before/after captures stay comparable and
    # the shadows do not crush.  Same volume is used by Play In Editor.
    vol = AES.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(0, 0, 0),
                                     unreal.Rotator(0, 0, 0))
    vol.set_actor_label("PostProceso")
    try:
        vol.set_folder_path("Iluminacion")
    except Exception:
        pass
    try:
        vol.set_editor_property("unbound", True)
        settings = vol.get_editor_property("settings")
        settings.set_editor_property("bloom_intensity", 0.35)
        settings.set_editor_property("auto_exposure_bias", 0.0)
        try:
            settings.set_editor_property("auto_exposure_min_ev100", 1.0)
            settings.set_editor_property("auto_exposure_max_ev100", 5.0)
            log("exposure clamped EV100 1..5")
        except Exception:
            settings.set_editor_property("auto_exposure_min_brightness", 2.0)
            settings.set_editor_property("auto_exposure_max_brightness", 4.0)
            log("exposure clamped via brightness")
        vol.set_editor_property("settings", settings)
    except Exception as exc:
        log("PostProcess EXC %r" % (exc,))

    for actor in AES.get_all_level_actors():
        if isinstance(actor, unreal.WorldSettings):
            try:
                actor.set_editor_property("default_game_mode", unreal.GameModeBase)
                log("GameMode = GameModeBase (no gameplay)")
            except Exception as exc:
                log("GameMode EXC %r" % (exc,))
            break


def build_cameras():
    camera("Camara_Comandante", (-3100, -510, 180), look_at=(4000, -510, 180))
    camera("Camara_Base", (-3200, 0, 430), look_at=(2000, 0, 100))
    camera("Camara_Centro", (0, 0, 560), look_at=(3000, 0, 100))
    camera("Camara_Flanco", (0, -1440, 300), look_at=(3000, -1440, 100))
    camera("Camara_Showcase_Oeste", (-3700, -900, 800), look_at=(-5350, -1250, 320), fov=70.0)
    camera("Camara_Showcase_Soldados", (-4000, 3050, 620), look_at=(-5450, 3200, 340), fov=65.0)
    camera("Camara_Showcase_Este", (3900, -1150, 700), look_at=(5450, -1500, 320), fov=70.0)
    camera("Camara_Showcase_Rocas", (3950, 1650, 620), look_at=(5450, 1850, 330), fov=65.0)
    camera("Camara_HUD", (0, -2500, 800), look_at=(0, -4300, 950), fov=75.0)
    camera("Camara_VFX", (0, 2500, 650), look_at=(0, 3400, 450), fov=65.0)


try:
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        log("Level exists, reloading and clearing")
        if not LES.load_level(LEVEL):
            raise RuntimeError("load_level failed")
        for actor in AES.get_all_level_actors():
            if isinstance(actor, unreal.WorldSettings):
                continue
            AES.destroy_actor(actor)
    else:
        if not LES.new_level(LEVEL):
            raise RuntimeError("new_level failed")
    build_environment()
    build_proxy()
    build_art_arena()
    build_showcase()
    build_cameras()
    LES.save_current_level()
    log("SAVED " + LEVEL)
    log("TOTAL actors " + str(len(MANIFEST_DATA)))
    log("DONE")
except Exception:
    log("EXC\n" + traceback.format_exc())
finally:
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES))
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(MANIFEST_DATA, f, indent=1)
