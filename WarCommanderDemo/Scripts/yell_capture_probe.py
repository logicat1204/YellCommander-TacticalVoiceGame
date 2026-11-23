import os
import traceback

import unreal

ART = "/Game/Yell/Art"
LEVEL = ART + "/Levels/ValleAlfa_Presentacion"
PROJECT = unreal.Paths.project_dir()
OUT = os.path.join(PROJECT, "Saved", "yell_capture_probe.txt")
LINES = []

AES = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
UES = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
RL = unreal.RenderingLibrary


def log(t):
    LINES.append(str(t))


try:
    LES.load_level(LEVEL)
    ctx = AES.spawn_actor_from_class(unreal.Actor, unreal.Vector(0, 0, 0),
                                     unreal.Rotator(0, 0, 0))
    log("ctx " + str(ctx))
    rt = RL.create_render_target2d(ctx, 640, 360, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    log("RT " + str(rt))
    cap = AES.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(-3100, -510, 180),
                                     unreal.Rotator(0, 0, 0))
    comp = cap.capture_component2d
    comp.set_editor_property("texture_target", rt)
    comp.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
    comp.set_editor_property("capture_every_frame", False)
    comp.set_editor_property("capture_on_movement", False)
    comp.capture_scene()
    comp.capture_scene()
    log("captured")
    out_dir = os.path.join(PROJECT, "Saved", "probe_shots")
    os.makedirs(out_dir, exist_ok=True)
    ok = RL.export_render_target(ctx, rt, out_dir, "probe")
    log("export -> " + str(ok) + " dir=" + out_dir)
    log("exists " + str(os.path.isfile(os.path.join(out_dir, "probe.png"))))
    try:
        pixels = RL.read_render_target(ctx, rt)
        log("pixels len " + str(len(pixels)))
        for i in (0, 1000, len(pixels) // 2):
            p = pixels[i]
            log("px[%d] = %.3f %.3f %.3f %.3f" % (i, p.r, p.g, p.b, p.a))
    except Exception as exc:
        log("read EXC %r" % (exc,))
    AES.destroy_actor(cap)
except Exception:
    log("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES))
