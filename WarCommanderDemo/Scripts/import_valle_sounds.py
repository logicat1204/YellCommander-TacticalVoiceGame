"""Import the converted effects as acoustic assets in Unreal."""
from pathlib import Path
import unreal

source = Path(__file__).resolve().parents[2] / ".yell-cache" / "valle-sounds"
tasks = []
for name in ("Disparo", "Caida", "RadioEnvio", "Paso1", "Paso2", "Paso3"):
    task = unreal.AssetImportTask()
    task.filename = str(source / f"{name}.wav")
    task.destination_path = "/Game/Yell/Gameplay/Sounds"
    task.automated = True
    task.save = True
    task.replace_existing = True
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for task in tasks:
    if not task.imported_object_paths:
        raise RuntimeError(f"Audio no importado: {task.filename}")
    unreal.log(f"VALLE sound {task.imported_object_paths[0]}")
