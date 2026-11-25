"""Calibration capture for the HUD reference plane.

Spawns six probe planes in front of the HUD board with different rotations and
materials, then renders one frame from Camara_HUD so the correct orientation and
a working material can be picked visually.
"""
import os
import traceback

import unreal

ART = "/Game/Yell/Art"
LEVEL = ART + "/Levels/ValleAlfa_Presentacion"
PROJECT = unreal.Paths.project_dir()
ROOT = os.path.abspath(os.path.join(PROJECT, ".."))
OUT_DIR = os.path.join(ROOT, "Documentacion", "Capturas")
REPORT = os.path.join(PROJECT, "Saved", "yell_hud_calib.txt")

WIDTH, HEIGHT = 1280, 720

AES = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
RL = unreal.RenderingLibrary

LINES = []


def log(t):
    LINES.append(str(t))
    try:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(LINES))
    except Exception:
        pass


def find(label):
    for actor in AES.get_all_level_actors():
        if actor.get_actor_label() == label:
            return actor
    return None


PROBES = [
    ("PROBE_A", -2100, "/Engine/BasicShapes/Plane", (6.0, 3.6, 1.0),
     unreal.Rotator(pitch=0.0, yaw=0.0, roll=90.0), "HUD/MI_Cartel_HUD"),
    ("PROBE_B", -1200, "/Engine/BasicShapes/Plane", (6.0, 3.6, 1.0),
     unreal.Rotator(pitch=0.0, yaw=180.0, roll=-90.0), "HUD/MI_Cartel_HUD"),
    ("PROBE_C", -300, "/Engine/BasicShapes/Cube", (6.0, 0.04, 3.6),
     unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0), "HUD/MI_Cartel_HUD"),
    ("PROBE_D", 600, "/Engine/BasicShapes/Cube", (6.0, 0.04, 3.6),
     unreal.Rotator(pitch=0.0, yaw=180.0, roll=0.0), "HUD/MI_Cartel_HUD"),
    ("PROBE_E", 1500, "/Engine/BasicShapes/Plane", (6.0, 3.6, 1.0),
     unreal.Rotator(pitch=0.0, yaw=180.0, roll=-90.0), "Teams/MI_Proxy_Oro"),
    ("PROBE_F", 2400, "/Engine/BasicShapes/Cube", (6.0, 0.04, 3.6),
     unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0), "Teams/MI_Proxy_Oro"),
]


