import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_import_probe2.txt")
lines = []
def w(s):
    lines.append(str(s))

try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    base = "/Game/Yell/Art/_Probe"
    unreal.EditorAssetLibrary.make_directory(base)
    root = os.path.abspath(os.path.join(unreal.Paths.project_dir(), ".."))
    fbx = os.path.join(root, "Assets", "Models", "UE5_StaticMeshes", "SM_Trinchera_Recta_4m.fbx")

    # Attempt A: factory FbxFactory + options FbxImportUI
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = base
    task.destination_name = "SM_Trinchera_A"
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    f = unreal.FbxImportUI()
    f.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    f.import_mesh = True
    f.import_materials = True
    f.import_textures = False
    f.static_mesh_import_data.set_editor_property("combine_meshes", True)
    f.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    f.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    try:
        task.options = f
        w("OPTIONS A SET")
    except Exception as e:
        w("OPTIONS A EXC " + repr(e))
    at.import_asset_tasks([task])
    w("A RESULT " + str(task.imported_object_paths))
    sm = unreal.EditorAssetLibrary.load_asset(base + "/SM_Trinchera_A")
    w("A SM " + str(sm))
    if sm:
        w("A BOUNDS " + str(sm.get_bounding_box()))
        w("A MATS " + str([str(m) for m in sm.get_editor_property("static_materials")]))
        try:
            w("A COL " + str(unreal.StaticMeshEditorSubsystem().get_simple_collision_count(sm)))
        except Exception as e:
            w("A COL EXC " + repr(e))

    # Attempt B: FbxSceneImportFactory
    task2 = unreal.AssetImportTask()
    task2.filename = fbx
    task2.destination_path = base
    task2.destination_name = "SM_Trinchera_B"
    task2.automated = True
    task2.save = True
    task2.replace_existing = True
    fac = unreal.FbxSceneImportFactory()
    w("B FAC " + str(fac))
    try:
        w("B OPTS " + str(fac.get_editor_property("scene_import_options_static_mesh")))
    except Exception as e:
        w("B OPTS EXC " + repr(e))
    task2.factory = fac
    at.import_asset_tasks([task2])
    w("B RESULT " + str(task2.imported_object_paths))
    sm2 = unreal.EditorAssetLibrary.load_asset(base + "/SM_Trinchera_B")
    w("B SM " + str(sm2))
    if sm2:
        w("B BOUNDS " + str(sm2.get_bounding_box()))
        w("B MATS " + str([str(m) for m in sm2.get_editor_property("static_materials")]))
        try:
            w("B COL " + str(unreal.StaticMeshEditorSubsystem().get_simple_collision_count(sm2)))
        except Exception as e:
            w("B COL EXC " + repr(e))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
