import os

import unreal

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_caps_probe.txt")
LINES = []


def dump(label, obj):
    try:
        names = [n for n in dir(obj) if not n.startswith("_")]
    except Exception as exc:
        LINES.append("%s EXC %r" % (label, exc))
        return
    LINES.append(label + " " + repr(names))


dump("LevelEditorSubsystem", unreal.LevelEditorSubsystem)
dump("UnrealEditorSubsystem", unreal.UnrealEditorSubsystem)
dump("EditorActorSubsystem", unreal.EditorActorSubsystem)
dump("RenderingLibrary", unreal.RenderingLibrary)
dump("SceneCaptureComponent2D", unreal.SceneCaptureComponent2D)
dump("SceneCapture2D", unreal.SceneCapture2D)
dump("TextureRenderTarget2D", unreal.TextureRenderTarget2D)
dump("TextureRenderTargetFormat", unreal.TextureRenderTargetFormat)
dump("SceneCaptureSource", unreal.SceneCaptureSource)
dump("AutomationLibrary", unreal.AutomationLibrary)
dump("SystemLibrary", unreal.SystemLibrary)
dump("EditorLevelLibrary", unreal.EditorLevelLibrary)
dump("Actor", unreal.Actor)

try:
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    LINES.append("les instance " + repr(les))
    ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    LINES.append("ues instance " + repr(ues))
    LINES.append("game world " + repr(ues.get_game_world()))
    LINES.append("editor world " + repr(ues.get_editor_world()))
except Exception as exc:
    LINES.append("subsystem EXC %r" % (exc,))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES))
