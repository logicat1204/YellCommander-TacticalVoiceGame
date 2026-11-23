"""Run with UnrealEditor-Cmd and the editor Python plugin enabled."""

import unreal


MAP = "/Game/Yell/ValleAlfa"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
opened = levels.load_level(MAP) if unreal.EditorAssetLibrary.does_asset_exist(MAP) else levels.new_level(MAP)
if not opened:
    raise RuntimeError(f"Could not open or create {MAP}")
battle_mode = unreal.load_class(None, "/Script/WarCommanderDemo.YellBattle")
if not battle_mode:
    raise RuntimeError("Compile the WarCommanderDemoEditor target before creating the map")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", battle_mode)
if not levels.save_current_level():
    raise RuntimeError(f"Could not save {MAP}")
unreal.log(f"Yell map ready: {MAP}")
