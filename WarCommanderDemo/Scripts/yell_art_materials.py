"""Build the Operacion Voz master materials and material instances.

Everything lands under /Game/Yell/Art/Materials.  Run headless:
  UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script="<this file>"
"""
import os
import traceback

import unreal

ART = "/Game/Yell/Art"
MAT = ART + "/Materials"
PROJECT = unreal.Paths.project_dir()
REPORT = os.path.join(PROJECT, "Saved", "yell_art_materials.txt")

LINES = []


def log(text):
    LINES.append(str(text))


MEL = unreal.MaterialEditingLibrary
AT = unreal.AssetToolsHelpers.get_asset_tools()


def tex(path):
    return unreal.EditorAssetLibrary.load_asset(path)


def new_material(name, domain=None, blend=None, shading=None):
    path = MAT + "/Master/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    mat = AT.create_asset(name, MAT + "/Master", unreal.Material, unreal.MaterialFactoryNew())
    if domain is not None:
        mat.set_editor_property("material_domain", domain)
    if blend is not None:
        mat.set_editor_property("blend_mode", blend)
    if shading is not None:
        mat.set_editor_property("shading_model", shading)
    return mat


def expr(mat, klass, x, y):
    return MEL.create_material_expression(mat, klass, x, y)


def tex_param(mat, name, texture, x, y):
    node = expr(mat, unreal.MaterialExpressionTextureSampleParameter2D, x, y)
    node.set_editor_property("parameter_name", name)
    if texture is not None:
        node.set_editor_property("texture", texture)
    return node


