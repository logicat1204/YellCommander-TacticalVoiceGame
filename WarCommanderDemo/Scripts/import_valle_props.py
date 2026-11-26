"""Import Valle Alfa props with Unreal's Python commandlet.

Pass -ini:Engine:[ConsoleVariables]:Interchange.FeatureFlags.Import.FBX=0
so the commandlet applies the legacy FBX import options below.
"""

import os
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).parent
PACK = ROOT / "Assets" / "OperacionVoz_Props_P1" / "OperacionVoz_Props_P1"
SCREENS = Path(os.environ["YELL_PROP_SCREENS"])
MODELS = "/Game/Yell/Art/Models/Props"
TEXTURES = "/Game/Yell/Art/Textures/Props"
MATERIALS = "/Game/Yell/Art/Materials/Props"
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
EDIT = unreal.MaterialEditingLibrary
ASSETS = unreal.EditorAssetLibrary


def imported(source, folder, factory, options=None):
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = folder
    task.destination_name = source.stem
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.factory = factory
    if options is not None:
        task.options = options
    TOOLS.import_asset_tasks([task])
    path = folder + "/" + source.stem
    asset = ASSETS.load_asset(path)
    if asset is None or not task.imported_object_paths:
        raise RuntimeError(f"Import failed for {source}")
    return asset


def save(asset):
    if not ASSETS.save_asset(asset.get_path_name(), only_if_is_dirty=False):
        raise RuntimeError(f"Could not save {asset.get_path_name()}")


def texture(name, source, is_color=True, atlas=False):
    asset = imported(source / f"{name}.png", TEXTURES, unreal.TextureFactory())
    asset.set_editor_property("srgb", is_color)
    if not is_color:
        asset.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_MASKS)
    if atlas:
        asset.set_editor_property("filter", unreal.TextureFilter.TF_NEAREST)
    save(asset)
    return asset


def material(name):
    asset = ASSETS.load_asset(MATERIALS + "/" + name) if ASSETS.does_asset_exist(MATERIALS + "/" + name) else None
    if asset is None:
        asset = TOOLS.create_asset(name, MATERIALS, unreal.Material, unreal.MaterialFactoryNew())
    else:
        EDIT.delete_all_material_expressions(asset)
    return asset


def node(asset, kind, x, y):
    return EDIT.create_material_expression(asset, kind, x, y)


def sample(asset, tex, y, param=None, masks=False):
    kind = unreal.MaterialExpressionTextureSampleParameter2D if param else unreal.MaterialExpressionTextureSample
    expression = node(asset, kind, -560, y)
    expression.set_editor_property("texture", tex)
    if param:
        expression.set_editor_property("parameter_name", param)
    if masks:
        expression.set_editor_property("sampler_type", unreal.MaterialSamplerType.SAMPLERTYPE_MASKS)
    return expression


def emit(asset, sample_node, gain, y):
    expression = node(asset, unreal.MaterialExpressionMultiply, -250, y)
    expression.set_editor_property("const_b", gain)
    EDIT.connect_material_expressions(sample_node, "RGB", expression, "A")
    EDIT.connect_material_property(expression, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)


def finish(asset):
    EDIT.recompile_material(asset)
    save(asset)


