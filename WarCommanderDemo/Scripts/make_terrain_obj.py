"""Generate a low-poly visual terrain OBJ from the Valle Alfa heightmap.

The gameplay arena is a flat C++-generated field.  This mesh is only a visual
reference for the presentation copy: the arena footprint is flattened just
below the gameplay floor so the imported tiles do not intersect it.
"""
from __future__ import annotations

import json
import math
import os

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "Assets", "Terrain", "Heightmap_ValleAlfa_1009.png")
OUT_DIR = os.path.join(ROOT, "Assets", "Models", "Generated")
OBJ = os.path.join(OUT_DIR, "SM_Terreno_ValleAlfa.obj")
META = os.path.join(OUT_DIR, "SM_Terreno_ValleAlfa.json")
POINTS = os.path.join(OUT_DIR, "terrain_points.json")

GRID = 96                 # quads per side (97 x 97 vertices)
SIZE = 25200.0            # 252 m in Unreal centimetres
MIN_Z = -600.0            # -6 m
MAX_Z = 1700.0            # +17 m
ARENA_X = 4300.0          # half footprint of the flat arena (8500 uu)
ARENA_Y = 2550.0          # half footprint of the flat arena (4950 uu)
ARENA_Z = -12.0           # just below the arena floor top (z = 0)

SHOWCASE_POINTS = {
    "base_camera": (-3000.0, 0.0),
    "center_camera": (0.0, 0.0),
    "flank_camera": (0.0, -1440.0),
    "trench_a": (-4750.0, -1440.0),
    "trench_b": (-4750.0, -1000.0),
    "trench_c": (-4750.0, -1880.0),
    "north_gate_center": (4800.0, 0.0),
    "north_rock_left": (5050.0, -1150.0),
    "north_rock_right": (5050.0, 1150.0),
    "north_rock_wall": (5350.0, 0.0),
    "bunker_intact": (5350.0, -1800.0),
    "bunker_damaged": (5350.0, 0.0),
    "bunker_destroyed": (5350.0, 1800.0),
    "soldier_showcase": (-5350.0, 1800.0),
    "hud_showcase": (-5350.0, -1800.0),
    "sandbag_line_a": (-3500.0, -1700.0),
    "sandbag_line_b": (-3500.0, -1180.0),
}



def main() -> None:
    image = Image.open(SRC)
    width, height = image.size
    lo, hi = image.getextrema()
    span = float(hi - lo) or 1.0
    os.makedirs(OUT_DIR, exist_ok=True)

    def sample(x: float, y: float) -> float:
        # Image top = north (+X); image left = west (-Y).
        row = int(round((0.5 - x / SIZE) * (height - 1)))
        col = int(round((y / SIZE + 0.5) * (width - 1)))
        row = max(0, min(height - 1, row))
        col = max(0, min(width - 1, col))
        value = image.getpixel((col, row))
        if isinstance(value, tuple):
            value = value[0]
        z = MIN_Z + (float(value) - lo) / span * (MAX_Z - MIN_Z)
        if abs(x) <= ARENA_X and abs(y) <= ARENA_Y:
            return ARENA_Z
        return z

    verts: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    for r in range(GRID + 1):
        x = (0.5 - r / GRID) * SIZE
        for c in range(GRID + 1):
            y = (c / GRID - 0.5) * SIZE
            verts.append((x, y, sample(x, y)))
            uvs.append((x / 2000.0, y / 2000.0))

    def index(r: int, c: int) -> int:
        return r * (GRID + 1) + c + 1  # OBJ is 1-based

    faces: list[tuple[int, int, int]] = []
    for r in range(GRID):
        for c in range(GRID):
            a = index(r, c)
            b = index(r, c + 1)
            d = index(r + 1, c)
            e = index(r + 1, c + 1)
            faces.append((a, b, e))
            faces.append((a, e, d))

    # Smooth vertex normals from the triangle fan.
    normals = [(0.0, 0.0, 0.0) for _ in verts]
    for a, b, c in faces:
        ax, ay, az = verts[a - 1]
        bx, by, bz = verts[b - 1]
        cx, cy, cz = verts[c - 1]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        nx, ny, nz = nx / length, ny / length, nz / length
        for i in (a - 1, b - 1, c - 1):
            ox, oy, oz = normals[i]
            normals[i] = (ox + nx, oy + ny, oz + nz)

    with open(OBJ, "w", encoding="ascii", newline="\n") as f:
        f.write("# Valle Alfa visual terrain - generated from Heightmap_ValleAlfa_1009.png\n")
        f.write("# 1 unit = 1 cm. Arena footprint flattened at z=-12.\n")
        for x, y, z in verts:
            f.write(f"v {x:.4f} {y:.4f} {z:.4f}\n")
        for u, v in uvs:
            f.write(f"vt {u:.6f} {v:.6f}\n")
        for nx, ny, nz in normals:
            length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            f.write(f"vn {nx / length:.6f} {ny / length:.6f} {nz / length:.6f}\n")
        for a, b, c in faces:
            f.write(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}\n")

    meta = {
        "source": os.path.relpath(SRC, ROOT).replace("\\", "/"),
        "obj": os.path.relpath(OBJ, ROOT).replace("\\", "/"),
        "grid_quads": GRID,
        "size_cm": SIZE,
        "height_range_cm": [MIN_Z, MAX_Z],
        "arena_flatten": {"half_x": ARENA_X, "half_y": ARENA_Y, "z": ARENA_Z},
        "vertices": len(verts),
        "triangles": len(faces),
        "heightmap_extrema": [lo, hi],
    }
    with open(META, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    points = {}
    for name, (px, py) in SHOWCASE_POINTS.items():
        points[name] = {
            "x": px,
            "y": py,
            "z": round(sample(px, py), 2),
            "inside_arena": abs(px) <= ARENA_X and abs(py) <= ARENA_Y,
        }
    with open(POINTS, "w", encoding="utf-8") as f:
        json.dump(points, f, indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