def scalar_param(mat, name, value, x, y):
    node = expr(mat, unreal.MaterialExpressionScalarParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", value)
    return node


def vector_param(mat, name, color, x, y):
    node = expr(mat, unreal.MaterialExpressionVectorParameter, x, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", color)
    return node


def link(mat, src, src_out, dst, dst_in):
    MEL.connect_material_expressions(src, src_out, dst, dst_in)


def out(mat, src, src_out, prop):
    MEL.connect_material_property(src, src_out, prop)


def finish(mat):
    MEL.recompile_material(mat)
    unreal.EditorAssetLibrary.save_asset(mat.get_path_name(), only_if_is_dirty=False)


# ------------------------------------------------------------------ masters

def master_surface():
    mat = new_material("M_Superficie", unreal.MaterialDomain.MD_SURFACE)
    uv = expr(mat, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    tile = scalar_param(mat, "UVTile", 1.0, -900, 120)
    mul_uv = expr(mat, unreal.MaterialExpressionMultiply, -700, 20)
    link(mat, uv, "", mul_uv, "A")
    link(mat, tile, "", mul_uv, "B")

    bc = tex_param(mat, "BaseColor", tex(ART + "/Textures/Tileable/T_Concreto_BC"), -500, -300)
    nrm = tex_param(mat, "Normal", tex(ART + "/Textures/Tileable/T_Concreto_N"), -500, 40)
    orm = tex_param(mat, "ORM", tex(ART + "/Textures/Tileable/T_Concreto_ORM"), -500, 380)
    for node in (bc, nrm, orm):
        link(mat, mul_uv, "", node, "UVs")

    tint = vector_param(mat, "Tint", unreal.LinearColor(1.0, 1.0, 1.0, 1.0), -500, -560)
    tinted = expr(mat, unreal.MaterialExpressionMultiply, -230, -300)
    link(mat, bc, "RGB", tinted, "A")
    link(mat, tint, "", tinted, "B")
    out(mat, tinted, "", unreal.MaterialProperty.MP_BASE_COLOR)
    out(mat, nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)

    ao = expr(mat, unreal.MaterialExpressionComponentMask, -230, 330)
    ao.set_editor_property("r", True)
    ao.set_editor_property("g", False)
    ao.set_editor_property("b", False)
    ao.set_editor_property("a", False)
    link(mat, orm, "R", ao, "")
    out(mat, ao, "", unreal.MaterialProperty.MP_AMBIENT_OCCLUSION)

    rough_scale = scalar_param(mat, "RoughnessScale", 1.0, -500, 620)
    rough = expr(mat, unreal.MaterialExpressionMultiply, -230, 520)
    link(mat, orm, "G", rough, "A")
    link(mat, rough_scale, "", rough, "B")
    out(mat, rough, "", unreal.MaterialProperty.MP_ROUGHNESS)

    metal = expr(mat, unreal.MaterialExpressionComponentMask, -230, 700)
    metal.set_editor_property("r", False)
    metal.set_editor_property("g", False)
    metal.set_editor_property("b", True)
    metal.set_editor_property("a", False)
    link(mat, orm, "B", metal, "")
    out(mat, metal, "", unreal.MaterialProperty.MP_METALLIC)
    finish(mat)
    return mat


def master_simple(name, roughness, metallic, tint_default):
    mat = new_material(name, unreal.MaterialDomain.MD_SURFACE)
    bc = tex_param(mat, "BaseColor", tex(ART + "/Textures/Soldado/T_Soldado_Alpha_BC"), -420, 0)
    tint = vector_param(mat, "Tint", tint_default, -420, -240)
    mul = expr(mat, unreal.MaterialExpressionMultiply, -180, -40)
    link(mat, bc, "RGB", mul, "A")
    link(mat, tint, "", mul, "B")
    out(mat, mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    r = scalar_param(mat, "Roughness", roughness, -420, 240)
    out(mat, r, "", unreal.MaterialProperty.MP_ROUGHNESS)
    m = scalar_param(mat, "Metallic", metallic, -420, 360)
    out(mat, m, "", unreal.MaterialProperty.MP_METALLIC)
    finish(mat)
    return mat


def master_team():
    mat = new_material("M_Equipo", unreal.MaterialDomain.MD_SURFACE)
    color = vector_param(mat, "Color", unreal.LinearColor(0.05, 0.48, 0.60, 1.0), -520, -120)
    out(mat, color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    strength = scalar_param(mat, "EmissiveStrength", 2.5, -520, 200)
    glow = expr(mat, unreal.MaterialExpressionMultiply, -250, 40)
    link(mat, color, "", glow, "A")
    link(mat, strength, "", glow, "B")
    out(mat, glow, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough = scalar_param(mat, "Roughness", 0.35, -520, 340)
    out(mat, rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    finish(mat)
    return mat


def master_ui_icon():
    mat = new_material("M_UI_Icono", unreal.MaterialDomain.MD_UI,
                       unreal.BlendMode.BLEND_TRANSLUCENT,
                       unreal.MaterialShadingModel.MSM_UNLIT)
    sample = tex_param(mat, "Icono", tex(ART + "/Textures/UI/Icons/T_Icon_Atacar"), -520, -60)
    tint = vector_param(mat, "Tint", unreal.LinearColor(1.0, 1.0, 1.0, 1.0), -520, 220)
    opacity = scalar_param(mat, "Opacity", 1.0, -520, 360)
    color = expr(mat, unreal.MaterialExpressionMultiply, -240, -60)
    link(mat, sample, "RGB", color, "A")
    link(mat, tint, "", color, "B")
    out(mat, color, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    alpha = expr(mat, unreal.MaterialExpressionMultiply, -240, 220)
    link(mat, sample, "A", alpha, "A")
    link(mat, opacity, "", alpha, "B")
    out(mat, alpha, "", unreal.MaterialProperty.MP_OPACITY)
    finish(mat)
    return mat


def master_decal(name):
    mat = new_material(name, unreal.MaterialDomain.MD_DEFERRED_DECAL,
                       unreal.BlendMode.BLEND_TRANSLUCENT,
                       unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    sample = tex_param(mat, "Textura", tex(ART + "/Textures/UI/Markers/T_Decal_Seleccion"), -520, -60)
    color = vector_param(mat, "Color", unreal.LinearColor(0.37, 0.63, 1.0, 1.0), -520, 220)
    opacity = scalar_param(mat, "Opacity", 1.0, -520, 360)
    tinted = expr(mat, unreal.MaterialExpressionMultiply, -240, -60)
    link(mat, sample, "RGB", tinted, "A")
    link(mat, color, "", tinted, "B")
    out(mat, tinted, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    alpha = expr(mat, unreal.MaterialExpressionMultiply, -240, 220)
    link(mat, sample, "A", alpha, "A")
    link(mat, opacity, "", alpha, "B")
    out(mat, alpha, "", unreal.MaterialProperty.MP_OPACITY)
    finish(mat)
    return mat


def master_vfx(name, subuv, texture_path):
    mat = new_material(name, unreal.MaterialDomain.MD_SURFACE,
                       unreal.BlendMode.BLEND_TRANSLUCENT,
                       unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    if subuv:
        sample = expr(mat, unreal.MaterialExpressionParticleSubUV, -560, -60)
        sample.set_editor_property("texture", tex(texture_path))
        try:
            sample.set_editor_property("blend", False)
        except Exception:
            pass
        src_rgb, src_a = "RGB", "A"
    else:
        sample = tex_param(mat, "Textura", tex(texture_path), -560, -60)
        src_rgb, src_a = "RGB", "A"
    color = vector_param(mat, "Color", unreal.LinearColor(1.0, 1.0, 1.0, 1.0), -560, 240)
    opacity = scalar_param(mat, "Opacity", 1.0, -560, 380)
    tinted = expr(mat, unreal.MaterialExpressionMultiply, -260, -60)
    link(mat, sample, src_rgb, tinted, "A")
    link(mat, color, "", tinted, "B")
    out(mat, tinted, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    alpha = expr(mat, unreal.MaterialExpressionMultiply, -260, 240)
    link(mat, sample, src_a, alpha, "A")
    link(mat, opacity, "", alpha, "B")
    out(mat, alpha, "", unreal.MaterialProperty.MP_OPACITY)
    finish(mat)
    return mat


def master_cartel():
    """Opaque unlit board material for the art review boards (HUD, icons)."""
    mat = new_material("M_Cartel", unreal.MaterialDomain.MD_SURFACE,
                       unreal.BlendMode.BLEND_OPAQUE,
                       unreal.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property("two_sided", True)
    sample = tex_param(mat, "Textura",
                       tex(ART + "/Textures/UI/Mockups/T_UI_HUD_Referencia_1210x720"),
                       -560, -60)
    color = vector_param(mat, "Color", unreal.LinearColor(1.0, 1.0, 1.0, 1.0), -560, 240)
    tinted = expr(mat, unreal.MaterialExpressionMultiply, -260, -60)
    link(mat, sample, "RGB", tinted, "A")
    link(mat, color, "", tinted, "B")
    out(mat, tinted, "RGB", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    finish(mat)
    return mat


def master_terrain():
    mat = new_material("M_Terreno", unreal.MaterialDomain.MD_SURFACE)
    grass = tex_param(mat, "Pasto", tex(ART + "/Textures/Tileable/T_Pasto_BC"), -820, -260)
    dirt = tex_param(mat, "Tierra", tex(ART + "/Textures/Tileable/T_Tierra_BC"), -820, 60)
    rock = tex_param(mat, "Roca", tex(ART + "/Textures/Tileable/T_Roca_BC"), -820, 380)
    nrm = tex_param(mat, "Normal", tex(ART + "/Textures/Tileable/T_Pasto_N"), -820, 700)

    world = expr(mat, unreal.MaterialExpressionWorldPosition, -1150, -260)
    z = expr(mat, unreal.MaterialExpressionComponentMask, -980, -260)
    z.set_editor_property("r", False)
    z.set_editor_property("g", False)
    z.set_editor_property("b", True)
    z.set_editor_property("a", False)
    link(mat, world, "", z, "")

    low = expr(mat, unreal.MaterialExpressionDivide, -820, -120)
    low.set_editor_property("const_b", 500.0)
    link(mat, z, "", low, "A")
    low_sat = expr(mat, unreal.MaterialExpressionSaturate, -650, -120)
    link(mat, low, "", low_sat, "")

    blend_a = expr(mat, unreal.MaterialExpressionLinearInterpolate, -470, -60)
    link(mat, grass, "RGB", blend_a, "A")
    link(mat, dirt, "RGB", blend_a, "B")
    link(mat, low_sat, "", blend_a, "Alpha")

    high = expr(mat, unreal.MaterialExpressionSubtract, -820, 200)
    high.set_editor_property("const_b", 620.0)
    link(mat, z, "", high, "A")
    high_div = expr(mat, unreal.MaterialExpressionDivide, -650, 200)
    high_div.set_editor_property("const_b", 420.0)
    link(mat, high, "", high_div, "A")
    high_sat = expr(mat, unreal.MaterialExpressionSaturate, -470, 200)
    link(mat, high_div, "", high_sat, "")

    blend_b = expr(mat, unreal.MaterialExpressionLinearInterpolate, -230, -60)
    link(mat, blend_a, "", blend_b, "A")
    link(mat, rock, "RGB", blend_b, "B")
    link(mat, high_sat, "", blend_b, "Alpha")
    out(mat, blend_b, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    out(mat, nrm, "RGB", unreal.MaterialProperty.MP_NORMAL)
    rough = scalar_param(mat, "Roughness", 0.92, -230, 240)
    out(mat, rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    finish(mat)
    return mat


def master_proxy():
    mat = new_material("M_Proxy", unreal.MaterialDomain.MD_SURFACE)
    color = vector_param(mat, "Color", unreal.LinearColor(0.10, 0.15, 0.13, 1.0), -420, -60)
    out(mat, color, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = scalar_param(mat, "Roughness", 0.95, -420, 200)
    out(mat, rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    finish(mat)
    return mat


# ------------------------------------------------------------------ instances

def instance(name, folder, parent):
    path = MAT + "/Instances/" + folder + "/" + name
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        unreal.EditorAssetLibrary.delete_asset(path)
    mi = AT.create_asset(name, MAT + "/Instances/" + folder, unreal.MaterialInstanceConstant,
                         unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, parent)
    return mi


def set_tex(mi, name, texture):
    if texture is None:
        return
    MEL.set_material_instance_texture_parameter_value(mi, name, texture)


def set_vec(mi, name, color):
    MEL.set_material_instance_vector_parameter_value(mi, name, color)


def set_scalar(mi, name, value):
    MEL.set_material_instance_scalar_parameter_value(mi, name, value)


def save(mi):
    unreal.EditorAssetLibrary.save_asset(mi.get_path_name(), only_if_is_dirty=False)
    return mi


def build_instances(masters):
    surface = masters["surface"]
    for stem, label in [("T_Concreto", "Concreto"), ("T_Metal", "Metal"),
                        ("T_Pasto", "Pasto"), ("T_Roca", "Roca"),
                        ("T_Saco", "Saco"), ("T_Tierra", "Tierra")]:
        mi = instance("MI_" + label, "Tileable", surface)
        set_tex(mi, "BaseColor", tex(ART + "/Textures/Tileable/" + stem + "_BC"))
        set_tex(mi, "Normal", tex(ART + "/Textures/Tileable/" + stem + "_N"))
        set_tex(mi, "ORM", tex(ART + "/Textures/Tileable/" + stem + "_ORM"))
        set_scalar(mi, "UVTile", 1.0)
        save(mi)
        log("MI " + mi.get_name() + " <- " + surface.get_name())

    team = masters["team"]
    for name, color, strength in [
        ("MI_Base_Aliada", unreal.LinearColor(0.05, 0.48, 0.60, 1.0), 0.35),
        ("MI_Base_Rival", unreal.LinearColor(0.67, 0.13, 0.055, 1.0), 0.35),
        ("MI_Nucleo_Aliado", unreal.LinearColor(0.27, 0.88, 0.91, 1.0), 2.5),
        ("MI_Nucleo_Rival", unreal.LinearColor(0.99, 0.35, 0.23, 1.0), 2.5),
        ("MI_Terminal_Aliado", unreal.LinearColor(0.96, 0.68, 0.30, 1.0), 1.6),
        ("MI_Terminal_Rival", unreal.LinearColor(0.96, 0.68, 0.30, 1.0), 1.6),
    ]:
        mi = instance(name, "Teams", team)
        set_vec(mi, "Color", color)
        set_scalar(mi, "EmissiveStrength", strength)
        save(mi)
        log("MI " + mi.get_name() + " <- " + team.get_name())

    soldier = masters["soldier"]
    for name, atlas in [("MI_Soldado_Alpha", "T_Soldado_Alpha_BC"),
                        ("MI_Soldado_Bravo", "T_Soldado_Bravo_BC"),
                        ("MI_Soldado_Medico", "T_Soldado_Medico_BC"),
                        ("MI_Soldado_Enemigo", "T_Soldado_Enemigo_BC")]:
        mi = instance(name, "Teams", soldier)
        set_tex(mi, "BaseColor", tex(ART + "/Textures/Soldado/" + atlas))
        save(mi)
        log("MI " + mi.get_name() + " <- " + soldier.get_name())

    arms = masters["arms"]
    mi = instance("MI_Armas", "Teams", arms)
    set_tex(mi, "BaseColor", tex(ART + "/Textures/Armas/T_Armas_BC"))
    save(mi)
    log("MI " + mi.get_name() + " <- " + arms.get_name())

    icon = masters["icon"]
    icon_sources = {
        "Aclarar": "T_Icon_Aclarar", "Alerta": "T_Icon_Alerta", "Atacar": "T_Icon_Atacar",
        "Cancelar": "T_Icon_Cancelar", "CesarFuego": "T_Icon_CesarFuego",
        "Check": "T_Icon_Check", "Cruz": "T_Icon_Cruz", "Curar": "T_Icon_Curar",
        "Defender": "T_Icon_Defender", "Formar": "T_Icon_Formar",
        "Mic": "T_Icon_Mic", "MicOff": "T_Icon_MicOff", "Mover": "T_Icon_Mover",
        "Puntos": "T_Icon_Puntos", "Reportar": "T_Icon_Reportar",
        "Seguir": "T_Icon_Seguir", "Vigilar": "T_Icon_Vigilar",
    }
    for label, source in sorted(icon_sources.items()):
        mi = instance("MI_Icono_" + label, "HUD", icon)
        set_tex(mi, "Icono", tex(ART + "/Textures/UI/Icons/" + source))
        save(mi)
    log("MI icons " + str(len(icon_sources)))

    for name, source in [("MI_Marcador_Aliado", "T_Marker_Aliado_Circulo"),
                         ("MI_Marcador_Enemigo", "T_Marker_Enemigo_Rombo"),
                         ("MI_Marcador_Objetivo", "T_Marker_Objetivo"),
                         ("MI_Marcador_Ping", "T_Marker_Ping"),
                         ("MI_Marcador_Flecha", "T_Marker_Flecha")]:
        mi = instance(name, "HUD", icon)
        set_tex(mi, "Icono", tex(ART + "/Textures/UI/Markers/" + source))
        save(mi)
    log("MI markers 5")

    for name, source in [("MI_Mic_Anillo", "T_UI_Mic_Anillo"),
                         ("MI_Mic_Disco", "T_UI_Mic_Disco"),
                         ("MI_Mic_Resplandor", "T_UI_Mic_Resplandor"),
                         ("MI_Mic_BarraOnda", "T_UI_Mic_BarraOnda")]:
        mi = instance(name, "HUD", icon)
        set_tex(mi, "Icono", tex(ART + "/Textures/UI/Mic/" + source))
        save(mi)
    log("MI mic 4")

    for name, source in [("MI_UI_Panel", "T_UI_Panel_9S"),
                         ("MI_UI_PanelLigero", "T_UI_Panel_Ligero_9S"),
                         ("MI_UI_BarraMarco", "T_UI_Barra_Marco"),
                         ("MI_UI_BarraRelleno", "T_UI_Barra_Relleno"),
                         ("MI_UI_Insignia", "T_UI_Insignia_Circulo"),
                         ("MI_UI_Divisor", "T_UI_Divisor"),
                         ("MI_UI_Subtitulos", "T_UI_Subtitulos_Banda")]:
        mi = instance(name, "HUD", icon)
        set_tex(mi, "Icono", tex(ART + "/Textures/UI/Kit/" + source))
        save(mi)
    log("MI kit 7")

    decal_sel = masters["decal_sel"]
    mi = instance("MI_Decal_Seleccion", "HUD", decal_sel)
    set_tex(mi, "Textura", tex(ART + "/Textures/UI/Markers/T_Decal_Seleccion"))
    save(mi)
    decal_dst = masters["decal_dst"]
    mi = instance("MI_Decal_Destino", "HUD", decal_dst)
    set_tex(mi, "Textura", tex(ART + "/Textures/UI/Markers/T_Decal_AnilloDestino"))
    save(mi)
    log("MI decals 2")

    sprite = masters["sprite"]
    for name, source, color in [
        ("MI_VFX_Chispas", "T_VFX_Chispas", unreal.LinearColor(1.0, 0.62, 0.24, 1.0)),
        ("MI_VFX_Circulo", "T_VFX_CirculoSuave", unreal.LinearColor(0.40, 0.91, 0.48, 1.0)),
    ]:
        mi = instance(name, "VFX", sprite)
        set_tex(mi, "Textura", tex(ART + "/Textures/VFX/" + source))
        set_vec(mi, "Color", color)
        save(mi)

    for name, master_key, color in [
        ("MI_VFX_Fogonazo", "fogonazo", unreal.LinearColor(1.0, 0.72, 0.30, 1.0)),
        ("MI_VFX_Humo", "humo", unreal.LinearColor(0.55, 0.55, 0.55, 1.0)),
        ("MI_VFX_Polvo", "polvo", unreal.LinearColor(0.72, 0.62, 0.46, 1.0)),
    ]:
        mi = instance(name, "VFX", masters[master_key])
        set_vec(mi, "Color", color)
        save(mi)
    log("MI vfx 5")

    terrain = masters["terrain"]
    mi = instance("MI_Terreno_ValleAlfa", "Terrain", terrain)
    set_tex(mi, "Pasto", tex(ART + "/Textures/Tileable/T_Pasto_BC"))
    set_tex(mi, "Tierra", tex(ART + "/Textures/Tileable/T_Tierra_BC"))
    set_tex(mi, "Roca", tex(ART + "/Textures/Tileable/T_Roca_BC"))
    save(mi)
    log("MI terrain 1")

    # ---- proxy (before) palette ---------------------------------------
    proxy = masters["proxy"]
    for name, color in [
        ("MI_Proxy_Cesped", unreal.LinearColor(0.10, 0.15, 0.13, 1.0)),
        ("MI_Proxy_Camino", unreal.LinearColor(0.25, 0.26, 0.25, 1.0)),
        ("MI_Proxy_Muro", unreal.LinearColor(0.34, 0.40, 0.41, 1.0)),
        ("MI_Proxy_Aliado", unreal.LinearColor(0.05, 0.48, 0.60, 1.0)),
        ("MI_Proxy_Rival", unreal.LinearColor(0.67, 0.13, 0.055, 1.0)),
        ("MI_Proxy_Oro", unreal.LinearColor(0.76, 0.47, 0.10, 1.0)),
    ]:
        mi = instance(name, "Teams", proxy)
        set_vec(mi, "Color", color)
        save(mi)
    log("MI proxy 6")

    # ---- arena-specific surface instances ------------------------------
    surface = masters["surface"]
    mi = instance("MI_Suelo_Arena", "Tileable", surface)
    set_tex(mi, "BaseColor", tex(ART + "/Textures/Tileable/T_Tierra_BC"))
    set_tex(mi, "Normal", tex(ART + "/Textures/Tileable/T_Tierra_N"))
    set_tex(mi, "ORM", tex(ART + "/Textures/Tileable/T_Tierra_ORM"))
    set_scalar(mi, "UVTile", 42.0)
    save(mi)
    mi = instance("MI_Camino_Arena", "Tileable", surface)
    set_tex(mi, "BaseColor", tex(ART + "/Textures/Tileable/T_Tierra_BC"))
    set_tex(mi, "Normal", tex(ART + "/Textures/Tileable/T_Tierra_N"))
    set_tex(mi, "ORM", tex(ART + "/Textures/Tileable/T_Tierra_ORM"))
    set_scalar(mi, "UVTile", 40.0)
    set_vec(mi, "Tint", unreal.LinearColor(0.72, 0.70, 0.66, 1.0))
    save(mi)
    mi = instance("MI_Plinto", "Tileable", surface)
    set_tex(mi, "BaseColor", tex(ART + "/Textures/Tileable/T_Concreto_BC"))
    set_tex(mi, "Normal", tex(ART + "/Textures/Tileable/T_Concreto_N"))
    set_tex(mi, "ORM", tex(ART + "/Textures/Tileable/T_Concreto_ORM"))
    set_scalar(mi, "UVTile", 8.0)
    save(mi)
    log("MI arena surfaces 3")

    # ---- world-space HUD cards (art review boards) ---------------------
    cartel = masters["cartel"]
    cards = [
        ("MI_Cartel_Minimapa", "Textures/Terrain/T_Minimapa_ValleAlfa"),
        ("MI_Cartel_HUD", "Textures/UI/Mockups/T_UI_HUD_Referencia_1210x720"),
        ("MI_Cartel_Zonas", "Textures/Terrain/T_Referencia_Zonas_ValleAlfa"),
        ("MI_Cartel_Panel", "Textures/UI/Kit/T_UI_Panel_9S"),
        ("MI_Cartel_PanelLigero", "Textures/UI/Kit/T_UI_Panel_Ligero_9S"),
        ("MI_Cartel_BarraMarco", "Textures/UI/Kit/T_UI_Barra_Marco"),
        ("MI_Cartel_BarraRelleno", "Textures/UI/Kit/T_UI_Barra_Relleno"),
        ("MI_Cartel_Insignia", "Textures/UI/Kit/T_UI_Insignia_Circulo"),
        ("MI_Cartel_MicAnillo", "Textures/UI/Mic/T_UI_Mic_Anillo"),
        ("MI_Cartel_MicDisco", "Textures/UI/Mic/T_UI_Mic_Disco"),
        ("MI_Cartel_MicResplandor", "Textures/UI/Mic/T_UI_Mic_Resplandor"),
        ("MI_Cartel_MarcadorAliado", "Textures/UI/Markers/T_Marker_Aliado_Circulo"),
        ("MI_Cartel_MarcadorEnemigo", "Textures/UI/Markers/T_Marker_Enemigo_Rombo"),
        ("MI_Cartel_MarcadorObjetivo", "Textures/UI/Markers/T_Marker_Objetivo"),
        ("MI_Cartel_MarcadorPing", "Textures/UI/Markers/T_Marker_Ping"),
        ("MI_Cartel_DecalSeleccion", "Textures/UI/Markers/T_Decal_Seleccion"),
        ("MI_Cartel_DecalDestino", "Textures/UI/Markers/T_Decal_AnilloDestino"),
        ("MI_Cartel_Icono_Atacar", "Textures/UI/Icons/T_Icon_Atacar"),
        ("MI_Cartel_Icono_Defender", "Textures/UI/Icons/T_Icon_Defender"),
        ("MI_Cartel_Icono_Mover", "Textures/UI/Icons/T_Icon_Mover"),
        ("MI_Cartel_Icono_Curar", "Textures/UI/Icons/T_Icon_Curar"),
        ("MI_Cartel_Icono_Seguir", "Textures/UI/Icons/T_Icon_Seguir"),
        ("MI_Cartel_Icono_Vigilar", "Textures/UI/Icons/T_Icon_Vigilar"),
        ("MI_Cartel_Icono_Formar", "Textures/UI/Icons/T_Icon_Formar"),
        ("MI_Cartel_Icono_Cancelar", "Textures/UI/Icons/T_Icon_Cancelar"),
        ("MI_Cartel_Icono_Check", "Textures/UI/Icons/T_Icon_Check"),
        ("MI_Cartel_Icono_Cruz", "Textures/UI/Icons/T_Icon_Cruz"),
        ("MI_Cartel_Icono_Alerta", "Textures/UI/Icons/T_Icon_Alerta"),
        ("MI_Cartel_Icono_Mic", "Textures/UI/Icons/T_Icon_Mic"),
        ("MI_Cartel_Icono_MicOff", "Textures/UI/Icons/T_Icon_MicOff"),
    ]
    for name, rel in cards:
        mi = instance(name, "HUD", cartel)
        set_tex(mi, "Textura", tex(ART + "/" + rel))
        save(mi)
    log("MI carteles " + str(len(cards)))


try:
    masters = {
        "surface": master_surface(),
        "soldier": master_simple("M_Soldado", 0.62, 0.0, unreal.LinearColor(1.0, 1.0, 1.0, 1.0)),
        "arms": master_simple("M_Armas", 0.34, 0.45, unreal.LinearColor(1.0, 1.0, 1.0, 1.0)),
        "team": master_team(),
        "icon": master_ui_icon(),
        "decal_sel": master_decal("M_Decal_Seleccion"),
        "decal_dst": master_decal("M_Decal_Destino"),
        "sprite": master_vfx("M_VFX_Sprite", False, ART + "/Textures/VFX/T_VFX_CirculoSuave"),
        "cartel": master_cartel(),
        "fogonazo": master_vfx("M_VFX_Fogonazo", True, ART + "/Textures/VFX/T_VFX_Fogonazo_Flipbook4x4"),
        "humo": master_vfx("M_VFX_Humo", True, ART + "/Textures/VFX/T_VFX_Humo_Flipbook4x4"),
        "polvo": master_vfx("M_VFX_Polvo", True, ART + "/Textures/VFX/T_VFX_Polvo_Flipbook4x4"),
        "terrain": master_terrain(),
        "proxy": master_proxy(),
    }
    log("MASTERS " + ", ".join(sorted(masters)))
    build_instances(masters)
    log("DONE")
except Exception:
    log("EXC\n" + traceback.format_exc())
finally:
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(LINES))
