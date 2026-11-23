import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_scale_probe.txt")
lines = []
def w(s):
    lines.append(str(s))

def imp_static(at, src, base, name, scale=1.0, convert=True):
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = base
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.FbxFactory()
    f = unreal.FbxImportUI()
    f.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    f.import_mesh = True
    f.import_materials = False
    f.import_textures = False
    f.static_mesh_import_data.set_editor_property("combine_meshes", True)
    f.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    f.static_mesh_import_data.set_editor_property("generate_lightmap_u_vs", False)
    f.static_mesh_import_data.set_editor_property("convert_scene_unit", convert)
    f.static_mesh_import_data.set_editor_property("import_uniform_scale", scale)
    task.options = f
    at.import_asset_tasks([task])
    return task.imported_object_paths

try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    base = "/Game/Yell/Art/_ScaleProbe"
    unreal.EditorAssetLibrary.make_directory(base)
    root = os.path.abspath(os.path.join(unreal.Paths.project_dir(), ".."))
    tri = os.path.join(root, "Assets", "Models", "UE5_StaticMeshes", "SM_Trinchera_Recta_4m.fbx")
    sol = os.path.join(root, "Assets", "Models", "Mixamo_Upload", "Extracted", "SK_Soldado_Aliado_TPose.fbx")

    for label, src, name, scale, convert in [
        ("tri_c1", tri, "SM_Tri_C1", 1.0, True),
        ("tri_s100", tri, "SM_Tri_S100", 100.0, False),
        ("sol_c1", sol, "SK_Sol_C1", 1.0, True),
        ("sol_s100", sol, "SK_Sol_S100", 100.0, False),
    ]:
        paths = imp_static(at, src, base, name, scale, convert)
        w(label + " PATHS " + str(paths))
        obj = unreal.EditorAssetLibrary.load_asset(paths[0]) if paths else None
        if obj:
            b = obj.get_bounding_box()
            w(label + " CLASS " + obj.get_class().get_name())
            w(label + " BOUNDS min=" + str(b.min) + " max=" + str(b.max) + " size=" + str(b.max - b.min))
            try:
                w(label + " COL complex=" + str(unreal.StaticMeshEditorSubsystem().get_collision_complexity(obj)) +
                  " simple=" + str(unreal.StaticMeshEditorSubsystem().get_simple_collision_count(obj)) +
                  " convex=" + str(unreal.StaticMeshEditorSubsystem().get_convex_collision_count(obj)))
            except Exception as e:
                w(label + " COL EXC " + repr(e))
            try:
                w(label + " TRIS " + str(obj.get_num_triangles(0)) + " VERTS " + str(obj.get_num_vertices(0)) + " UV " + str(obj.get_num_tex_coords(0)))
            except Exception as e:
                w(label + " TRIS EXC " + repr(e))
    # textures
    for label, fn, settings in [
        ("bc", "T_Concreto_BC.png", (True, unreal.TextureCompressionSettings.TC_DEFAULT, unreal.TextureGroup.TEXTUREGROUP_WORLD, unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)),
        ("n", "T_Concreto_N.png", (False, unreal.TextureCompressionSettings.TC_NORMALMAP, unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP, unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)),
        ("orm", "T_Concreto_ORM.png", (False, unreal.TextureCompressionSettings.TC_MASKS, unreal.TextureGroup.TEXTUREGROUP_WORLD, unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)),
    ]:
        src = os.path.join(root, "Assets", "Textures", "Tileable", fn)
        t = unreal.AssetImportTask()
        t.filename = src
        t.destination_path = base
        t.destination_name = "T_Test_" + label
        t.automated = True
        t.save = True
        t.replace_existing = True
        t.factory = unreal.TextureFactory()
        at.import_asset_tasks([t])
        tex = unreal.EditorAssetLibrary.load_asset(base + "/T_Test_" + label)
        w("TEX " + label + " " + str(tex))
        if tex:
            tex.set_editor_property("srgb", settings[0])
            tex.set_editor_property("compression_settings", settings[1])
            tex.set_editor_property("lod_group", settings[2])
            tex.set_editor_property("mip_gen_settings", settings[3])
            unreal.EditorAssetLibrary.save_asset(tex.get_path_name())
            w("TEX " + label + " srgb=" + str(tex.get_editor_property("srgb")) + " comp=" + str(tex.get_editor_property("compression_settings")) + " lod=" + str(tex.get_editor_property("lod_group")) + " mips=" + str(tex.get_editor_property("mip_gen_settings")))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
