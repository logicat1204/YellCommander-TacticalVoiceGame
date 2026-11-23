import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_import_probe.txt")
lines = []
def w(s):
    lines.append(str(s))

try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    base = "/Game/Yell/Art/_Probe"
    unreal.EditorAssetLibrary.make_directory(base)
    root = os.path.abspath(os.path.join(unreal.Paths.project_dir(), ".."))
    w("ROOT " + root)
    png = os.path.join(root, "Assets", "Textures", "Tileable", "T_Concreto_BC.png")
    w("PNG " + png + " exists=" + str(os.path.exists(png)))
    task = unreal.AssetImportTask()
    task.filename = png
    task.destination_path = base
    task.destination_name = "T_Concreto_BC_Test"
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.TextureFactory()
    at.import_asset_tasks([task])
    w("IMPORT RESULT " + str(task.imported_object_paths))
    tex = unreal.EditorAssetLibrary.load_asset(base + "/T_Concreto_BC_Test")
    w("TEX " + str(tex))
    if tex:
        for prop in ["srgb", "compression_settings", "lod_group", "mip_gen_settings", "never_stream", "address_x", "address_y"]:
            try:
                w("TEX PROP " + prop + " = " + str(tex.get_editor_property(prop)))
            except Exception as e:
                w("TEX PROP EXC " + prop + " " + repr(e))
        for prop, val in [("srgb", False), ("compression_settings", unreal.TextureCompressionSettings.TC_MASKS),
                          ("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD), ("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)]:
            try:
                tex.set_editor_property(prop, val)
                w("TEX SET " + prop + " OK -> " + str(tex.get_editor_property(prop)))
            except Exception as e:
                w("TEX SET EXC " + prop + " " + repr(e))
        unreal.EditorAssetLibrary.save_asset(tex.get_path_name())
    # FBX
    fbx = os.path.join(root, "Assets", "Models", "UE5_StaticMeshes", "SM_Trinchera_Recta_4m.fbx")
    w("FBX exists=" + str(os.path.exists(fbx)))
    task2 = unreal.AssetImportTask()
    task2.filename = fbx
    task2.destination_path = base
    task2.destination_name = "SM_Trinchera_Recta_4m_Test"
    task2.automated = True
    task2.save = True
    task2.replace_existing = True
    f = unreal.FbxImportUI()
    f.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    f.import_mesh = True
    f.import_materials = True
    f.import_textures = False
    f.static_mesh_import_data.set_editor_property("combine_meshes", True)
    f.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    f.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    task2.factory = f
    at.import_asset_tasks([task2])
    w("FBX RESULT " + str(task2.imported_object_paths))
    sm = unreal.EditorAssetLibrary.load_asset(base + "/SM_Trinchera_Recta_4m_Test")
    w("SM " + str(sm))
    if sm:
        w("SM DIR " + str([x for x in dir(sm) if not x.startswith("_")]))
        try:
            w("BOUNDS " + str(sm.get_bounding_box()))
        except Exception as e:
            w("BOUNDS EXC " + repr(e))
        try:
            w("MATS " + str([str(m) for m in sm.get_editor_property("static_materials")]))
        except Exception as e:
            w("MATS EXC " + repr(e))
        try:
            w("SIMPLE COL " + str(unreal.StaticMeshEditorSubsystem().get_simple_collision_count(sm)))
        except Exception as e:
            w("SIMPLE COL EXC " + repr(e))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
