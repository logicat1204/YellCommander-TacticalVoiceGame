import os
import traceback

import unreal

PROJECT = unreal.Paths.project_dir()
ROOT = os.path.abspath(os.path.join(PROJECT, ".."))
OUT = os.path.join(PROJECT, "Saved", "yell_reimport_check.txt")
LINES = []


def log(t):
    LINES.append(str(t))


try:
    lib = unreal.EditorAssetLibrary
    for rel in ["Models/Static", "Models/Characters", "Models/Terrain"]:
        path = "/Game/Yell/Art/" + rel
        if lib.does_directory_exist(path):
            log("DELETE " + path + " -> " + str(lib.delete_directory(path)))
        lib.make_directory(path)

    src = os.path.join(ROOT, "Assets", "Models", "UE5_StaticMeshes", "SM_Trinchera_Recta_4m.fbx")
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = "/Game/Yell/Art/Models/Static"
    task.destination_name = "SM_Trinchera_Recta_4m"
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    options = unreal.FbxImportUI()
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_mesh = True
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.set_editor_property("combine_meshes", True)
    options.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    options.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    options.static_mesh_import_data.set_editor_property("convert_scene_unit", True)
    options.static_mesh_import_data.set_editor_property("import_uniform_scale", 1.0)
    log("READBACK convert=" + str(options.static_mesh_import_data.get_editor_property("convert_scene_unit")))
    log("READBACK scale=" + str(options.static_mesh_import_data.get_editor_property("import_uniform_scale")))
    task.options = options
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = lib.load_asset("/Game/Yell/Art/Models/Static/SM_Trinchera_Recta_4m")
    log("MESH " + str(mesh))
    if mesh:
        box = mesh.get_bounding_box()
        log("BOUNDS " + str(box.min) + " .. " + str(box.max) + " size=" + str(box.max - box.min))
except Exception:
    log("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES))
