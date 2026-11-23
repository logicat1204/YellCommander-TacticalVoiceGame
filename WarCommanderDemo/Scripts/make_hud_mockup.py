"""Compose a 1210x720 HUD reference image from the shipped UI assets.

The layout mirrors Source/WarCommanderDemo/Yell/YellHUD.cpp (same coordinates,
same palette) so the image can be used both as the widget target and as the
world-space board in the presentation level.  Runs with plain CPython.
"""
from __future__ import annotations

import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UI = os.path.join(ROOT, "Assets", "UI")
OUT = os.path.join(UI, "Mockups", "T_UI_HUD_Referencia_1210x720.png")

W, H = 1210, 720
INK = (7, 16, 19, 238)
PANEL = (16, 30, 34, 230)
PAPER = (219, 240, 240, 255)
MUTED = (133, 176, 181, 255)
CYAN = (69, 224, 232, 255)
GOLD = (245, 173, 77, 255)
DANGER = (252, 89, 59, 255)
MEDIC = (102, 232, 122, 255)


def load(path):
    return Image.open(path).convert("RGBA")


def font(name, size):
    return ImageFont.truetype(os.path.join(UI, "Fonts", name), size)


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(base)

    bold = font("DejaVuSans-Bold.ttf", 18)
    small = font("DejaVuSans.ttf", 12)
    tiny = font("DejaVuSans.ttf", 11)
    mono = font("DejaVuSansMono.ttf", 12)

    panel9 = load(os.path.join(UI, "Kit", "T_UI_Panel_9S.png"))

    def panel(x, y, w, h, img=panel9, border=16):
        # simple 9-slice
        iw, ih = img.size
        box = (x, y, x + w, y + h)
        src = img
        if w < iw or h < ih:
            src = img.resize((max(w, 1), max(h, 1)))
            base.alpha_composite(src, (x, y))
            return
        top = img.crop((0, 0, iw, border))
        base.alpha_composite(top.resize((w, border)), (x, y))

    def box(color, x, y, w, h):
        draw.rectangle((x, y, x + w, y + h), fill=color)

    def label(text, color, x, y, f):
        draw.text((x, y), text, font=f, fill=color)

    def bar(x, y, w, ratio, color):
        box(PANEL, x, y, w, 5)
        box(color, x, y, max(1, int(w * ratio)), 5)

    # ---- top-left commander panel (YellHUD.cpp X=22 Y=22 295x135)
    X, Y = 22, 22
    box(INK, X, Y, 295, 135)
    box(CYAN, X, Y, 295, 3)
    label("YELL COMMANDER", PAPER, X + 13, Y + 8, bold)
    label("VALLE ALFA", MUTED, X + 13, Y + 33, small)
    label("COMANDANTE   100", PAPER, X + 13, Y + 54, small)
    bar(X + 13, Y + 73, 269, 1.0, CYAN)
    label("BASE ALIADA   500", PAPER, X + 13, Y + 88, small)
    label("RIVAL   500", MUTED, X + 191, Y + 88, small)
    bar(X + 13, Y + 110, 129, 1.0, CYAN)
    bar(X + 153, Y + 110, 129, 1.0, DANGER)

    # ---- allied squads (295 wide, 29 per row)
    allies = [("ALFA-1", "Atacar", "4/4", CYAN, False),
              ("BRAVO-2", "Defender", "3/4", CYAN, False),
              ("MÉDICOS", "Seguir", "2/2", MEDIC, False),
              ("CHARLIE-3", "Mover", "4/4", CYAN, True)]
    AY = Y + 150
    box(INK, X, AY, 295, len(allies) * 29 + 53)
    label("PELOTONES ALIADOS", MUTED, X + 13, AY + 8, tiny)
    AY += 31
    for name, action, ready, tint, inspired in allies:
        box(PANEL, X + 7, AY - 2, 281, 23)
        box(GOLD if inspired else tint, X + 7, AY - 2, 3, 23)
        label(name, tint, X + 15, AY + 3, small)
        label(action, PAPER, X + 91, AY + 4, tiny)
        label(ready, MUTED, X + 245, AY + 4, tiny)
        AY += 29
    label("Refuerzos 12 s     Moral 8 s", MUTED, X + 13, AY + 1, tiny)

    # ---- tactical map (237 wide, X = W-237-22)
    MW, MX, MY = 237, W - 237 - X, Y + 31
    box(INK, MX, Y, MW, 235)
    box(GOLD, MX, Y, MW, 3)
    label("MAPA TÁCTICO", PAPER, MX + 11, Y + 8, tiny)
    for i, (name, dx) in enumerate([("IZQ", -60), ("CTR", 0), ("DER", 60)]):
        box(PANEL, MX + 117 + dx - 20, MY + 7, 40, 160)
        label(name, MUTED, MX + 117 + dx - 10, MY + 170, tiny)
    mini = load(os.path.join(ROOT, "Assets", "Terrain", "T_Minimapa_ValleAlfa.png"))
    mini = mini.resize((MW - 22, 150))
    alpha = mini.getchannel("A").point(lambda v: int(v * 0.30))
    mini.putalpha(alpha)
    base.alpha_composite(mini, (MX + 11, MY + 14))
    box(CYAN, MX + 117 - 7, MY + 88 - 70 - 5, 14, 10)
    box(DANGER, MX + 117 - 7, MY + 88 + 70 - 5, 14, 10)
    for px, py, tint in [(MX + 117 - 60, MY + 40, CYAN), (MX + 117, MY + 70, CYAN),
                         (MX + 117 + 60, MY + 120, CYAN), (MX + 117 - 20, MY + 100, MEDIC),
                         (MX + 117 + 40, MY + 30, DANGER)]:
        box(tint, px - 2, py - 2, 4, 4)
    box(PAPER, MX + 117 - 3, MY + 150 - 3, 6, 6)
    label("Rival · Agresivo", MUTED, MX + 11, MY + 187, tiny)

    # ---- crosshair
    box(PAPER, W // 2 - 5, H // 2, 10, 1)
    box(PAPER, W // 2, H // 2 - 5, 1, 10)

    # ---- radio panel (700x85 centered, bottom 108)
    RW = min(W - 48, 700)
    RX, RY = (W - RW) // 2, H - 108
    box(INK, RX, RY, RW, 85)
    box(DANGER, RX, RY, RW, 3)
    label("RADIO  /  GRABANDO  /  MODELO D", GOLD, RX + 14, RY + 7, small)
    label("«Alfa uno, atacar el flanco izquierdo»", PAPER, RX + 14, RY + 29, small)
    box(PANEL, RX + RW - 114, RY + 13, 98, 4)
    box(CYAN, RX + RW - 114, RY + 13, 98 * 0.62, 4)
    label("V  Hablar    T  Escribir    R  Canal    F2  Modelo    F3  Diagnóstico",
          MUTED, RX + 14, RY + 58, tiny)

    # ---- order icons strip (kit + icons, tinted)
    icons = [("Atacar", "T_Icon_Atacar", GOLD), ("Defender", "T_Icon_Defender", CYAN),
             ("Mover", "T_Icon_Mover", CYAN), ("Seguir", "T_Icon_Seguir", CYAN),
             ("Vigilar", "T_Icon_Vigilar", CYAN), ("Curar", "T_Icon_Curar", MEDIC),
             ("Formar", "T_Icon_Formar", CYAN), ("Cancelar", "T_Icon_Cancelar", DANGER),
             ("Reportar", "T_Icon_Reportar", GOLD), ("CesarFuego", "T_Icon_CesarFuego", GOLD)]
    IY = RY - 74
    IX = RX
    for name, file, tint in icons:
        img = load(os.path.join(UI, "Icons", file + ".png")).resize((28, 28))
        tinted = Image.new("RGBA", img.size, tint)
        tinted.putalpha(img.getchannel("A"))
        base.alpha_composite(tinted, (IX + 6, IY + 4))
        label(name, MUTED, IX + 2, IY + 36, tiny)
        IX += 66
    label("ÓRDENES (iconos del kit)", MUTED, RX, IY - 16, tiny)
    ring = load(os.path.join(UI, "Mic", "T_UI_Mic_Anillo.png")).resize((64, 64))
    disc = load(os.path.join(UI, "Mic", "T_UI_Mic_Disco.png")).resize((40, 40))
    glow = load(os.path.join(UI, "Mic", "T_UI_Mic_Resplandor.png")).resize((92, 92))
    base.alpha_composite(glow, (RX + RW - 150, RY - 92))
    base.alpha_composite(disc, (RX + RW - 124, RY - 66))
    base.alpha_composite(ring, (RX + RW - 136, RY - 78))

    # ---- nameplate + markers sample (diegetic strip)
    NX, NY = X, H - 292
    box(INK, NX, NY, 295, 62)
    box(CYAN, NX, NY, 3, 62)
    label("Sargento Rivas · ALFA-1", PAPER, NX + 12, NY + 8, small)
    label("Atacar · flanco izquierdo", CYAN, NX + 12, NY + 26, tiny)
    label("86/100", MUTED, NX + 178, NY + 8, tiny)
    bar(NX + 12, NY + 44, 200, 0.86, CYAN)
    aliado = load(os.path.join(UI, "Markers", "T_Marker_Aliado_Circulo.png")).resize((20, 20))
    enemigo = load(os.path.join(UI, "Markers", "T_Marker_Enemigo_Rombo.png")).resize((20, 20))
    ping = load(os.path.join(UI, "Markers", "T_Marker_Ping.png")).resize((20, 20))
    base.alpha_composite(aliado, (NX + 250, NY + 8))
    base.alpha_composite(enemigo, (NX + 250, NY + 24))
    base.alpha_composite(ping, (NX + 250, NY + 40))

    base.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
