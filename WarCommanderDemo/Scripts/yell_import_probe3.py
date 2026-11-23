import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_import_probe3.txt")
lines = []
def w(s):
    lines.append(str(s))

try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    base = "/Game/Yell/Art/_Probe"
    unreal.EditorAssetLibrary.make_directory(base)
    root = os.path.abspath(os.path.join(unreal.Paths.project_dir(), ".."))

    # static mesh import with options
    fbx = os.path.join(root, "Assets", "Models", "UE5_StaticMeshes", "SM_Trinchera_Recta_4m.fbx")
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = base
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
    task.options = f
    at.import_asset_tasks([task])
    w("SM RESULT " + str(task.imported_object_paths))
    sm = unreal.EditorAssetLibrary.load_asset(base + "/SM_Trinchera_Recta_4m")
    w("SM " + str(sm))
    if sm:
        for prop in ["extended_bounds", "bounding_box", "static_materials", "nanite_settings"]:
            try:
                w("SM " + prop + " " + str(sm.get_editor_property(prop)))
            except Exception as e:
                w("SM " + prop + " EXC " + repr(e))
        w("SM DIR " + str([x for x in dir(sm) if not x.startswith("_")]))
        try:
            w("SM COL " + str(unreal.StaticMeshEditorSubsystem().get_simple_collision_count(sm)))
        except Exception as e:
            w("SM COL EXC " + repr(e))

    # skeletal mesh import
    sk_fbx = os.path.join(root, "Assets", "Models", "Mixamo_Upload", "Extracted", "SK_Soldado_Aliado_TPose.fbx")
    task2 = unreal.AssetImportTask()
    task2.filename = sk_fbx
    task2.destination_path = base
    task2.automated = True
    task2.save = True
    task2.replace_existing = True
    task2.factory = unreal.FbxFactory()
    f2 = unreal.FbxImportUI()
    f2.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    f2.import_mesh = True
    f2.import_as_skeletal = True
    f2.import_materials = True
    f2.import_textures = False
    f2.import_animations = False
    f2.create_physics_asset = False
    f2.skeletal_mesh_import_data.set_editor_property("import_uniform_scale", 1.0)
    f2.skeletal_mesh_import_data.set_editor_property("convert_scene_unit", True)
    f2.skeletal_mesh_import_data.set_editor_property("force_front_x_axis", False)
    task2.options = f2
    at.import_asset_tasks([task2])
    w("SK RESULT " + str(task2.imported_object_paths))
    sk = unreal.EditorAssetLibrary.load_asset(base + "/SK_Soldado_Aliado_TPose")
    w("SK " + str(sk))
    if sk:
        w("SK DIR " + str([x for x in dir(sk) if not x.startswith("_")]))
        for prop in ["extended_bounds", "skeleton", "physics_asset", "materials", "sk_skeleton"]:
            try:
                w("SK " + prop + " " + str(sk.get_editor_property(prop)))
            except Exception as e:
                w("SK " + prop + " EXC " + repr(e))
        try:
            w("SK BOUNDS " + str(sk.get_bounding_box()))
        except Exception as e:
            w("SK BOUNDS EXC " + repr(e))
        skel = sk.get_editor_property("skeleton")
        w("SKEL " + str(skel))
        if skel:
            w("SKEL DIR " + str([x for x in dir(skel) if not x.startswith("_")]))
            try:
                w("SKEL BONES " + str(skel.get_editor_property("bone_tree")))
            except Exception as e:
                w("SKEL BONES EXC " + repr(e))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
