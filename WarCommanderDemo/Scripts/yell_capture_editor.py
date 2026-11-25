"""Editor-session capture: needs a real Slate/renderer loop.

Launch:
  UnrealEditor.exe <uproject> -ExecutePythonScript="<this file>" -nosplash -nop4

A SceneCapture2D is not rendered inside -run=pythonscript (no frame loop), so
this script drives the captures from a Slate post-tick callback and then quits.
"""
import json
import os
import struct
import traceback

import unreal

ART = "/Game/Yell/Art"
LEVEL = ART + "/Levels/ValleAlfa_Presentacion"
PROJECT = unreal.Paths.project_dir()
ROOT = os.path.abspath(os.path.join(PROJECT, ".."))
OUT_DIR = os.path.join(ROOT, "Documentacion", "Capturas")
REPORT = os.path.join(PROJECT, "Saved", "yell_capture_editor.txt")

WIDTH, HEIGHT = 1280, 720
PARK = -250000.0

AES = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
RL = unreal.RenderingLibrary

LINES = []


def log(t):
    LINES.append(str(t))
    try:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES))
    except Exception:
        pass


def actors_in(prefix):
    out = []
    for actor in AES.get_all_level_actors():
        try:
            if str(actor.get_folder_path()).startswith(prefix):
                out.append(actor)
        except Exception:
            pass
    return out


def move(actors, dz):
    for actor in actors:
        loc = actor.get_actor_location()
        actor.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + dz), False, False)


def find_camera(label):
    for actor in AES.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


class Runner:
    def __init__(self):
        self.rt = None
        self.capture = None
        self.ctx = None
        self.proxy = []
        self.art = []
        self.show = []
        self.queue = []
        self.wait = 0
        self.index = 0
        self.done = False
        self.phase = "load"

    def setup(self):
        os.makedirs(OUT_DIR, exist_ok=True)
        if not LES.load_level(LEVEL):
            raise RuntimeError("load_level failed")
        self.ctx = AES.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0),
                                              unreal.Rotator(0, 0, 0))
        self.rt = RL.create_render_target2d(self.ctx, WIDTH, HEIGHT,
                                            unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        self.rt.set_editor_property("clear_color",
                                    unreal.LinearColor(0.03, 0.05, 0.06, 1.0))
        self.capture = AES.spawn_actor_from_class(unreal.SceneCapture2D,
                                                  unreal.Vector(0, 0, 0),
                                                  unreal.Rotator(0, 0, 0))
        self.capture.set_actor_label("CaptureTemp")
        comp = self.capture.capture_component2d
        comp.set_editor_property("texture_target", self.rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property("capture_every_frame", False)
        comp.set_editor_property("capture_on_movement", False)
        comp.set_editor_property("fov_angle", 75.0)

        self.proxy = actors_in("Arena_Proxy")
        self.art = actors_in("Arena_Art")
        self.show = actors_in("Art_Showcase")
        log("actors proxy=%d art=%d showcase=%d" % (len(self.proxy), len(self.art), len(self.show)))

        # hide the imported art so the proxy state is the "before" frame
        move(self.art, PARK)
        move(self.show, PARK)
        self.queue = [
            ("warm", 45),
            ("shot", ("Camara_Comandante", "01_antes_comandante")),
            ("shot", ("Camara_Base", "02_antes_base")),
            ("shot", ("Camara_Centro", "03_antes_centro")),
            ("shot", ("Camara_Flanco", "04_antes_flanco")),
            ("swap", None),
            ("warm", 45),
            ("shot", ("Camara_Comandante", "05_despues_comandante")),
            ("shot", ("Camara_Base", "06_despues_base")),
            ("shot", ("Camara_Centro", "07_despues_centro")),
            ("shot", ("Camara_Flanco", "08_despues_flanco")),
            ("showcase", None),
            ("warm", 45),
            ("shot", ("Camara_Showcase_Oeste", "09_galeria_trinchera")),
            ("shot", ("Camara_Showcase_Soldados", "10_galeria_soldados")),
            ("shot", ("Camara_Showcase_Este", "11_galeria_bunker")),
            ("shot", ("Camara_Showcase_Rocas", "12_galeria_rocas")),
            ("shot", ("Camara_HUD", "13_hud")),
            ("shot", ("Camara_VFX", "14_vfx")),
            ("finish", None),
        ]
        self.phase = "run"

    def shoot(self, cam_label, name):
        cam = find_camera(cam_label)
        if cam is None:
            log("MISSING CAMERA " + cam_label)
            return
        comp = self.capture.capture_component2d
        comp.set_world_location_and_rotation(cam.get_actor_location(),
                                            cam.get_actor_rotation(), False, False)
        comp.capture_scene()
        raw_path = os.path.join(OUT_DIR, name)
        png_path = raw_path + ".png"
        if os.path.isfile(png_path):
            os.remove(png_path)
        RL.export_render_target(self.ctx, self.rt, OUT_DIR, name)
        ok = "fail"
        if os.path.isfile(raw_path):
            os.replace(raw_path, png_path)
            ok = "png"
        else:
            # fallback: dump raw pixels for an offline conversion
            try:
                pixels = RL.read_render_target(self.ctx, self.rt)
                with open(png_path.replace(".png", ".rgba"), "wb") as f:
                    for p in pixels:
                        f.write(struct.pack("<4f", p.r, p.g, p.b, p.a))
                ok = "raw"
            except Exception as exc:
                ok = "fail:%r" % (exc,)
        log("SHOT %-30s %s" % (name, ok))

    def tick(self, delta):
        if self.phase == "load":
            try:
                self.setup()
            except Exception:
                log("SETUP EXC\n" + traceback.format_exc())
                self.phase = "finish"
            return
        if self.phase != "run":
            return
        if self.wait > 0:
            self.wait -= 1
            return
        if self.index >= len(self.queue):
            self.phase = "finish"
            return
        kind, payload = self.queue[self.index]
        self.index += 1
        if kind == "warm":
            self.wait = payload
        elif kind == "shot":
            self.shoot(*payload)
            self.wait = 3
        elif kind == "swap":
            move(self.art, -PARK)
            move(self.proxy, PARK)
            log("swap to art (showcase still parked)")
        elif kind == "showcase":
            move(self.show, -PARK)
            log("showcase on")
        elif kind == "finish":
            self.finish()

    def finish(self):
        self.phase = "finish"
        try:
            move(self.proxy, -PARK)
            move(self.art, -PARK)
            move(self.show, -PARK)
        except Exception:
            pass
        log("DONE")
        try:
            unreal.unregister_slate_post_tick_callback(self.handle)
        except Exception:
            pass
        unreal.SystemLibrary.quit_editor()


RUNNER = Runner()


def on_tick(delta):
    try:
        RUNNER.tick(delta)
    except Exception:
        log("TICK EXC\n" + traceback.format_exc())
        RUNNER.phase = "finish"


log("script loaded")
RUNNER.handle = unreal.register_slate_post_tick_callback(on_tick)
