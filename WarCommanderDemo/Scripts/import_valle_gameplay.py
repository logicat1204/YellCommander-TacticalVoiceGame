"""Import the skeletal character kits and HUD sprites used by Valle Alfa."""
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2] / "Assets"
ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
DEST = "/Game/Yell/Gameplay"


def load_or_import(source, folder, name, factory, options=None, replace=False):
    path = f"{folder}/{name}"
    if not replace and ASSETS.does_asset_exist(path):
        return ASSETS.load_asset(path)
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.save = True
    task.replace_existing = replace
    task.factory = factory
    if options:
        task.options = options
    TOOLS.import_asset_tasks([task])
    return ASSETS.load_asset(path)


def import_characters():
    sources = ROOT / "Models" / "Assets de soldados con animaciones USAR"
    for role, walk, pose in (("Aliado", "Walk Forward", "Idle Aiming"),
                             ("Enemigo", "Walk Forward", "Idle Aiming"),
                             ("Medico", "Walking", "Helping Out")):
        source = sources / f"SK_Soldado_{role}_Mixamo+animations"
        folder = f"{DEST}/Characters/{role}"
        settings = unreal.FbxImportUI()
        settings.automated_import_should_detect_type = False
        settings.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
        settings.import_as_skeletal = True
        settings.import_materials = False
        settings.import_textures = False
        settings.import_animations = False
        settings.create_physics_asset = False
        mesh_path = f"{folder}/SK_{role}"
        existing = ASSETS.load_asset(mesh_path) if ASSETS.does_asset_exist(mesh_path) else None
        repair = not existing or not existing.get_editor_property("skeleton")
        mesh = load_or_import(source / "Dying_with_skin.fbx", folder, f"SK_{role}", unreal.FbxFactory(), settings, repair)
        if not isinstance(mesh, unreal.SkeletalMesh):
            raise RuntimeError(f"SkeletalMesh no importado: {role}")
        skeleton = mesh.get_editor_property("skeleton")
        if not skeleton or not ASSETS.save_loaded_asset(skeleton, only_if_is_dirty=False):
            raise RuntimeError(f"Esqueleto no guardado: {role}")
        ASSETS.save_loaded_asset(mesh, only_if_is_dirty=False)
        unreal.log(f"VALLE skeleton {role}: {skeleton.get_path_name()}")
        clips = [("Caminar", source / f"{walk}.fbx"), ("Postura", source / f"{pose}.fbx"),
                 ("Caer", source / "Dying_with_skin.fbx")]
        if role == "Medico":
            clips.append(("Alerta", sources / "SK_Soldado_Aliado_Mixamo+animations" / "Idle Aiming.fbx"))
        for asset, filename in clips:
            settings = unreal.FbxImportUI()
            settings.automated_import_should_detect_type = False
            settings.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
            settings.import_mesh = False
            settings.import_animations = True
            settings.import_materials = False
            settings.import_textures = False
            settings.skeleton = skeleton
            clip = load_or_import(filename, folder, f"A_{asset}", unreal.FbxFactory(), settings, repair)
            if not isinstance(clip, unreal.AnimSequence):
                raise RuntimeError(f"Animación no importada: {role}/{asset}")
            clip.set_editor_property("force_root_lock", asset != "Caer")
            ASSETS.save_loaded_asset(clip)
            unreal.log(f"VALLE animation {role}/{asset}: {clip.get_play_length():.2f}s")


def import_hud():
    selected = {
        "T_Heart_Sano", "T_Heart_Herido", "T_Heart_Critico", "T_Comm_Glifo_Walkie", "T_Comm_Glifo_Habla",
        "T_MM_Fondo_Circular", "T_MM_Marco_Circular", "T_MM_Soldado_Bravo", "T_MM_Soldado_Alpha",
        "T_MM_Jugador", "T_MM_Medico", "T_MM_Estructura_BaseAliada", "T_MM_Estructura_BaseEnemiga",
    }
    for source in sorted((ROOT / "OperacionVoz_HUD_Assets").rglob("*.png")):
        if source.stem not in selected:
            continue
        tex = load_or_import(source, f"{DEST}/HUD", source.stem, unreal.TextureFactory())
        if not tex:
            raise RuntimeError(f"Textura no importada: {source.name}")
        tex.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        tex.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        ASSETS.save_loaded_asset(tex)


import_hud()
import_characters()
soldier_material = ASSETS.load_asset("/Game/Yell/Art/Materials/Master/M_Soldado")
soldier_material.set_editor_property("used_with_skeletal_mesh", True)
unreal.MaterialEditingLibrary.recompile_material(soldier_material)
ASSETS.save_loaded_asset(soldier_material, only_if_is_dirty=False)
unreal.log("VALLE gameplay import complete")
