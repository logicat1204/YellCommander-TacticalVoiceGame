"""Import every Operacion Voz source asset into /Game/Yell/Art.

Run with:
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<this file>"

Writes a report to Saved/yell_art_import.txt (Python print does not reach the
commandlet log).
"""
import os
import traceback

import unreal

PROJECT = unreal.Paths.project_dir()
ROOT = os.path.abspath(os.path.join(PROJECT, ".."))
ART = "/Game/Yell/Art"
REPORT = os.path.join(PROJECT, "Saved", "yell_art_import.txt")

LINES = []


def log(text):
    LINES.append(str(text))


DIRS = [
    "Textures/Tileable",
    "Textures/Soldado",
    "Textures/Armas",
    "Textures/Terrain",
    "Textures/UI/Kit",
    "Textures/UI/Icons",
    "Textures/UI/Markers",
    "Textures/UI/Mic",
    "Textures/UI/Mockups",
    "Textures/VFX",
    "Models/Static",
    "Models/Characters",
    "Models/Terrain",
    "Materials/Master",
    "Materials/Instances/Tileable",
    "Materials/Instances/Teams",
    "Materials/Instances/HUD",
    "Materials/Instances/VFX",
    "Materials/Instances/Terrain",
    "VFX",
    "Levels",
    "Presentation",
    "UI/Fonts",
]

# ---------------------------------------------------------------- helpers


def ensure_dirs():
    for rel in DIRS:
        path = ART + "/" + rel
        if not unreal.EditorAssetLibrary.does_directory_exist(path):
            unreal.EditorAssetLibrary.make_directory(path)
        log("DIR " + path)


def apply_texture_settings(tex, srgb, compression, group, mips):
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("compression_settings", compression)
    tex.set_editor_property("lod_group", group)
    tex.set_editor_property("mip_gen_settings", mips)
    try:
        tex.set_editor_property("never_stream", True)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(tex.get_path_name(), only_if_is_dirty=False)


def import_texture(src, dest, name, srgb, compression, group, mips):
    try:
        return _import_texture(src, dest, name, srgb, compression, group, mips)
    except Exception:
        log("TEX EXC %s\n%s" % (name, traceback.format_exc()))
        return None


def _import_texture(src, dest, name, srgb, compression, group, mips):
    if not os.path.isfile(src):
        log("MISSING TEX " + src)
        return None
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = dest
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.TextureFactory()
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([task])
    path = dest + "/" + name
    tex = unreal.EditorAssetLibrary.load_asset(path)
    if tex is None:
        log("FAIL TEX " + src)
        return None
    apply_texture_settings(tex, srgb, compression, group, mips)
    log("TEX %s -> %s [srgb=%s comp=%s group=%s]" % (
        os.path.basename(src), path, srgb, compression, group))
    return tex


def import_static(src, dest, name, kind="static"):
    try:
        return _import_static(src, dest, name, kind)
    except Exception:
        log("MESH EXC %s\n%s" % (name, traceback.format_exc()))
        return None


def _import_static(src, dest, name, kind="static"):
    if not os.path.isfile(src):
        log("MISSING MESH " + src)
        return None
    task = unreal.AssetImportTask()
    task.filename = src
    task.destination_path = dest
    task.destination_name = name
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
    task.options = options
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([task])
    path = dest + "/" + name
    mesh = unreal.EditorAssetLibrary.load_asset(path)
    if mesh is None:
        log("FAIL MESH " + src)
        return None
    box = mesh.get_bounding_box()
    size = box.max - box.min
    log("MESH %-34s -> %s  class=%s size=(%.1f, %.1f, %.1f) cm" % (
        os.path.basename(src), path, mesh.get_class().get_name(), size.x, size.y, size.z))
    if kind == "character":
        # Cosmetic T-pose only: the FBX carries no skeleton, so the importer
        # produces a StaticMesh.  Keep the scale proof in the report.
        log("     character height %.2f cm (target 180)" % size.z)
    return mesh


