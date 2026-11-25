import os

import unreal

LEVEL = "/Game/Yell/Art/Levels/ValleAlfa_Presentacion"
OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_hud_probe.txt")
LINES = []

AES = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

LES.load_level(LEVEL)
for actor in AES.get_all_level_actors():
    try:
        folder = str(actor.get_folder_path())
    except Exception:
        folder = "?"
    if folder.startswith("Art_Showcase_HUD") or actor.get_actor_label() == "HUD_Referencia":
        loc = actor.get_actor_location()
        rot = actor.get_actor_rotation()
        sc = actor.get_actor_scale3d()
        LINES.append("%s | %s | %s | loc=(%.1f,%.1f,%.1f) rot=(%.1f,%.1f,%.1f) scale=(%.2f,%.2f,%.2f)" % (
            actor.get_actor_label(), actor.get_class().get_name(), folder,
            loc.x, loc.y, loc.z, rot.pitch, rot.yaw, rot.roll, sc.x, sc.y, sc.z))
        if isinstance(actor, unreal.StaticMeshActor):
            comp = actor.static_mesh_component
            mesh = comp.get_editor_property("static_mesh")
            LINES.append("   mesh=%s hidden=%s visible=%s" % (
                mesh.get_name() if mesh else None, comp.get_editor_property("hidden_in_game"),
                actor.is_hidden()))
            for i in range(4):
                mat = comp.get_material(i)
                if mat is None:
                    continue
                LINES.append("   mat[%d]=%s" % (i, mat.get_path_name()))
                try:
                    parent = mat.get_editor_property("parent")
                    LINES.append("      parent=%s" % (parent.get_path_name() if parent else None))
                    params = unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat, "Textura")
                    LINES.append("      Textura=%s" % (params.get_path_name() if params else None))
                except Exception as exc:
                    LINES.append("      inst EXC %r" % (exc,))

with open(OUT, "w", encoding="utf-8") as f:
    f.write("\n".join(LINES))
