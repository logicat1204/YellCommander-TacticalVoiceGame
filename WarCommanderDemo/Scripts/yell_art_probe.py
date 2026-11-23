import unreal, traceback, os
out = os.path.join(unreal.Paths.project_dir(), "Saved", "yell_probe_out.txt")
with open(out, "w", encoding="utf-8") as f:
    try:
        f.write("START\n")
        f.write("ENGINE " + unreal.SystemLibrary.get_engine_version() + "\n")
        f.write("ASSETS " + str(unreal.EditorAssetLibrary.list_assets("/Game/Yell", recursive=True)) + "\n")
        for name in ["MaterialFactoryNew", "MaterialInstanceConstantFactoryNew", "StaticMeshFactory", "TextureFactory",
                     "WorldFactory", "BlueprintFactory", "NiagaraSystemFactoryNew", "WidgetBlueprintFactory",
                     "SkeletalMeshFactory", "AnimSequenceFactory", "LevelSequenceFactoryNew"]:
            f.write("CLASS " + name + " " + str(hasattr(unreal, name)) + "\n")
        for name in ["EditorAssetLibrary", "LevelEditorSubsystem", "EditorLevelLibrary", "AutomationLibrary",
                     "StaticMeshEditorSubsystem", "MaterialEditingLibrary", "NiagaraEditorAssetLibrary",
                     "WidgetBlueprint", "SubobjectDataSubsystem", "KismetEditorUtilities", "EditorUtilityLibrary"]:
            f.write("API " + name + " " + str(hasattr(unreal, name)) + "\n")
        if hasattr(unreal, "AutomationLibrary"):
            f.write("AUTOMATION " + str([x for x in dir(unreal.AutomationLibrary) if not x.startswith("_")]) + "\n")
        if hasattr(unreal, "LevelEditorSubsystem"):
            f.write("LEVELEDITOR " + str([x for x in dir(unreal.LevelEditorSubsystem) if not x.startswith("_")]) + "\n")
        if hasattr(unreal, "StaticMeshEditorSubsystem"):
            f.write("SMEDITOR " + str([x for x in dir(unreal.StaticMeshEditorSubsystem) if not x.startswith("_")]) + "\n")
        f.write("END\n")
    except Exception:
        f.write("EXC\n" + traceback.format_exc())