class Runner:
    def __init__(self):
        self.phase = "load"
        self.wait = 0

    def setup(self):
        os.makedirs(OUT_DIR, exist_ok=True)
        if not LES.load_level(LEVEL):
            raise RuntimeError("load_level failed")

    def build_probes(self):
        # remove old probes
        for actor in list(AES.get_all_level_actors()):
            try:
                if str(actor.get_actor_label()).startswith("PROBE_"):
                    AES.destroy_actor(actor)
            except Exception:
                pass
        names = set()
        for actor in AES.get_all_level_actors():
            try:
                names.add(actor.get_actor_label())
            except Exception:
                pass
        log("level actors = %d" % len(names))
        cam = find("Camara_HUD")
        cl = cam.get_actor_location()
        cr = cam.get_actor_rotation()
        log("CAMERA loc=(%.0f,%.0f,%.0f) rot=(%.2f,%.2f,%.2f)" % (cl.x, cl.y, cl.z,
                                                                  cr.pitch, cr.yaw, cr.roll))
        for probe_label in ("HUD_Panel", "HUD_Referencia", "Art_Plinto_HUD"):
            act = find(probe_label)
            if act is None:
                log("%s NOT FOUND" % probe_label)
                continue
            o, e = act.get_actor_bounds(False)
            log("%s loc=(%.0f,%.0f,%.0f) ext=(%.0f,%.0f,%.0f)" % (
                probe_label, o.x, o.y, o.z, e.x, e.y, e.z))
        # a probe 3 m in front of the camera to prove spawning+rendering works
        near = AES.spawn_actor_from_class(unreal.StaticMeshActor,
                                          unreal.Vector(0, cl.y + 300, cl.z),
                                          unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0))
        near.set_actor_label("PROBE_G")
        ncomp = near.static_mesh_component
        ncomp.set_editor_property("static_mesh", unreal.load_asset("/Engine/BasicShapes/Cube"))
        near.set_actor_scale3d(unreal.Vector(1.0, 0.05, 1.0))
        ncomp.set_material(0, unreal.load_asset(ART + "/Materials/Instances/Teams/MI_Proxy_Oro"))
        near.set_folder_path("Art_Showcase_HUD")
        log("PROBE_G at (0, %.0f, %.0f)" % (cl.y + 300, cl.z))
        for label, x, mesh_path, scale, rot, mat_name in PROBES:
            actor = AES.spawn_actor_from_class(unreal.StaticMeshActor,
                                               unreal.Vector(x, -4260, 970), rot)
            actor.set_actor_label(label)
            comp = actor.static_mesh_component
            comp.set_editor_property("static_mesh", unreal.load_asset(mesh_path))
            actor.set_actor_scale3d(unreal.Vector(scale[0], scale[1], scale[2]))
            mat = unreal.load_asset(ART + "/Materials/Instances/" + mat_name)
            if mat:
                comp.set_material(0, mat)
            try:
                origin, extent = actor.get_actor_bounds(False)
                log("%s mesh=%s bounds loc=(%.0f,%.0f,%.0f) ext=(%.0f,%.0f,%.0f)" % (
                    label, mesh_path.split("/")[-1], origin.x, origin.y, origin.z,
                    extent.x, extent.y, extent.z))
            except Exception as exc:
                log("%s bounds EXC %r" % (label, exc))
            actor.set_folder_path("Art_Showcase_HUD")

    def prepare_capture(self):
        self.ctx = AES.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0),
                                              unreal.Rotator(0, 0, 0))
        self.rt = RL.create_render_target2d(self.ctx, WIDTH, HEIGHT,
                                            unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        self.capture = AES.spawn_actor_from_class(unreal.SceneCapture2D,
                                                  unreal.Vector(0, 0, 0),
                                                  unreal.Rotator(0, 0, 0))
        comp = self.capture.capture_component2d
        comp.set_editor_property("texture_target", self.rt)
        comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        comp.set_editor_property("capture_every_frame", False)
        cam = find("Camara_HUD")
        log("camera found = %r" % (cam is not None,))
        comp.set_world_location_and_rotation(cam.get_actor_location(),
                                             cam.get_actor_rotation(), False, False)

    def tick(self, delta):
        if self.phase == "load":
            try:
                self.setup()
                self.phase = "settle"
                self.wait = 0
            except Exception:
                log("SETUP EXC\n" + traceback.format_exc())
                self.finish()
            return
        if self.phase == "settle":
            self.wait += 1
            if self.wait < 90:
                return
            try:
                self.build_probes()
                self.prepare_capture()
                self.phase = "run"
                self.wait = 0
            except Exception:
                log("PROBE EXC\n" + traceback.format_exc())
                self.finish()
            return
        if self.phase != "run":
            return
        if self.wait < 30:
            self.wait += 1
            return
        try:
            comp = self.capture.capture_component2d
            comp.capture_scene()
            name = "probe_hud"
            RL.export_render_target(self.ctx, self.rt, OUT_DIR, name)
            raw = os.path.join(OUT_DIR, name)
            if os.path.isfile(raw):
                os.replace(raw, raw + ".png")
                log("EXPORT ok")
            else:
                log("EXPORT missing file")
        except Exception:
            log("SHOT EXC\n" + traceback.format_exc())
        self.finish()

    def finish(self):
        self.phase = "finish"
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
        RUNNER.finish()


log("calib loaded")
RUNNER.handle = unreal.register_slate_post_tick_callback(on_tick)
