"""Import the supplied Yell Commander logo and compose it over the live menu."""

from pathlib import Path

import unreal


root = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).parent
folder = "/Game/Yell/Art/Textures/UI/Brand"
material_folder = "/Game/Yell/Art/Materials/HUD"
source = root / "Assets" / "UI" / "T_YellCommander_Original.png"
assets = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
edit = unreal.MaterialEditingLibrary

task = unreal.AssetImportTask()
task.filename = str(source)
task.destination_path = folder
task.destination_name = source.stem
task.automated = True
task.replace_existing = True
task.factory = unreal.TextureFactory()
tools.import_asset_tasks([task])
texture = assets.load_asset(folder + "/" + source.stem)
if texture is None:
    raise RuntimeError(f"Could not import {source}")
texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
assets.save_asset(texture.get_path_name(), only_if_is_dirty=False)

name = "M_UI_YellCommander"
path = material_folder + "/" + name
logo = assets.load_asset(path) if assets.does_asset_exist(path) else None
if logo is None:
    logo = tools.create_asset(name, material_folder, unreal.Material, unreal.MaterialFactoryNew())
else:
    edit.delete_all_material_expressions(logo)
logo.set_editor_property("material_domain", unreal.MaterialDomain.MD_UI)
logo.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)


def node(expression, x, y):
    return edit.create_material_expression(logo, expression, x, y)


def custom(kind, inputs, code, x, y):
    expression = node(unreal.MaterialExpressionCustom, x, y)
    expression.set_editor_property("output_type", kind)
    pins = []
    for pin, _, _ in inputs:
        entry = unreal.CustomInput()
        entry.set_editor_property("input_name", pin)
        pins.append(entry)
    expression.set_editor_property("inputs", pins)
    expression.set_editor_property("code", code)
    for pin, previous, output in inputs:
        if not edit.connect_material_expressions(previous, output, expression, pin):
            raise RuntimeError(f"Could not connect logo input {pin}")
    return expression


coords = node(unreal.MaterialExpressionTextureCoordinate, -940, -90)
crop = custom(unreal.CustomMaterialOutputType.CMOT_FLOAT2, [("UV", coords, "")],
              "return float2(0.026, 0.120) + UV * float2(0.948, 0.592);", -720, -90)
sample = node(unreal.MaterialExpressionTextureSample, -475, -90)
sample.set_editor_property("texture", texture)
edit.connect_material_expressions(crop, "", sample, "UVs")
opacity = custom(unreal.CustomMaterialOutputType.CMOT_FLOAT1, [("LogoRGB", sample, "RGB")],
                 "return smoothstep(0.010, 0.042, length(LogoRGB - float3(0.0103, 0.0176, 0.0137)));",
                 -240, 170)
edit.connect_material_property(sample, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
edit.connect_material_property(opacity, "", unreal.MaterialProperty.MP_OPACITY)
edit.recompile_material(logo)
if not assets.save_asset(logo.get_path_name(), only_if_is_dirty=False):
    raise RuntimeError("Could not save Yell Commander logo material")
unreal.log(f"Yell menu brand ready: {logo.get_path_name()}")
