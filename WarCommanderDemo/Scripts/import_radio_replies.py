"""Import the generated Spanish radio cues into the Unreal project."""

import os
from pathlib import Path

import unreal


source = Path(os.environ["YELL_REPLY_SOURCE"])
tasks = []
known_cues = ("RadioCopiado", "RadioAclarar", "RadioMoral", "RadioPatrulla")
selected = os.getenv("YELL_REPLY_CUES")
for cue in selected.split(",") if selected else known_cues:
    if cue not in known_cues:
        raise ValueError(f"Unknown radio cue: {cue}")
    task = unreal.AssetImportTask()
    task.filename = str(source / f"{cue}.wav")
    task.destination_path = "/Game/Yell/Audio"
    task.destination_name = cue
    task.automated = True
    task.replace_existing = True
    task.save = True
    tasks.append(task)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for task in tasks:
    if not task.imported_object_paths:
        raise RuntimeError(f"Audio import failed: {task.filename}")
    unreal.log(f"Yell radio cue ready: {task.imported_object_paths[0]}")