def build_ground_material():
    ground = material("M_Valle_Suelo")
    world = node(ground, unreal.MaterialExpressionWorldPosition, -1200, 0)
    xy = node(ground, unreal.MaterialExpressionComponentMask, -1000, 0)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    uv = node(ground, unreal.MaterialExpressionDivide, -790, 0)
    uv.set_editor_property("const_b", 570.0)
    EDIT.connect_material_expressions(world, "", xy, "")
    EDIT.connect_material_expressions(xy, "", uv, "A")

    tileable = "/Game/Yell/Art/Textures/Tileable/"
    color = sample(ground, ASSETS.load_asset(tileable + "T_Tierra_BC"), 0)
    orm = sample(ground, ASSETS.load_asset(tileable + "T_Tierra_ORM"), 250, masks=True)
    for channel in (color, orm):
        EDIT.connect_material_expressions(uv, "", channel, "UVs")
    EDIT.connect_material_property(orm, "G", unreal.MaterialProperty.MP_ROUGHNESS)
    EDIT.connect_material_property(orm, "R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)
    layout = node(ground, unreal.MaterialExpressionVectorParameter, -920, -350)
    layout.set_editor_property("parameter_name", "Vias")
    layout.set_editor_property("default_value", unreal.LinearColor(4500.0, 570.0, 11100.0, 12860.0))
    crossing = node(ground, unreal.MaterialExpressionScalarParameter, -920, -510)
    crossing.set_editor_property("parameter_name", "CruceInterior")
    crossing.set_editor_property("default_value", 5600.0)
    mask = node(ground, unreal.MaterialExpressionCustom, -670, -430)
    mask.set_editor_property("code", """
float x = abs(WorldXY.x);
float y = abs(WorldXY.y);
float middle = min(Layout.a - x, Layout.g - y);
float flank = min(Layout.b + Layout.g - x, Layout.g - abs(y - Layout.r));
float distanceToCrossing = min(x, min(abs(x - InnerCrossing), abs(x - Layout.b)));
float cross = min(Layout.g - distanceToCrossing, Layout.r - y);
float erosion = 21.0 * sin(WorldXY.x * .029) * sin(WorldXY.y * .025);
return smoothstep(-25.0, 50.0, max(middle, max(flank, cross)) + erosion);
""")
    connections = (("WorldXY", xy, ""), ("Layout", layout, "RGBA"), ("InnerCrossing", crossing, ""))
    inputs = []
    for name, _, _ in connections:
        parameter = unreal.CustomInput()
        parameter.set_editor_property("input_name", name)
        inputs.append(parameter)
    mask.set_editor_property("inputs", inputs)
    for name, expression, output in connections:
        if not EDIT.connect_material_expressions(expression, output, mask, name):
            raise RuntimeError(f"Could not connect the road material's {name} input")
    tint = node(ground, unreal.MaterialExpressionLinearInterpolate, -435, -290)
    for label, color_value in (
        ("A", unreal.LinearColor(0.71, 0.72, 0.62, 1.0)),
        ("B", unreal.LinearColor(1.10, 1.03, 0.83, 1.0)),
    ):
        constant = node(ground, unreal.MaterialExpressionConstant3Vector, -680, -130 if label == "A" else -35)
        constant.set_editor_property("constant", color_value)
        EDIT.connect_material_expressions(constant, "", tint, label)
    EDIT.connect_material_expressions(mask, "", tint, "Alpha")
    colored = node(ground, unreal.MaterialExpressionMultiply, -230, -80)
    EDIT.connect_material_expressions(color, "RGB", colored, "A")
    EDIT.connect_material_expressions(tint, "", colored, "B")
    EDIT.connect_material_property(colored, "", unreal.MaterialProperty.MP_BASE_COLOR)
    finish(ground)


build_ground_material()

source = PACK / "Textures"
base = texture("T_Props_BC", source, atlas=True)
orm = texture("T_Props_ORM", source, is_color=False, atlas=True)
emissive = texture("T_Props_E", source, atlas=True)
screen_ready = texture("T_Terminal_Pantalla_Activa", SCREENS)
texture("T_Terminal_Pantalla_Alerta", SCREENS)
texture("T_Terminal_Pantalla_Apagada", source)

props = material("M_Valle_Props")
EDIT.connect_material_property(sample(props, base, 0), "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
surface = sample(props, orm, 240, masks=True)
for output, prop in (
    ("R", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION),
    ("G", unreal.MaterialProperty.MP_ROUGHNESS),
    ("B", unreal.MaterialProperty.MP_METALLIC),
):
    EDIT.connect_material_property(surface, output, prop)
emit(props, sample(props, emissive, 480), 2.0, 480)
props.set_editor_property("two_sided", True)
finish(props)

screen = material("M_Valle_Terminal")
screen.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
screen.set_editor_property("two_sided", True)
emit(screen, sample(screen, screen_ready, 0, param="Pantalla"), 1.25, 0)
finish(screen)

for name, expected_height in (
    ("SM_Tienda_Militar", 221.0), ("SM_Terminal_Refuerzos", 153.0), ("SM_Mastil_Radio", 629.0),
    ("SM_Cajas_Municion_Pila", 71.0), ("SM_Barril_Combustible", 90.0), ("SM_Alambrada_4m", 116.0),
):
    options = unreal.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials = False
    options.import_textures = False
    settings = options.static_mesh_import_data
    settings.auto_generate_collision = False
    settings.combine_meshes = True
    # This FBX pack stores metre-sized vertex coordinates even with its unit metadata.
    settings.convert_scene_unit = False
    settings.import_uniform_scale = 100.0
    path = MODELS + "/" + name
    if ASSETS.does_asset_exist(path):
        previous = ASSETS.load_asset(path).get_editor_property("asset_import_data")
        if isinstance(previous, unreal.FbxStaticMeshImportData):
            previous.convert_scene_unit = settings.convert_scene_unit
            previous.import_uniform_scale = settings.import_uniform_scale
    mesh = imported(PACK / "Models" / "UE5_StaticMeshes" / f"{name}.fbx", MODELS, unreal.FbxFactory(), options)
    slots = mesh.get_editor_property("static_materials")
    num_screens = 0
    for index, slot in enumerate(slots):
        is_screen = "pantalla" in str(slot.get_editor_property("imported_material_slot_name")).lower()
        mesh.set_material(index, screen if is_screen else props)
        num_screens += int(is_screen)
    if name == "SM_Terminal_Refuerzos" and num_screens != 1:
        raise RuntimeError(f"Expected one terminal screen, found {num_screens}")
    hulls = unreal.StaticMeshEditorSubsystem().get_convex_collision_count(mesh)
    if hulls <= 0:
        raise RuntimeError(f"Missing collision setup for {name}")
    bounds = mesh.get_bounding_box()
    size = bounds.max - bounds.min
    unreal.log(f"Valle prop size: {name}, {size.x:.1f} x {size.y:.1f} x {size.z:.1f} cm, {hulls} hulls")
    if abs(size.z - expected_height) > expected_height * 0.12:
        raise RuntimeError(f"Expected {expected_height} cm for {name}, imported {size.z:.2f} cm")
    save(mesh)
    unreal.log(f"Valle prop ready: {name}, {len(slots)} material slots")
