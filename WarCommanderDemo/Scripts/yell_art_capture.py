"""Capture before/after frames of ValleAlfa_Presentacion with a SceneCapture2D.

Runs headless (no viewport needed): renders into a 1280x720 render target and
exports PNGs to Documentation/Capturas.  The "before" state parks every
Arena_Art / Art_Showcase actor far below the map so only the flat proxy blocks
remain; the "after" state parks the proxy instead.  Camera transforms are read
from the named camera actors, so both states use the exact same point of view.
"""
import json
import os
import traceback

import unreal

ART = "/Game/Yell/Art"
LEVEL = ART + "/Levels/ValleAlfa_Presentacion"
PROJECT = unreal.Paths.project_dir()
ROOT = os.path.abspath(os.path.join(PROJECT, ".."))
OUT_DIR = os.path.join(ROOT, "Documentacion", "Capturas")
REPORT = os.path.join(PROJECT, "Saved", "yell_capture.txt")

WIDTH, HEIGHT = 1280, 720
PARK = -250000.0

LINES = []
AES = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
RL = unreal.RenderingLibrary


def log(t):
    LINES.append(str(t))


def actors_in(folder_prefix):
    out = []
    for actor in AES.get_all_level_actors():
        try:
            path = str(actor.get_folder_path())
        except Exception:
            continue
        if path.startswith(folder_prefix):
            out.append(actor)
    return out


def park(actors, on):
    for actor in actors:
        loc = actor.get_actor_location()
        if on:
            actor.set_actor_location(unreal.Vector(loc.x, loc.y, PARK), False, False)
        else:
            # stored by park_offset
            actor.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + 250000.0), False, False)


def park_all(actors, on):
    for actor in actors:
        loc = actor.get_actor_location()
        if on:
            actor.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + PARK), False, False)


def restore_all(actors):
    for actor in actors:
        loc = actor.get_actor_location()
        actor.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z - PARK), False, False)


def find_camera(label):
    for actor in AES.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


def main():
    world = UES.get_editor_world()
    os.makedirs(OUT_DIR, exist_ok=True)

    if not LES.load_level(LEVEL):
        raise RuntimeError("load_level failed")

    ctx = None
    for actor in AES.get_all_level_actors():
        if isinstance(actor, unreal.WorldSettings):
            ctx = actor
            break
    if ctx is None:
        ctx = AES.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0),
                                         unreal.Rotator(0, 0, 0))
    log("context " + str(ctx))

    rt = RL.create_render_target2d(ctx, WIDTH, HEIGHT,
                                   unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    rt.set_editor_property("clear_color", unreal.LinearColor(0.03, 0.05, 0.06, 1.0))
    log("RT " + str(rt))

    capture = AES.spawn_actor_from_class(unreal.SceneCapture2D,
                                         unreal.Vector(0, 0, 0),
                                         unreal.Rotator(0, 0, 0))
    capture.set_actor_label("CaptureTemp")
    comp = capture.capture_component2d
    comp.set_editor_property("texture_target", rt)
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property("capture_every_frame", False)
    comp.set_editor_property("capture_on_movement", False)
    comp.set_editor_property("fov_angle", 75.0)

    proxy = actors_in("Arena_Proxy")
    art = actors_in("Arena_Art")
    showcases = actors_in("Art_Showcase")
    log("proxy=%d art=%d showcase=%d" % (len(proxy), len(art), len(showcases)))

    def shoot(cam_label, file_name):
        cam = find_camera(cam_label)
        if cam is None:
            log("MISSING CAMERA " + cam_label)
            return
        loc = cam.get_actor_location()
        rot = cam.get_actor_rotation()
        comp.set_world_location_and_rotation(loc, rot, False, False)
        for _ in range(4):
            comp.capture_scene()
        RL.export_render_target(ctx, rt, OUT_DIR, file_name)
        log("SHOT %-28s %-34s %s" % (file_name, cam_label, (loc.x, loc.y, loc.z)))

    # ---------------- BEFORE (flat proxy only)
    park_all(art, True)
    park_all(showcases, True)
    shoot("Camara_Comandante", "01_antes_comandante")
    shoot("Camara_Base", "02_antes_base")
    shoot("Camara_Centro", "03_antes_centro")
    shoot("Camara_Flanco", "04_antes_flanco")
    restore_all(art)
    restore_all(showcases)

    # ---------------- AFTER (imported art only)
    park_all(proxy, True)
    shoot("Camara_Comandante", "05_despues_comandante")
    shoot("Camara_Base", "06_despues_base")
    shoot("Camara_Centro", "07_despues_centro")
    shoot("Camara_Flanco", "08_despues_flanco")
    restore_all(proxy)

    # ---------------- showcases
    shoot("Camara_Showcase_Oeste", "09_galeria_oeste")
    shoot("Camara_Showcase_Este", "10_galeria_este")
    shoot("Camara_HUD", "11_hud")
    shoot("Camara_VFX", "12_vfx")

    AES.destroy_actor(capture)
    log("DONE")


try:
    main()
except Exception:
    log("EXC\n" + traceback.format_exc())
finally:
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES))
