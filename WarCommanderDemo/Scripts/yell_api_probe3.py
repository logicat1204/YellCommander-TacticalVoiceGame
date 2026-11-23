import unreal, traceback, os

OUT = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_api_probe3.txt")
lines = []
def w(s):
    lines.append(str(s))

try:
    at = unreal.AssetToolsHelpers.get_asset_tools()
    base = "/Game/Yell/Art/_Probe"
    unreal.EditorAssetLibrary.make_directory(base)
    # widget CDO route
    wbp = at.create_asset("WBP_Probe2", base, unreal.WidgetBlueprint, unreal.WidgetBlueprintFactory())
    w("WBP CREATE " + str(wbp))
    unreal.EditorAssetLibrary.save_asset(wbp.get_path_name())
    try:
        w("COMPILE " + str(unreal.BlueprintEditorLibrary.compile_blueprint(wbp)))
    except Exception as e:
        w("COMPILE EXC " + repr(e))
    cls = wbp.generated_class()
    w("GENCLASS " + str(cls))
    cdo = unreal.get_default_object(cls) if cls else None
    w("CDO " + str(cdo))
    if cdo:
        w("CDO DIR " + str([x for x in dir(cdo) if not x.startswith("_")]))
        for prop in ["widget_tree", "WidgetTree"]:
            try:
                w("CDO GET " + prop + " " + str(cdo.get_editor_property(prop)))
            except Exception as e:
                w("CDO GET EXC " + prop + " " + repr(e))
        try:
            tree = unreal.new_object(unreal.WidgetTree, cdo)
            w("NEW TREE " + str(tree))
            w("TREE DIR " + str([x for x in dir(tree) if not x.startswith("_")]))
            canvas = unreal.new_object(unreal.CanvasPanel, tree)
            tree.set_editor_property("root_widget", canvas)
            txt = unreal.new_object(unreal.TextBlock, tree)
            txt.set_editor_property("text", unreal.Text("ALFA-1"))
            canvas.add_child(txt)
            cdo.set_editor_property("widget_tree", tree)
            w("CDO SET TREE OK")
        except Exception as e:
            w("CDO TREE EXC " + repr(e))
        try:
            unreal.EditorAssetLibrary.save_asset(wbp.get_path_name())
            w("WBP SAVED")
        except Exception as e:
            w("WBP SAVE EXC " + repr(e))
    # niagara
    try:
        ns = at.create_asset("NS_Test", base, unreal.NiagaraSystem, unreal.NiagaraSystemFactoryNew())
        w("NS CREATE " + str(ns))
        if ns:
            w("NS DIR " + str([x for x in dir(ns) if not x.startswith("_")]))
            for prop in ["emitter_handles", "exposed_parameters", "editor_data"]:
                try:
                    w("NS GET " + prop + " " + str(ns.get_editor_property(prop)))
                except Exception as e:
                    w("NS GET EXC " + prop + " " + repr(e))
            w("NS SAVE " + str(unreal.EditorAssetLibrary.save_asset(ns.get_path_name())))
    except Exception as e:
        w("NS EXC " + repr(e))
    # engine niagara assets
    for root in ["/Niagara", "/Engine/Niagara", "/Niagara/DefaultAssets"]:
        try:
            assets = unreal.EditorAssetLibrary.list_assets(root, recursive=True)
            w("LIST " + root + " n=" + str(len(assets)))
            for a in assets[:20]:
                w("  " + a)
        except Exception as e:
            w("LIST EXC " + root + " " + repr(e))
    # texture factory props
    tf = unreal.TextureFactory()
    w("TEXTURE FACTORY PROPS " + str([x for x in dir(tf) if not x.startswith("_")]))
    # import test
    task = unreal.AssetImportTask()
    task.filename = unreal.Paths.project_dir() + "/Assets/Textures/Tileable/T_Concreto_BC.png"
    task.destination_path = base
    task.automated = True
    task.save = True
    task.replace_existing = True
    task.factory = unreal.TextureFactory()
    at.import_asset_tasks([task])
    w("IMPORT RESULT " + str(task.imported_object_paths))
    tex = unreal.EditorAssetLibrary.load_asset(base + "/T_Concreto_BC")
    w("TEX " + str(tex))
    if tex:
        w("TEX DIR " + str([x for x in dir(tex) if not x.startswith("_")]))
except Exception:
    w("EXC\n" + traceback.format_exc())
finally:
    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