# ---------------------------------------------------------------- main

try:
    ensure_dirs()

    # ---- tileable PBR sets --------------------------------------------
    tile = os.path.join(ROOT, "Assets", "Textures", "Tileable")
    for stem in ["T_Concreto", "T_Metal", "T_Pasto", "T_Roca", "T_Saco", "T_Tierra"]:
        import_texture(os.path.join(tile, stem + "_BC.png"), ART + "/Textures/Tileable",
                       stem + "_BC", True,
                       unreal.TextureCompressionSettings.TC_DEFAULT,
                       unreal.TextureGroup.TEXTUREGROUP_WORLD,
                       unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        import_texture(os.path.join(tile, stem + "_N.png"), ART + "/Textures/Tileable",
                       stem + "_N", False,
                       unreal.TextureCompressionSettings.TC_NORMALMAP,
                       unreal.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP,
                       unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
        import_texture(os.path.join(tile, stem + "_ORM.png"), ART + "/Textures/Tileable",
                       stem + "_ORM", False,
                       unreal.TextureCompressionSettings.TC_MASKS,
                       unreal.TextureGroup.TEXTUREGROUP_WORLD,
                       unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)

    # ---- character + weapon palettes ----------------------------------
    soldier = os.path.join(ROOT, "Assets", "Textures", "Soldado")
    for name in ["T_Soldado_Alpha_BC", "T_Soldado_Bravo_BC",
                 "T_Soldado_Enemigo_BC", "T_Soldado_Medico_BC", "T_Soldado_ORM"]:
        import_texture(os.path.join(soldier, name + ".png"), ART + "/Textures/Soldado",
                       name, True,
                       unreal.TextureCompressionSettings.TC_DEFAULT,
                       unreal.TextureGroup.TEXTUREGROUP_WORLD,
                       unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)

    arms = os.path.join(ROOT, "Assets", "Textures", "Armas")
    for name in ["T_Armas_BC", "T_Armas_ORM"]:
        import_texture(os.path.join(arms, name + ".png"), ART + "/Textures/Armas",
                       name, True,
                       unreal.TextureCompressionSettings.TC_DEFAULT,
                       unreal.TextureGroup.TEXTUREGROUP_WORLD,
                       unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)

    # ---- terrain weight maps + minimap --------------------------------
    layers = os.path.join(ROOT, "Assets", "Terrain", "Layers")
    for name in ["L_Pasto", "L_Tierra", "L_Roca"]:
        import_texture(os.path.join(layers, name + ".png"), ART + "/Textures/Terrain",
                       name, False,
                       unreal.TextureCompressionSettings.TC_GRAYSCALE,
                       unreal.TextureGroup.TEXTUREGROUP_TERRAIN_WEIGHTMAP,
                       unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    terrain = os.path.join(ROOT, "Assets", "Terrain")
    import_texture(os.path.join(terrain, "T_Minimapa_ValleAlfa.png"),
                   ART + "/Textures/Terrain", "T_Minimapa_ValleAlfa", True,
                   unreal.TextureCompressionSettings.TC_DEFAULT,
                   unreal.TextureGroup.TEXTUREGROUP_UI,
                   unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    import_texture(os.path.join(terrain, "Referencia_Zonas_ValleAlfa.png"),
                   ART + "/Textures/Terrain", "T_Referencia_Zonas_ValleAlfa", True,
                   unreal.TextureCompressionSettings.TC_DEFAULT,
                   unreal.TextureGroup.TEXTUREGROUP_UI,
                   unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    import_texture(os.path.join(terrain, "Heightmap_ValleAlfa_1009.png"),
                   ART + "/Textures/Terrain", "T_Heightmap_ValleAlfa", False,
                   unreal.TextureCompressionSettings.TC_GRAYSCALE,
                   unreal.TextureGroup.TEXTUREGROUP_UI,
                   unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    # ---- UI kit / icons / markers / mic -------------------------------
    ui = os.path.join(ROOT, "Assets", "UI")
    kit = os.path.join(ui, "Kit")
    for entry in sorted(os.listdir(kit)):
        if entry.lower().endswith(".png"):
            import_texture(os.path.join(kit, entry), ART + "/Textures/UI/Kit",
                           os.path.splitext(entry)[0], True,
                           unreal.TextureCompressionSettings.TC_DEFAULT,
                           unreal.TextureGroup.TEXTUREGROUP_UI,
                           unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    for folder, dest in [("Icons", "Icons"), ("Markers", "Markers"), ("Mic", "Mic")]:
        src_dir = os.path.join(ui, folder)
        for entry in sorted(os.listdir(src_dir)):
            if entry.lower().endswith(".png"):
                import_texture(os.path.join(src_dir, entry),
                               ART + "/Textures/UI/" + dest,
                               os.path.splitext(entry)[0], True,
                               unreal.TextureCompressionSettings.TC_DEFAULT,
                               unreal.TextureGroup.TEXTUREGROUP_UI,
                               unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    # ---- UI mockup composed from the kit (make_hud_mockup.py) ----------
    mockups = os.path.join(ui, "Mockups")
    if os.path.isdir(mockups):
        for entry in sorted(os.listdir(mockups)):
            if entry.lower().endswith(".png"):
                import_texture(os.path.join(mockups, entry),
                               ART + "/Textures/UI/Mockups",
                               os.path.splitext(entry)[0], True,
                               unreal.TextureCompressionSettings.TC_DEFAULT,
                               unreal.TextureGroup.TEXTUREGROUP_UI,
                               unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    # ---- VFX sprites ---------------------------------------------------
    vfx = os.path.join(ROOT, "Assets", "VFX", "Textures")
    for entry in sorted(os.listdir(vfx)):
        if entry.lower().endswith(".png"):
            import_texture(os.path.join(vfx, entry), ART + "/Textures/VFX",
                           os.path.splitext(entry)[0], True,
                           unreal.TextureCompressionSettings.TC_DEFAULT,
                           unreal.TextureGroup.TEXTUREGROUP_EFFECTS,
                           unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)

    # ---- fonts ---------------------------------------------------------
    # FontFileImportFactory needs an interactive Slate application and hard
    # crashes in -run=pythonscript, so the TTFs stay as source files and the
    # widget request (Docs/ENTREGA_UI.md) references them for the editor step.
    log("FONT skip (FontFileImportFactory requires Slate; import manually)")

    # ---- static meshes -------------------------------------------------
    static = os.path.join(ROOT, "Assets", "Models", "UE5_StaticMeshes")
    for entry in sorted(os.listdir(static)):
        if entry.lower().endswith(".fbx"):
            import_static(os.path.join(static, entry), ART + "/Models/Static",
                          os.path.splitext(entry)[0])

    # ---- characters (T-pose, no skeleton in the FBX) -------------------
    chars = os.path.join(ROOT, "Assets", "Models", "Mixamo_Upload", "Extracted")
    for entry in sorted(os.listdir(chars)):
        if entry.lower().endswith(".fbx"):
            import_static(os.path.join(chars, entry), ART + "/Models/Characters",
                          os.path.splitext(entry)[0], kind="character")

    # ---- terrain mesh --------------------------------------------------
    terrain_obj = os.path.join(ROOT, "Assets", "Models", "Generated", "SM_Terreno_ValleAlfa.obj")
    import_static(terrain_obj, ART + "/Models/Terrain", "SM_Terreno_ValleAlfa")

    unreal.EditorAssetLibrary.save_directory(ART, only_if_is_dirty=False, recursive=True)
    log("DONE")
except Exception:
    log("EXCEPTION\n" + traceback.format_exc())
finally:
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as handle:
        handle.write("\n".join(LINES))
