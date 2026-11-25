# -*- coding: utf-8 -*-
"""Genera los assets del HUD del jugador (minimapa, comunicacion, teclas, salud). Uso: gen_hud.py <out_root>"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

OUT = sys.argv[1]
S = 4
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
DARK = (12, 14, 12, 255)
WHITE = (255, 255, 255, 255)
BLUE = (47, 123, 255, 255)
TEAL = (25, 199, 199, 255)
RED = (214, 58, 47, 255)
AMBER = (232, 166, 38, 255)
OLIVE = (74, 82, 66, 255)


def path(*p):
    q = os.path.join(OUT, *p)
    os.makedirs(os.path.dirname(q), exist_ok=True)
    return q


def cv(w, h):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def L(*p):
    return [c * S for c in p]


def fin(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def font(sz):
    return ImageFont.truetype(FB, int(sz * S))


def text_c(d, cx, cy, s, sz, fill=WHITE):
    d.text((cx * S, cy * S), s, font=font(sz), fill=fill, anchor='mm')


def circ(d, cx, cy, r, **k):
    d.ellipse(L(cx - r, cy - r, cx + r, cy + r), **k)


def with_outline(im, px, col=DARK):
    """Contorno redondeado alrededor del alfa (im a resolucion supersampleada)."""
    a = im.getchannel('A')
    dil = a.filter(ImageFilter.GaussianBlur(px * S * 0.55)).point(lambda v: 255 if v > 22 else 0)
    dil = dil.filter(ImageFilter.GaussianBlur(0.8))
    base = Image.new('RGBA', im.size, col)
    base.putalpha(dil)
    return Image.alpha_composite(base, im)


def save(im, w, h, *p):
    fin(im, w, h).save(path(*p), optimize=True)


def grad_v(w, h, c1, c2):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = (np.array(c1[:3])[None, None, :] * (1 - t) + np.array(c2[:3])[None, None, :] * t)
    arr = np.repeat(arr, w, axis=1).astype(np.uint8)
    return Image.fromarray(arr, 'RGB').convert('RGBA')


def masked(layer, mask):
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    out.paste(layer, (0, 0), mask)
    return out


# ============================================================================ MINIMAPA: iconos (128 px)
def badge_disc(d, ring, fill=(24, 30, 24, 255), r=52):
    circ(d, 64, 64, r, fill=fill)
    circ(d, 64, 64, r, outline=ring, width=8 * S)


def ic_jugador():
    im, d = cv(128, 128)
    d.polygon(L(64, 8, 108, 112, 64, 90, 20, 112), fill=BLUE)
    d.polygon(L(64, 8, 64, 90, 20, 112), fill=(30, 96, 214, 255))
    d.line(L(64, 30, 64, 78), fill=(255, 255, 255, 235), width=5 * S)
    d.polygon(L(64, 22, 72, 40, 56, 40), fill=WHITE)
    return with_outline(im, 5)


def ic_cono():
    n = 256
    y, x = np.mgrid[0:n, 0:n].astype(np.float32)
    dx, dy = x - n / 2, (n / 2) - y          # origen en el centro, apunta hacia arriba
    r = np.hypot(dx, dy)
    ang = np.degrees(np.arctan2(dx, dy))     # 0 = arriba
    half = 42
    edge = np.clip((half - np.abs(ang)) / 6.0, 0, 1)
    fall = np.clip(1 - r / (n / 2 - 2), 0, 1) ** 1.3
    a = (edge * fall * 0.85 * (r > 6) * 255).astype(np.uint8)
    arr = np.zeros((n, n, 4), np.uint8)
    arr[..., :3] = 255
    arr[..., 3] = a
    Image.fromarray(arr, 'RGBA').save(path('Minimapa', 'Iconos', 'T_MM_Cono_Vision.png'), optimize=True)


def helmet(d, col, cx=64, cy=66, s=1.0):
    d.pieslice(L(cx - 22 * s, cy - 30 * s, cx + 22 * s, cy + 14 * s), 180, 360, fill=col)
    d.rounded_rectangle(L(cx - 25 * s, cy - 8 * s, cx + 25 * s, cy - 1 * s), radius=3 * S, fill=col)
    d.pieslice(L(cx - 28 * s, cy + 8 * s, cx + 28 * s, cy + 56 * s), 180, 360, fill=col)   # hombros


def ic_soldado(nme, ring):
    im, d = cv(128, 128)
    badge_disc(d, ring)
    helmet(d, (235, 238, 230, 255), 64, 60, 0.95)
    d.rectangle(L(46, 58, 82, 62), fill=(24, 30, 24, 255))
    return with_outline(im, 4)


def ic_medico():
    im, d = cv(128, 128)
    badge_disc(d, WHITE, fill=(242, 242, 238, 255))
    d.rounded_rectangle(L(54, 30, 74, 98), radius=4 * S, fill=RED)
    d.rounded_rectangle(L(30, 54, 98, 74), radius=4 * S, fill=RED)
    return with_outline(im, 4)


def hexagon(d, cx, cy, r, **k):
    pts = [(cx + r * math.cos(math.radians(60 * i - 30)), cy + r * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    d.polygon([(x * S, y * S) for x, y in pts], **k)


def fort(d, col, ox=0, oy=0, sc=1.0):
    def P(*c):
        return L(*[(v * sc + (ox if i % 2 == 0 else oy)) for i, v in enumerate(c)])
    d.rectangle(P(36, 52, 92, 92), fill=col)
    for x in (36, 54, 72):
        d.rectangle(P(x, 42, x + 20, 54), fill=col)
    d.rectangle(P(56, 68, 72, 92), fill=(24, 30, 24, 255))
    d.line(P(64, 20, 64, 42), fill=col, width=int(4 * S * sc))
    d.polygon(P(64, 20, 84, 27, 64, 34), fill=col)


def ic_estructura(nme):
    im, d = cv(128, 128)
    ring = {'FlancoIzq': AMBER, 'FlancoDer': AMBER, 'BaseAliada': BLUE, 'BaseEnemiga': RED}[nme]
    hexagon(d, 64, 64, 58, fill=(24, 30, 24, 255))
    hexagon(d, 64, 64, 58, outline=ring, width=7 * S)
    if nme in ('BaseAliada', 'BaseEnemiga'):
        fort(d, ring if nme == 'BaseEnemiga' else (235, 240, 255, 255), 0, 4, 1.0)
    else:
        left = nme == 'FlancoIzq'
        for k, off in enumerate((0, 22)):
            xs = (44 + off, 66 + off) if left else (84 - off, 62 - off)
            tip, back = (xs[0], xs[1]) if left else (xs[0], xs[1])
            d.line(L(back, 30, tip, 52, back, 74), fill=WHITE, width=9 * S, joint='curve')
        text_c(d, 64, 94, 'IZQ' if left else 'DER', 20, WHITE)
    return with_outline(im, 4)


# ============================================================================ MINIMAPA: rutas
def ruta_tile():
    im, d = cv(64, 16)
    for x0 in (0, 32):
        d.rounded_rectangle(L(x0 + 2, 4, x0 + 24, 12), radius=4 * S, fill=WHITE)
    save(im, 64, 16, 'Minimapa', 'Rutas', 'T_MM_Ruta_Tile.png')


def ruta_flecha():
    im, d = cv(64, 64)
    d.line(L(18, 14, 46, 32, 18, 50), fill=WHITE, width=10 * S, joint='curve')
    save(with_outline(im, 2), 64, 64, 'Minimapa', 'Rutas', 'T_MM_Ruta_Flecha.png')


def ruta_nodo():
    im, d = cv(64, 64)
    circ(d, 32, 32, 22, fill=(24, 30, 24, 255))
    circ(d, 32, 32, 22, outline=WHITE, width=6 * S)
    circ(d, 32, 32, 8, fill=WHITE)
    save(with_outline(im, 2), 64, 64, 'Minimapa', 'Rutas', 'T_MM_Ruta_Nodo.png')


def ruta_destino():
    im, d = cv(128, 128)
    d.line(L(40, 112, 40, 18), fill=WHITE, width=8 * S)
    d.polygon(L(44, 18, 104, 36, 44, 58), fill=AMBER)
    circ(d, 40, 114, 9, fill=WHITE)
    save(with_outline(im, 4), 128, 128, 'Minimapa', 'Rutas', 'T_MM_Ruta_Destino.png')


def indicador_borde():
    im, d = cv(64, 64)
    d.polygon(L(32, 8, 56, 52, 32, 42, 8, 52), fill=WHITE)
    save(with_outline(im, 3), 64, 64, 'Minimapa', 'Iconos', 'T_MM_Indicador_Borde.png')


# ============================================================================ MINIMAPA: marco, brujula, mascara, fondo (512)
N = 512
C = N // 2


def marco():
    im, d = cv(N, N)
    R0, R1 = 254, 216
    circ(d, C, C, R0, fill=(22, 26, 22, 255))
    # biselado: anillos concentricos de claro a oscuro
    steps = R0 - R1
    for i in range(steps):
        t = i / steps
        v = int(92 - 40 * abs(t - 0.35) * 2)
        circ(d, C, C, R0 - i, outline=(v - 6, v + 2, v - 12, 255), width=S + 1)
    circ(d, C, C, R0, outline=(10, 12, 10, 255), width=3 * S)
    circ(d, C, C, R1, outline=(10, 12, 10, 255), width=3 * S)
    circ(d, C, C, R1 - 5, outline=(47, 123, 255, 150), width=2 * S)
    # tornillos
    for a in (45, 135, 225, 315):
        x, y = C + 235 * math.cos(math.radians(a)), C + 235 * math.sin(math.radians(a))
        circ(d, x, y, 6, fill=(40, 44, 38, 255))
        circ(d, x, y, 6, outline=(120, 128, 112, 255), width=S)
        d.line(L(x - 4, y, x + 4, y), fill=(20, 22, 18, 255), width=S)
    # marca fija de "adelante" (arriba)
    out = Image.new('RGBA', im.size, (0, 0, 0, 0))
    hole = Image.new('L', im.size, 0)
    ImageDraw.Draw(hole).ellipse(L(C - R1 + 2, C - R1 + 2, C + R1 - 2, C + R1 - 2), fill=255)
    a = ImageChops.subtract(im.getchannel('A'), hole)
    # dejar la marca azul fuera del recorte
    out = im.copy()
    out.putalpha(a)
    mark, md = cv(N, N)
    md.polygon(L(C - 12, C - R1 - 2, C + 12, C - R1 - 2, C, C - R1 + 20), fill=BLUE)
    out = Image.alpha_composite(out, with_outline(mark, 2))
    save(out, N, N, 'Minimapa', 'Marco', 'T_MM_Marco_Circular.png')


def brujula():
    im, d = cv(N, N)
    for deg in range(0, 360, 5):
        a = math.radians(deg - 90)
        big = deg % 30 == 0
        r1, r2 = (200, 213) if big else (206, 213)
        d.line(L(C + r1 * math.cos(a), C + r1 * math.sin(a), C + r2 * math.cos(a), C + r2 * math.sin(a)),
               fill=(235, 238, 230, 230 if big else 120), width=(3 if big else 2) * S)
    for deg, ch, col in ((0, 'N', (255, 96, 80, 255)), (90, 'E', WHITE), (180, 'S', WHITE), (270, 'O', WHITE)):
        a = math.radians(deg - 90)
        text_c(d, C + 178 * math.cos(a), C + 178 * math.sin(a), ch, 30, col)
    # sombra de legibilidad
    sh = im.filter(ImageFilter.GaussianBlur(3 * S))
    sh = ImageChops.multiply(sh, Image.new('RGBA', im.size, (0, 0, 0, 255)))
    out = Image.alpha_composite(sh, im)
    save(out, N, N, 'Minimapa', 'Marco', 'T_MM_Brujula_Rotante.png')


def mascara_fondo():
    R = 218
    m = Image.new('L', (N * S, N * S), 0)
    ImageDraw.Draw(m).ellipse(L(C - R, C - R, C + R, C + R), fill=255)
    fin(m, N, N).save(path('Minimapa', 'Marco', 'T_MM_Mascara_Circular.png'), optimize=True)
    # fondo: disco oscuro con rejilla tenue y viñeta
    y, x = np.mgrid[0:N, 0:N].astype(np.float32)
    r = np.hypot(x - C, y - C)
    base = np.stack([np.full((N, N), v, np.float32) for v in (16, 21, 17)], -1)
    grid = (((x % 32) < 1.2) | ((y % 32) < 1.2)).astype(np.float32)[..., None] * np.array([10, 14, 10])
    vig = (1 - 0.35 * (r / R) ** 2)[..., None]
    rgb = np.clip((base + grid) * vig, 0, 255).astype(np.uint8)
    img = Image.fromarray(rgb, 'RGB').convert('RGBA')
    img.putalpha(fin(m, N, N))
    img.save(path('Minimapa', 'Marco', 'T_MM_Fondo_Circular.png'), optimize=True)


# ============================================================================ COMUNICACION
def glyph_walkie():
    im, d = cv(256, 256)
    d.rounded_rectangle(L(139, 44, 157, 80), radius=5 * S, fill=WHITE)                 # antena
    for r in (26, 46):
        d.arc(L(148 - r, 40 - r, 148 + r, 40 + r), 215, 325, fill=WHITE, width=9 * S)  # ondas
    d.rounded_rectangle(L(76, 70, 184, 244), radius=24 * S, fill=WHITE)                # cuerpo
    d.rounded_rectangle(L(60, 108, 78, 168), radius=7 * S, fill=WHITE)                 # boton PTT
    clear = (0, 0, 0, 0)
    for y in (96, 110, 124, 138):
        d.rounded_rectangle(L(98, y, 162, y + 7), radius=3 * S, fill=clear)           # rejilla
    d.rounded_rectangle(L(98, 160, 162, 190), radius=6 * S, fill=clear)               # pantalla
    d.rectangle(L(106, 172, 130, 178), fill=WHITE)
    circ(d, 104, 218, 8, fill=clear)
    circ(d, 156, 218, 8, fill=clear)
    return im


def bez(p0, p1, p2, n=28):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [k / n for k in range(n + 1)]]


def glyph_habla():
    im, d = cv(256, 256)
    dx = -12
    P = lambda pts: [((x + dx) * S, y * S) for x, y in pts]
    A, B = (26, 128), (158, 128)
    upper = (bez(A, (48, 90), (76, 98)) + bez((76, 98), (84, 98), (92, 107))[1:] + bez((92, 107), (100, 98), (108, 98))[1:]
             + bez((108, 98), (136, 90), B)[1:] + bez(B, (92, 134), A)[1:])
    lower = bez(A, (92, 154), B) + bez(B, (92, 204), A)[1:]
    d.polygon(P(upper), fill=WHITE)
    d.polygon(P(lower), fill=WHITE)
    for r in (30, 58, 86):                                                      # ondas de voz
        d.arc(L(158 + dx - r, 128 - r, 158 + dx + r, 128 + r), -36, 36, fill=WHITE, width=11 * S)
    return im


def badge_with(glyph, ring, nm_glyph, nm_badge, active=True):
    save(glyph, 256, 256, 'Comunicacion', nm_glyph)
    im, d = cv(256, 256)
    circ(d, 128, 128, 120, fill=(20, 26, 20, 240))
    circ(d, 128, 128, 120, outline=ring, width=10 * S)
    g = glyph.resize((int(164 * S), int(164 * S)), Image.LANCZOS)
    im.alpha_composite(g, (int(46 * S), int(46 * S)))
    save(with_outline(im, 3), 256, 256, 'Comunicacion', nm_badge)


def cambio_modo():
    im, d = cv(256, 256)
    cx = cy = 128
    r = 82
    for a0, a1 in ((200, 330), (20, 150)):
        d.arc(L(cx - r, cy - r, cx + r, cy + r), a0, a1, fill=WHITE, width=18 * S)
        a = math.radians(a1)
        px, py = cx + r * math.cos(a), cy + r * math.sin(a)
        tx, ty = -math.sin(a), math.cos(a)
        nx, ny = math.cos(a), math.sin(a)
        d.polygon(L(px + tx * 30, py + ty * 30, px + nx * 28, py + ny * 28, px - nx * 28, py - ny * 28), fill=WHITE)
    save(with_outline(im, 4), 256, 256, 'Comunicacion', 'T_Comm_Icono_Cambio.png')


# ============================================================================ CONTROLES
def keycap(label, w=96, h=96, pressed=False, sz=None, accent=None):
    im, d = cv(w, h)
    lip = 8
    off = 5 if pressed else 0
    d.rounded_rectangle(L(2, 6, w - 2, h - 2), radius=16 * S, fill=(26, 30, 26, 255))                    # base/labio
    top = (92, 100, 86, 255) if not pressed else (74, 82, 70, 255)
    bot = (58, 64, 54, 255)
    face = grad_v((w - 12) * S, (h - 12 - lip) * S, top, bot)
    fm = Image.new('L', face.size, 0)
    ImageDraw.Draw(fm).rounded_rectangle([0, 0, face.size[0] - 1, face.size[1] - 1], radius=13 * S, fill=255)
    im.alpha_composite(masked(face, fm), (6 * S, (4 + off) * S))
    d.rounded_rectangle(L(6, 4 + off, w - 6, h - 8 - lip + 4 + off + 4), radius=13 * S,
                        outline=accent or (150, 160, 140, 255), width=2 * S)
    sz = sz or (46 if len(label) == 1 else 28 if len(label) <= 3 else 22)
    text_c(d, w / 2, (h - 8 - lip) / 2 + 6 + off, label, sz, WHITE)
    return with_outline(im, 2)


def pill(label, key='R'):
    w, h = 520, 96
    im, d = cv(w, h)
    d.rounded_rectangle(L(40, 14, w - 2, h - 14), radius=22 * S, fill=(18, 22, 18, 215))
    d.rounded_rectangle(L(40, 14, w - 2, h - 14), radius=22 * S, outline=(90, 100, 80, 255), width=3 * S)
    text_c(d, 300, 48, label, 32, WHITE)
    im.alpha_composite(keycap(key).resize((96 * S, 96 * S), Image.LANCZOS), (0, 0))
    save(im, w, h, 'Controles', f'T_Prompt_{key}_CambiarModo.png')


def keys():
    spec = [('R', 96), ('V', 96), ('M', 96), ('E', 96), ('F', 96), ('Tab', 120), ('Esc', 96), ('Shift', 144),
            ('Espacio', 208), ('Enter', 144)]
    for lab, w in spec:
        save(keycap(lab, w, 96), w, 96, 'Controles', f'T_Key_{lab}.png')
    save(keycap('R', 96, 96, pressed=True), 96, 96, 'Controles', 'T_Key_R_Pressed.png')
    save(keycap('R', 96, 96, accent=BLUE), 96, 96, 'Controles', 'T_Key_R_Resaltada.png')
    save(keycap('', 128, 128), 128, 128, 'Controles', 'T_Key_Vacia_9S.png')


# ============================================================================ SALUD
HS = 256


def heart_pts(sc=6.6, n=360, dx=0, dy=0):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((HS / 2 + dx + x * sc, HS / 2 + dy - (y + 2.5) * sc))
    return pts


def hu(x, y, sc=6.6):
    """unidades de corazon -> px (256)"""
    return (HS / 2 + x * sc, HS / 2 - (y + 2.5) * sc)


def heart_mask(pts=None):
    m = Image.new('L', (HS * S, HS * S), 0)
    ImageDraw.Draw(m).polygon([(x * S, y * S) for x, y in (pts or heart_pts())], fill=255)
    return m


def heart_sprite(mask, c1, c2, shine=1.0):
    w, h = mask.size
    base = masked(grad_v(w, h, c1, c2), mask)
    d = ImageDraw.Draw(base, 'RGBA')
    hl = Image.new('RGBA', base.size, (0, 0, 0, 0))
    hd = ImageDraw.Draw(hl)
    hd.ellipse(L(52, 62, 100, 96), fill=(255, 255, 255, int(150 * shine)))
    hl = hl.filter(ImageFilter.GaussianBlur(5 * S))
    base = Image.alpha_composite(base, masked(hl, mask))
    # borde interior sutil
    er = mask.filter(ImageFilter.MinFilter(5 * S // 2 * 2 + 1))
    rim = ImageChops.subtract(mask, er)
    rimc = Image.new('RGBA', base.size, (255, 255, 255, 60))
    base = Image.alpha_composite(base, masked(rimc, rim))
    return base


def zig(pts_u, sc=6.6):
    return [hu(x, y, sc) for x, y in pts_u]


def heart_sano():
    m = heart_mask()
    sp = heart_sprite(m, (255, 96, 96), (186, 28, 40))
    save(with_outline(sp, 7), HS, HS, 'Salud', 'T_Heart_Sano.png')


def heart_herido():
    m = heart_mask()
    sp = heart_sprite(m, (255, 176, 82), (214, 92, 28), 0.7)
    d = ImageDraw.Draw(sp)
    crack = [(x * S, y * S) for x, y in zig([(0, 5.2), (-2.2, 1.0), (1.4, -2.2), (-1.6, -5.2), (0.8, -8.8)])]
    d.line(crack, fill=(70, 24, 10, 255), width=6 * S, joint='curve')
    # vendaje
    bd, bm = cv(HS, HS)
    bm.rounded_rectangle(L(138, 118, 222, 146), radius=10 * S, fill=(236, 220, 176, 255))
    bm.rounded_rectangle(L(138, 118, 222, 146), radius=10 * S, outline=(160, 140, 96, 255), width=3 * S)
    for x in (156, 172, 188, 204):
        bm.ellipse(L(x - 2.5, 129.5, x + 2.5, 134.5), fill=(160, 140, 96, 255))
    bd = bd.rotate(-35, resample=Image.BICUBIC, center=(180 * S, 132 * S))
    sp = Image.alpha_composite(sp, masked(bd, m))
    save(with_outline(sp, 7), HS, HS, 'Salud', 'T_Heart_Herido.png')


def heart_critico():
    m = heart_mask()
    cut = zig([(0.0, 16), (0.0, 7), (-1.8, 3), (1.8, -2), (-1.4, -7), (1.4, -12), (0, -19)])
    left_poly = cut + [hu(-30, -19), hu(-30, 16)]
    right_poly = cut + [hu(30, -19), hu(30, 16)]
    halves = []
    for poly, ang, off in ((left_poly, 8, (-8, 2)), (right_poly, -6, (7, 6))):
        pm = Image.new('L', m.size, 0)
        ImageDraw.Draw(pm).polygon([(x * S, y * S) for x, y in poly], fill=255)
        hm = ImageChops.multiply(m, pm)
        sp = heart_sprite(hm, (148, 38, 52), (72, 8, 22), 0.35)
        sp = sp.rotate(ang, resample=Image.BICUBIC, center=(128 * S, 205 * S))
        sh = Image.new('RGBA', sp.size, (0, 0, 0, 0))
        sh.alpha_composite(sp, (int(off[0] * S), int(off[1] * S)))
        halves.append(sh)
    sp = Image.alpha_composite(halves[0], halves[1])
    k = 0.84
    small = sp.resize((int(sp.width * k), int(sp.height * k)), Image.LANCZOS)
    sp = Image.new('RGBA', sp.size, (0, 0, 0, 0))
    sp.alpha_composite(small, ((sp.width - small.width) // 2, int(sp.height * 0.10)))
    # gota de sangre
    d = ImageDraw.Draw(sp)
    gx, gy = 128 * S, 222 * S
    d.polygon([(gx, gy - 22 * S), (gx - 8 * S, gy), (gx + 8 * S, gy)], fill=(170, 20, 28, 255))
    d.ellipse([gx - 8 * S, gy - 8 * S, gx + 8 * S, gy + 8 * S], fill=(170, 20, 28, 255))
    save(with_outline(sp, 7), HS, HS, 'Salud', 'T_Heart_Critico.png')


def heart_extras():
    m = heart_mask()
    # contorno blanco tintable
    er = m.filter(ImageFilter.MinFilter(21 * S // 2 * 2 + 1))
    ring = ImageChops.subtract(m, er)
    out = Image.new('RGBA', m.size, (255, 255, 255, 255))
    out.putalpha(ring)
    save(out, HS, HS, 'Salud', 'T_Heart_Contorno.png')
    # fondo vacio
    bg = masked(grad_v(*m.size, (40, 44, 40), (24, 26, 24)), m)
    save(with_outline(bg, 7, (12, 14, 12, 255)), HS, HS, 'Salud', 'T_Heart_Fondo.png')
    # brillo para pulso
    gl = Image.new('RGBA', m.size, (255, 255, 255, 255))
    gl.putalpha(m.filter(ImageFilter.GaussianBlur(16 * S)).point(lambda v: int(v * 0.9)))
    save(gl, HS, HS, 'Salud', 'T_Heart_Pulso_Glow.png')
    # mascara de relleno (para barra de vida en forma de corazon: llenado vertical en material)
    fin(m, HS, HS).save(path('Salud', 'T_Heart_Mascara.png'), optimize=True)


# ============================================================================ main
for nme, fn in (('Jugador', ic_jugador),):
    save(fn(), 128, 128, 'Minimapa', 'Iconos', 'T_MM_Jugador.png')
ic_cono()
save(ic_soldado('Alpha', BLUE), 128, 128, 'Minimapa', 'Iconos', 'T_MM_Soldado_Alpha.png')
save(ic_soldado('Bravo', TEAL), 128, 128, 'Minimapa', 'Iconos', 'T_MM_Soldado_Bravo.png')
save(ic_medico(), 128, 128, 'Minimapa', 'Iconos', 'T_MM_Medico.png')
for n in ('FlancoIzq', 'FlancoDer', 'BaseAliada', 'BaseEnemiga'):
    save(ic_estructura(n), 128, 128, 'Minimapa', 'Iconos', f'T_MM_Estructura_{n}.png')
ruta_tile(); ruta_flecha(); ruta_nodo(); ruta_destino(); indicador_borde()
marco(); brujula(); mascara_fondo()
badge_with(glyph_walkie(), AMBER, 'T_Comm_Glifo_Walkie.png', 'T_Comm_Modo_Walkie.png')
badge_with(glyph_habla(), BLUE, 'T_Comm_Glifo_Habla.png', 'T_Comm_Modo_Habla.png')
cambio_modo()
keys(); pill('CAMBIAR MODO')
heart_sano(); heart_herido(); heart_critico(); heart_extras()
print('HUD OK')
