import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_api_probe2.txt")
lines = []
def w(s):
    lines.append(str(s))

try:
    w("MATEDIT " + str([x for x in dir(unreal.MaterialEditingLibrary) if not x.startswith("_")]))
    mat = unreal.EditorAssetLibrary.load_asset("/Game/Yell/Art/_Probe/M_Probe")
    mi = unreal.EditorAssetLibrary.load_asset("/Game/Yell/Art/_Probe/MI_Probe")
    w("MI props " + str([x for x in dir(mi) if not x.startswith("_")]))
    for prop in ["vector_parameter_values", "scalar_parameter_values", "texture_parameter_values", "parent"]:
        try:
            w("MI GET " + prop + " " + str(mi.get_editor_property(prop)))
        except Exception as e:
            w("MI GET EXC " + prop + " " + repr(e))
    try:
        r = unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi, "Tint", unreal.LinearColor(0.2, 0.6, 0.9, 1.0))
        w("SETVEC " + str(r))
    except Exception as e:
        w("SETVEC EXC " + repr(e))
    try:
        r = unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, "RoughnessScale", 0.5)
        w("SETSCALAR " + str(r))
    except Exception as e:
        w("SETSCALAR EXC " + repr(e))
    try:
        r = unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(mi, "BC", unreal.EditorAssetLibrary.load_asset("/Game/Yell/Art/_Probe/M_Probe"))
        w("SETTEX " + str(r))
    except Exception as e:
        w("SETTEX EXC " + repr(e))
    w("MI AFTER " + str(mi.get_editor_property("vector_parameter_values")))
    # widget-related classes
    w("WIDGET CLASSES " + str([x for x in dir(unreal) if "Widget" in x and not x.startswith("_")]))
    w("BLUEPRINT LIB " + str(hasattr(unreal, "BlueprintEditorLibrary")))
    if hasattr(unreal, "BlueprintEditorLibrary"):
        w("BLUEPRINT LIB DIR " + str([x for x in dir(unreal.BlueprintEditorLibrary) if not x.startswith("_")]))
    w("SUBOBJ DIR " + str([x for x in dir(unreal.SubobjectDataSubsystem) if not x.startswith("_")]))
    # niagara
    ns = unreal.EditorAssetLibrary.load_asset("/Game/Yell/Art/_Probe/NS_Probe")
    w("NS " + str(ns))
    if ns:
        w("NS DIR " + str([x for x in dir(ns) if not x.startswith("_")]))
    w("NIAGARA CLASSES " + str([x for x in dir(unreal) if "Niagara" in x and not x.startswith("_")][:120]))
    # texture import task factory options
    w("FBXImportType " + str([x for x in dir(unreal.FBXImportType) if not x.startswith("_")]))
    w("TextureFactory props " + str([x for x in dir(unreal.TextureFactory) if not x.startswith("_")]))
    w("AssetImportTask props " + str([x for x in dir(unreal.AssetImportTask) if not x.startswith("_")]))
    w("FbxImportUI props " + str([x for x in dir(unreal.FbxImportUI) if not x.startswith("_")]))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
