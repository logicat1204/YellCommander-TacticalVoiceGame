import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_api_probe.txt")
lines = []
def w(s):
    lines.append(str(s))

try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    base = "/Game/Yell/Art/_Probe"
    unreal.EditorAssetLibrary.make_directory(base)
    # Material
    mat = at.create_asset("M_Probe", base, unreal.Material, unreal.MaterialFactoryNew())
    w("MAT " + str(mat))
    for cls in ["MaterialExpressionTextureSampleParameter2D", "MaterialExpressionVectorParameter",
                "MaterialExpressionScalarParameter", "MaterialExpressionMultiply",
                "MaterialExpressionLinearInterpolate", "MaterialExpressionConstant3Vector",
                "MaterialExpressionVertexNormalWS", "MaterialExpressionWorldPosition",
                "MaterialExpressionComponentMask", "MaterialExpressionDivide"]:
        w("CLS " + cls + " " + str(hasattr(unreal, cls)))
    bc = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, -200)
    bc.set_editor_property("parameter_name", "BC")
    w("BC " + str(bc))
    tint = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -600, 100)
    tint.set_editor_property("parameter_name", "Tint")
    tint.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = unreal.MaterialEditingLibrary.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, -100)
    w("CONNECT1 " + str(unreal.MaterialEditingLibrary.connect_material_expressions(bc, "RGB", mul, "A")))
    w("CONNECT2 " + str(unreal.MaterialEditingLibrary.connect_material_expressions(tint, "", mul, "B")))
    w("PROP " + str(unreal.MaterialEditingLibrary.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)))
    w("RECOMPILE " + str(unreal.MaterialEditingLibrary.recompile_material(mat)))
    w("SAVE " + str(unreal.EditorAssetLibrary.save_asset(mat.get_path_name())))
    mi = at.create_asset("MI_Probe", base, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    w("MI " + str(mi))
    w("MI_SETPARENT " + str(unreal.MaterialEditingLibrary.set_material_instance_parent(mi, mat)))
    w("MI_SETVEC " + str(unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(0.2, 0.6, 0.9, 1))))
    w("MI_SAVE " + str(unreal.EditorAssetLibrary.save_asset(mi.get_path_name())))
    # Widget
    wbp = at.create_asset("WBP_Probe", base, unreal.WidgetBlueprint, unreal.WidgetBlueprintFactory())
    w("WBP " + str(wbp))
    w("WBP_DIR " + str([x for x in dir(wbp) if not x.startswith("_")]))
    tree = wbp.get_editor_property("WidgetTree")
    w("TREE " + str(tree))
    if tree:
        w("TREE_DIR " + str([x for x in dir(tree) if not x.startswith("_")]))
        canvas = unreal.new_object(unreal.CanvasPanel, tree)
        w("CANVAS " + str(canvas))
        try:
            tree.set_editor_property("root_widget", canvas)
            w("ROOT SET")
        except Exception as e:
            w("ROOT EXC " + repr(e))
        try:
            text = unreal.new_object(unreal.TextBlock, tree)
            text.set_editor_property("text", unreal.Text("ALFA-1 · PELOTÓN ALFA · EN MOVIMIENTO"))
            canvas.add_child(text)
            w("TEXT ADDED " + str(text))
        except Exception as e:
            w("TEXT EXC " + repr(e))
    # Niagara
    ns = at.create_asset("NS_Probe", base, unreal.NiagaraSystem, unreal.NiagaraSystemFactoryNew())
    w("NS " + str(ns))
    if ns:
        w("NS_DIR " + str([x for x in dir(ns) if not x.startswith("_")]))
    # Blueprint actor
    bp = at.create_asset("BP_Probe", base, unreal.Blueprint, unreal.BlueprintFactory())
    w("BP " + str(bp))
    w("BP_DIR " + str([x for x in dir(bp) if not x.startswith("_")]))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
