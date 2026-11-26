"""Adapt the terminal screens to Valle Alfa's controls and cooldown."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
PACK = ROOT / "Assets" / "OperacionVoz_Props_P1" / "OperacionVoz_Props_P1"


def prepare(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    font_path = ROOT / "Assets" / "UI" / "Fonts" / "DejaVuSansMono-Bold.ttf"
    heading = ImageFont.truetype(str(font_path), 40)
    label = ImageFont.truetype(str(font_path), 29)
    small = ImageFont.truetype(str(font_path), 23)
    variants = (
        ("Activa", (133, 246, 179), "DISPONIBLE", ("[ E ]  REFUERZOS", "[ F ]  MÉDICOS"), "RADIO DE CAMPAÑA"),
        ("Alerta", (255, 191, 95), "EN ESPERA", ("TERMINAL OCUPADA", "ESPERA LA RECARGA"), "RADIO DE CAMPAÑA"),
    )
    for name, accent, status, lines, footer in variants:
        image = Image.open(PACK / "Textures" / f"T_Terminal_Pantalla_{name}.png").convert("RGB")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 1023, 77), fill=(14, 29, 24))
        draw.text((30, 39), "REFUERZOS", fill=accent, font=heading, anchor="lm")
        draw.text((992, 39), status, fill=accent, font=label, anchor="rm")
        draw.rectangle((475, 79, 1023, 639), fill=(9, 21, 17))
        for index, line in enumerate(lines):
            top = 181 + index * 95
            draw.rectangle((504, top, 993, top + 68), outline=accent, width=2)
            draw.text((528, top + 34), line, fill=accent, font=label, anchor="lm")
        draw.rectangle((0, 570, 1023, 639), fill=(14, 29, 24))
        draw.text((30, 606), footer, fill=accent, font=small, anchor="lm")
        image.save(destination / f"T_Terminal_Pantalla_{name}.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    prepare(parser.parse_args().destination)
