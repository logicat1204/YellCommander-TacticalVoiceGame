# -*- coding: utf-8 -*-
import sys, os, math, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

R = sys.argv[1]


def path(*a):
    p = os.path.join(R, *a)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def u8(a):
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def n01(a):
    return (a - a.min()) / (np.ptp(a) + 1e-12)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def pn(n, s, seed):
    """Ruido periodico (tileable) por FFT. s: suavidad (0.5 rugoso ... 2.2 suave)."""
    r = np.random.default_rng(seed)
    fx = np.fft.fftfreq(n)
    f = np.sqrt(fx[:, None] ** 2 + fx[None, :] ** 2)
    f[0, 0] = 1
    spec = (r.normal(size=(n, n)) + 1j * r.normal(size=(n, n))) / f ** s
    spec[0, 0] = 0
    return n01(np.fft.ifft2(spec).real)


def nmap(h, k):
    """Normal map (convencion DirectX / Unreal: verde hacia abajo) desde altura periodica."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * k
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * k
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def ao_of(h, strength=3.0):
    a = ndi.gaussian_filter(h, 8, mode='wrap') - h
    return 1 - np.clip(a * strength, 0, 1) * 0.7


def save_set(name, col, h, rough, metal, nk, aos=3.0):
    Image.fromarray(u8(col), 'RGB').save(path('Textures', 'Tileable', f'T_{name}_BC.png'), optimize=True)
    Image.fromarray(u8(nmap(h, nk)), 'RGB').save(path('Textures', 'Tileable', f'T_{name}_N.png'), optimize=True)
    orm = np.stack([ao_of(h, aos), rough, metal], -1)
    Image.fromarray(u8(orm), 'RGB').save(path('Textures', 'Tileable', f'T_{name}_ORM.png'), optimize=True)


N = 1024
yy, xx = np.mgrid[0:N, 0:N]

# ============================================================================ texturas tileables
def concreto():
    h = 0.5 * pn(N, 1.6, 11) + 0.3 * pn(N, 1.0, 12) + 0.2 * pn(N, 0.6, 13)
    seam = (np.exp(-(((yy % 256) - 0) / 1.5) ** 2) + np.exp(-(((yy % 256) - 256) / 1.5) ** 2) +
            np.exp(-(((xx % 512) - 0) / 1.5) ** 2) + np.exp(-(((xx % 512) - 512) / 1.5) ** 2))
    seam = np.clip(seam, 0, 1)
    pits = n01(ndi.gaussian_filter((pn(N, 0.4, 14) > 0.965).astype(float), 1.2, mode='wrap'))
    hh = h - 0.35 * seam - 0.3 * pits
    stain = n01(ndi.gaussian_filter(pn(N, 0.5, 15), (35, 2), mode='wrap'))
    base = 0.40 + 0.25 * h
    col = base[..., None] * np.array([1.0, 0.985, 0.95])
    col *= ((1 - 0.30 * stain) * (1 - 0.35 * seam) * (1 - 0.4 * pits))[..., None]
    save_set('Concreto', col, hh, 0.72 + 0.2 * pn(N, 1.2, 16), np.zeros((N, N)), 40)


def tierra():
    h = 0.6 * pn(N, 1.5, 21) + 0.4 * pn(N, 0.8, 22)
    hp = pn(N, 0.35, 23)
    peb = sstep(0.80, 0.86, ndi.gaussian_filter(hp, 1.5, mode='wrap') * 0 + hp)
    peb = n01(ndi.gaussian_filter(peb, 1.0, mode='wrap'))
    crack = np.exp(-((pn(N, 1.3, 24) - 0.5) / 0.012) ** 2)
    hh = h + 0.35 * peb - 0.25 * crack
    var = pn(N, 1.2, 25)
    col = np.array([0.34, 0.25, 0.17]) * (0.65 + 0.7 * var)[..., None]
    col = col * (1 - peb[..., None] * 0.0) + peb[..., None] * np.array([0.12, 0.11, 0.10])
    col *= (1 - 0.5 * crack)[..., None]
    save_set('Tierra', col, hh, 0.88 + 0.1 * pn(N, 1.0, 26), np.zeros((N, N)), 55)


def saco():
    p = 8
    fx, fy = (xx % p) / p, (yy % p) / p
    par = ((xx // p) + (yy // p)) % 2
    weave = np.where(par == 1, np.sin(np.pi * fx), np.sin(np.pi * fy)) ** 0.8
    wr = pn(N, 1.7, 31)
    h = 0.55 * weave + 0.45 * wr
    dirt = pn(N, 1.3, 32)
    col = np.array([0.58, 0.50, 0.34]) * (0.62 + 0.45 * weave)[..., None] * (0.7 + 0.5 * dirt)[..., None]
    col *= np.array([1.0, 0.98, 0.9])
    save_set('Saco', col, h, 0.95 + 0 * h, np.zeros((N, N)), 30, 4.0)


def roca():
    st = n01(ndi.gaussian_filter(np.random.default_rng(41).normal(size=(N, N)), (2, 38), mode='wrap'))
    h = 0.55 * pn(N, 1.3, 42) + 0.25 * pn(N, 0.8, 43) + 0.2 * st
    crack = np.exp(-((pn(N, 1.2, 44) - 0.5) / 0.010) ** 2) + 0.7 * np.exp(-((pn(N, 1.0, 45) - 0.5) / 0.008) ** 2)
    crack = np.clip(crack, 0, 1)
    hh = h - 0.4 * crack
    tint = pn(N, 1.6, 46)
    col = (np.array([0.47, 0.43, 0.38]) * (0.65 + 0.6 * h)[..., None] *
           (0.9 + 0.2 * (tint - 0.5))[..., None] * np.array([1.0, 1.0, 1.0]))
    col += np.array([0.03, 0.02, -0.01]) * (st - 0.5)[..., None] * 2
    col *= (1 - 0.55 * crack)[..., None]
    save_set('Roca', col, hh, 0.85 + 0.12 * pn(N, 1.0, 47), np.zeros((N, N)), 70, 3.5)


def metal():
    base = 0.6 * pn(N, 1.5, 51) + 0.4 * pn(N, 0.7, 52)
    sc = ndi.gaussian_filter(np.random.default_rng(53).normal(size=(N, N)), (0.6, 14), mode='wrap')
    scr = sstep(1.6 * sc.std(), 2.6 * sc.std(), sc)
    sc2 = ndi.gaussian_filter(np.random.default_rng(54).normal(size=(N, N)), (10, 0.6), mode='wrap')
    scr = np.clip(scr + sstep(1.8 * sc2.std(), 2.8 * sc2.std(), sc2), 0, 1)
    wear = sstep(0.72, 0.9, pn(N, 1.1, 55)) * 0.6
    rivet = np.zeros((N, N))
    gx, gy = (xx % 128) - 64, (yy % 128) - 64
    rivet = np.exp(-(gx ** 2 + gy ** 2) / (2 * 3.2 ** 2)) * 0.6
    seam = np.clip(np.exp(-(((yy % 512) - 0) / 1.4) ** 2) + np.exp(-(((yy % 512) - 512) / 1.4) ** 2), 0, 1)
    hh = 0.25 * base + rivet - 0.4 * seam - 0.15 * scr
    mask = np.clip(scr + wear, 0, 1)
    paint = np.array([0.16, 0.20, 0.14]) * (0.75 + 0.5 * base)[..., None]
    bare = np.array([0.42, 0.36, 0.30]) * (0.8 + 0.4 * pn(N, 1.0, 56))[..., None]
    col = paint * (1 - mask[..., None]) + bare * mask[..., None]
    col *= (1 - 0.4 * seam)[..., None]
    save_set('Metal', col, hh, 0.55 + 0.25 * mask, 0.85 * mask, 35)


def pasto():
    bl = n01(ndi.gaussian_filter(np.random.default_rng(61).normal(size=(N, N)), (6, 0.8), mode='wrap'))
    h = 0.5 * bl + 0.5 * pn(N, 1.0, 62)
    v = pn(N, 1.3, 63)
    dry = np.array([0.45, 0.41, 0.20]); green = np.array([0.30, 0.38, 0.16])
    col = (dry * v[..., None] + green * (1 - v[..., None])) * (0.65 + 0.7 * bl)[..., None]
    save_set('Pasto', col, h, 0.92 + 0 * h, np.zeros((N, N)), 22, 2.5)


for fn in (concreto, tierra, saco, roca, metal, pasto):
    fn()
print('texturas tileables OK')

# ============================================================================ paletas (soldados / armas)
def palette_images(cells, colors, orm, name_bc, name_orm, grid=GRID, cp=CELL_PX):
    S = grid * cp
    bc = np.zeros((S, S, 3), np.uint8) + 40
    om = np.zeros((S, S, 3), np.uint8)
    om[..., 0] = 255; om[..., 1] = 230
    for i, nme in enumerate(cells):
        c, r = i % grid, i // grid
        bc[r * cp:(r + 1) * cp, c * cp:(c + 1) * cp] = colors[nme]
        ro, me = orm[nme]
        om[r * cp:(r + 1) * cp, c * cp:(c + 1) * cp] = (255, int(ro * 255), int(me * 255))
    Image.fromarray(bc, 'RGB').save(name_bc, optimize=True)
    if name_orm:
        Image.fromarray(om, 'RGB').save(name_orm, optimize=True)


for vname, pal in PALETTES.items():
    cols = {k: hexc(v) for k, v in pal.items()}
    palette_images(CELLS, cols, ORM_VALS, path('Textures', 'Soldado', f'T_Soldado_{vname}_BC.png'),
                   path('Textures', 'Soldado', 'T_Soldado_ORM.png') if vname == 'Alpha' else None)
palette_images(WCELLS, {k: hexc(v) for k, v in WPAL.items()}, WORM, path('Textures', 'Armas', 'T_Armas_BC.png'),
               path('Textures', 'Armas', 'T_Armas_ORM.png'))
print('paletas OK')

# ============================================================================ terreno Valle Alfa
NL, SZ = LAND_N, MAP_SIZE_M
xs = np.linspace(0, SZ, NL)
X, Y = np.meshgrid(xs, xs)
nz = lambda s, seed: pn(1024, s, seed)[:NL, :NL]
base = (nz(2.0, 1) - 0.5) * 4.0 + (nz(1.2, 2) - 0.5) * 1.0
ridge = 9 * np.exp(-((Y - 26) / 8) ** 2) * (1 - np.exp(-((X - 126) / 7) ** 4)) * (0.75 + 0.5 * nz(1.5, 3))
d = np.minimum.reduce([X, Y, SZ - X, SZ - Y])
border = 8 * sstep(16, 0, d) * (0.7 + 0.6 * nz(1.3, 4))
hill = np.minimum(12 * np.exp(-(((X - 175) ** 2 + (Y - 60) ** 2) / (2 * 17 ** 2))), 10.5)
mounds = np.zeros_like(X)
for (mx, my, mh, mr) in [(110, 84, 3.0, 7), (112, 170, 3.2, 7), (150, 100, 2.5, 6), (150, 152, 2.5, 6),
                         (80, 100, 2.0, 6), (80, 155, 2.2, 6), (60, 60, 3.0, 9), (60, 195, 3.0, 9)]:
    mounds += mh * np.exp(-(((X - mx) ** 2 + (Y - my) ** 2) / (mr ** 2)))
rockm = np.clip((ridge + border + hill) / 6.0, 0, 1)
detail = (nz(0.9, 7) - 0.5) * 1.4 + (nz(0.6, 8) - 0.5) * 3.2 * rockm + (nz(1.1, 9) - 0.5) * 3.0 * sstep(0.2, 1.0, rockm)
H = base + ridge + border + hill + mounds + detail
xc = 126 + 5 * np.sin(Y / 37)
rv = -5.0 * np.exp(-((X - xc) / 7.5) ** 2) * (1 - np.exp(-((Y - 126) / 10) ** 4)) * sstep(34, 48, Y)
H = H + rv


def lerp_to(H, mask, target):
    return H * (1 - mask) + target * mask


H = lerp_to(H, sstep(24, 13, np.hypot(X - 214, Y - 126)), 3.0 + 0.08 * (nz(0.8, 5) - 0.5))      # meseta del bunker
pl = Image.new('L', (NL, NL), 0)
dr = ImageDraw.Draw(pl)
px = lambda x, y: (x / SZ * (NL - 1), y / SZ * (NL - 1))
dr.line([px(30, 100), px(38, 112), px(38, 140), px(30, 154)], fill=255, width=6)
dist_tr = ndi.distance_transform_edt(np.array(pl) == 0) * (SZ / (NL - 1))
H = lerp_to(H, sstep(10, 4, dist_tr), 0.4)                                                       # base de trinchera
H = lerp_to(H, sstep(15, 10, np.hypot(X - 126, Y - 232)), 0.8)                                   # extraccion
H = ndi.gaussian_filter(H, 1.0)
H = np.clip(H, -8.0, 20.0)
val = np.clip(32768 + H * 1280, 0, 65535).astype(np.uint16)       # ZScale=10 -> 1 m = 1280 niveles
Image.fromarray(val).save(path('Terrain', 'Heightmap_ValleAlfa_1009.png'))
val.astype('<u2').tofile(path('Terrain', 'Heightmap_ValleAlfa_1009.r16'))

gy, gx = np.gradient(H, SZ / (NL - 1))
slope = np.hypot(gx, gy)
paths = [[(34, 126), (126, 126), (214, 126)], [(126, 126), (112, 90), (100, 62), (126, 36), (126, 22)],
         [(126, 126), (112, 160), (100, 192), (126, 225), (126, 232)], [(214, 126), (190, 95), (175, 60)]]
pm = Image.new('L', (NL, NL), 0)
dr = ImageDraw.Draw(pm)
for pth in paths:
    dr.line([px(*p) for p in pth], fill=255, width=7, joint='curve')
dist_pa = ndi.distance_transform_edt(np.array(pm) == 0) * (SZ / (NL - 1))
roca_w = np.clip(sstep(0.40, 0.85, slope) + 0.7 * sstep(6.5, 9.5, H) * 0 + 0.5 * sstep(5.0, 8.0, H) * sstep(0.25, 0.5, slope), 0, 1)
tierra_w = np.clip(sstep(3.5, 1.2, dist_pa) * (0.55 + 0.6 * nz(0.9, 6)) + sstep(-1.5, -3.5, rv) * 0.8 +
                   sstep(10, 4, dist_tr) * 0.7 + sstep(15, 10, np.hypot(X - 126, Y - 232)) * 0.6 +
                   sstep(20, 13, np.hypot(X - 214, Y - 126)) * 0.5, 0, 1)
tierra_w *= (1 - roca_w)
pasto_w = np.clip(1 - roca_w - tierra_w, 0, 1) + 0.05
stack = np.stack([pasto_w, tierra_w, roca_w], 0)
stack = stack / stack.sum(0, keepdims=True)
for i, nme in enumerate(['Pasto', 'Tierra', 'Roca']):
    Image.fromarray(u8(stack[i]), 'L').save(path('Terrain', 'Layers', f'L_{nme}.png'))

hs = np.clip(0.55 + (-gx * 0.7 - gy * 0.7) * 0.9, 0.15, 1.1)
colmap = (stack[0][..., None] * np.array([0.42, 0.46, 0.27]) + stack[1][..., None] * np.array([0.56, 0.46, 0.33]) +
          stack[2][..., None] * np.array([0.46, 0.44, 0.41]))
colmap = colmap * hs[..., None] * 1.15
colmap *= (1 - 0.25 * sstep(-1.0, -4.5, rv))[..., None]
mm = Image.fromarray(u8(colmap), 'RGB').resize((1024, 1024), Image.LANCZOS)
mm.save(path('Terrain', 'T_Minimapa_ValleAlfa.png'))
ref = mm.copy().convert('RGBA')
dr = ImageDraw.Draw(ref)
fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)
for nme, (zx, zy, zr) in ZONES.items():
    cx, cy, rr = zx / SZ * 1024, zy / SZ * 1024, zr / SZ * 1024
    dr.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 255, 255, 230), width=2)
    dr.text((cx, cy - rr - 4), nme, font=fnt, fill=(255, 255, 255, 255), anchor='ms', stroke_width=3, stroke_fill=(0, 0, 0, 255))
ref.convert('RGB').save(path('Terrain', 'Referencia_Zonas_ValleAlfa.png'))

# DT_Zonas.csv  (coordenadas en uu relativas a la esquina; Landscape en (0,0,0), escala XY=25, Z=10)
alias = {'trinchera': 'trinchera;la trinchera;posicion defensiva;las trincheras',
         'puerta_norte': 'puerta norte;acceso norte;entrada norte;la puerta;el norte',
         'flanco_izquierdo': 'flanco izquierdo;lado izquierdo;por la izquierda;izquierda',
         'flanco_derecho': 'flanco derecho;lado derecho;por la derecha;derecha',
         'puente': 'puente;el puente;paso central;el cruce',
         'colina': 'colina;la colina;loma;la cima', 'torre_vigia': 'torre de vigia;torre;la torre;atalaya',
         'bunker_este': 'bunker;bunker este;el bunker;fortin;bunker enemigo;objetivo',
         'punto_extraccion': 'punto de extraccion;extraccion;zona de extraccion;evacuacion'}
tag = lambda n: ''.join(p.capitalize() for p in n.split('_'))
rows = ['Name,ZonaTag,NombreES,Alias,Ubicacion,Radio,Rol']
for nme, (zx, zy, zr) in ZONES.items():
    zz = float(H[int(zy / SZ * (NL - 1)), int(zx / SZ * (NL - 1))]) * 100
    rol = {'trinchera': 'defensa', 'bunker_este': 'objetivo_ofensivo', 'punto_extraccion': 'extraccion',
           'colina': 'vigilancia', 'torre_vigia': 'vigilancia', 'puente': 'cuello_de_botella'}.get(nme, 'transito')
    rows.append(f'{nme},"(TagName=""Zona.{tag(nme)}"")",{nme.replace("_", " ")},"{alias[nme]}",'
                f'"(X={zx * 100:.1f},Y={zy * 100:.1f},Z={zz:.1f})",{zr * 100:.0f},{rol}')
open(path('Data', 'DT_Zonas.csv'), 'w', encoding='utf-8').write('\n'.join(rows) + '\n')
print('terreno OK  h[min,max]=', round(float(H.min()), 2), round(float(H.max()), 2))

# ============================================================================ UI
S = 4
W = (255, 255, 255, 255)
BLU = (94, 160, 255, 255)
L = lambda *p: [c * S for c in p]
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'


def canvas(w, h):
    im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def done(im, w, h, *p):
    im.resize((w, h), Image.LANCZOS).save(path(*p), optimize=True)


def icon(nme, fn):
    im, d = canvas(128, 128)
    fn(d)
    done(im, 128, 128, 'UI', 'Icons', f'T_Icon_{nme}.png')


def circ(d, cx, cy, r, **k):
    d.ellipse(L(cx - r, cy - r, cx + r, cy + r), **k)


def i_mover(d):
    d.line(L(26, 100, 84, 42), fill=W, width=10 * S)
    d.polygon(L(72, 26, 106, 22, 102, 56), fill=W)
    circ(d, 24, 102, 9, outline=W, width=5 * S)


def i_atacar(d):
    circ(d, 64, 64, 36, outline=W, width=7 * S)
    for a in (L(64, 14, 64, 40), L(64, 88, 64, 114), L(14, 64, 40, 64), L(88, 64, 114, 64)):
        d.line(a, fill=W, width=7 * S)
    circ(d, 64, 64, 6, fill=W)


def i_defender(d):
    pts = L(64, 14, 106, 28, 102, 70, 64, 114, 26, 70, 22, 28)
    d.polygon(pts, outline=W, width=7 * S)
    d.line(L(64, 30, 64, 96), fill=W, width=5 * S)
    d.line(L(40, 52, 88, 52), fill=W, width=5 * S)


def i_curar(d):
    d.rounded_rectangle(L(50, 18, 78, 110), radius=6 * S, fill=W)
    d.rounded_rectangle(L(18, 50, 110, 78), radius=6 * S, fill=W)


def i_seguir(d):
    d.line(L(28, 32, 60, 64, 28, 96), fill=W, width=11 * S, joint='curve')
    d.line(L(68, 32, 100, 64, 68, 96), fill=W, width=11 * S, joint='curve')


def i_vigilar(d):
    top = [(64 + 48 * t, 64 - 30 * (1 - t * t)) for t in np.linspace(-1, 1, 30)]
    bot = [(64 + 48 * t, 64 + 30 * (1 - t * t)) for t in np.linspace(1, -1, 30)]
    d.line([(x * S, y * S) for x, y in top + bot + top[:1]], fill=W, width=7 * S, joint='curve')
    circ(d, 64, 64, 15, fill=W)
    circ(d, 59, 59, 4, fill=(0, 0, 0, 0))


def i_formar(d):
    for (x, y) in [(64, 30), (38, 64), (90, 64), (24, 100), (64, 100), (104, 100)]:
        circ(d, x, y, 10, fill=W)


def i_cesar(d):
    pts = [(64 + 48 * math.cos(math.radians(22.5 + 45 * k)), 64 + 48 * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    d.polygon([(x * S, y * S) for x, y in pts], outline=W, width=7 * S)
    d.rounded_rectangle(L(36, 56, 92, 72), radius=3 * S, fill=W)


def i_reportar(d):
    d.rounded_rectangle(L(34, 44, 94, 114), radius=8 * S, outline=W, width=7 * S)
    d.line(L(78, 44, 90, 14), fill=W, width=7 * S)
    for y in (62, 74, 86):
        d.line(L(46, y, 82, y), fill=W, width=5 * S)
    circ(d, 64, 102, 4, fill=W)


def i_cancelar(d):
    circ(d, 64, 64, 46, outline=W, width=8 * S)
    d.line(L(40, 40, 88, 88), fill=W, width=9 * S)
    d.line(L(88, 40, 40, 88), fill=W, width=9 * S)


def i_aclarar(d):
    circ(d, 64, 64, 46, outline=W, width=8 * S)
    f = ImageFont.truetype(FB, 74 * S)
    d.text((64 * S, 66 * S), '?', font=f, fill=W, anchor='mm')


def i_check(d):
    d.line(L(22, 68, 52, 96, 106, 34), fill=W, width=15 * S, joint='curve')


def i_cross(d):
    d.line(L(28, 28, 100, 100), fill=W, width=15 * S)
    d.line(L(100, 28, 28, 100), fill=W, width=15 * S)


def i_ellipsis(d):
    for x in (28, 64, 100):
        circ(d, x, 64, 12, fill=W)


def i_mic(d):
    d.rounded_rectangle(L(48, 14, 80, 70), radius=16 * S, outline=W, width=7 * S)
    d.arc(L(32, 40, 96, 100), 0, 180, fill=W, width=7 * S)
    d.line(L(64, 100, 64, 114), fill=W, width=7 * S)
    d.line(L(44, 114, 84, 114), fill=W, width=7 * S)


def i_mic_off(d):
    i_mic(d)
    d.line(L(22, 20, 106, 108), fill=(0, 0, 0, 0), width=17 * S)
    d.line(L(22, 20, 106, 108), fill=W, width=8 * S)


def i_alerta(d):
    d.polygon(L(64, 16, 116, 106, 12, 106), outline=W, width=7 * S)
    d.line(L(64, 48, 64, 78), fill=W, width=9 * S)
    circ(d, 64, 93, 5, fill=W)


for nme, fn in dict(Mover=i_mover, Atacar=i_atacar, Defender=i_defender, Curar=i_curar, Seguir=i_seguir,
                    Vigilar=i_vigilar, Formar=i_formar, CesarFuego=i_cesar, Reportar=i_reportar,
                    Cancelar=i_cancelar, Aclarar=i_aclarar, Check=i_check, Cruz=i_cross, Puntos=i_ellipsis,
                    Mic=i_mic, MicOff=i_mic_off, Alerta=i_alerta).items():
    icon(nme, fn)

# --- kit HUD
def panel9s(w, h, fill, border, tick, name, rad=0):
    im, d = canvas(w, h)
    d.rectangle(L(1, 1, w - 2, h - 2), fill=fill, outline=border, width=2 * S)
    t = 14
    for (x, y, sx, sy) in [(1, 1, 1, 1), (w - 2, 1, -1, 1), (1, h - 2, 1, -1), (w - 2, h - 2, -1, -1)]:
        d.line(L(x, y + sy * t, x, y, x + sx * t, y), fill=tick, width=4 * S)
    done(im, w, h, 'UI', 'Kit', name)


panel9s(128, 128, (10, 26, 52, 150), (94, 160, 255, 220), (170, 215, 255, 255), 'T_UI_Panel_9S.png')
panel9s(128, 128, (10, 26, 52, 70), (94, 160, 255, 120), (170, 215, 255, 200), 'T_UI_Panel_Ligero_9S.png')
for nme, (f, b, t) in dict(Normal=((14, 34, 70, 170), (94, 160, 255, 230), (170, 215, 255, 255)),
                           Hover=((24, 58, 112, 200), (150, 200, 255, 255), (255, 255, 255, 255)),
                           Pressed=((60, 120, 220, 230), (255, 255, 255, 255), (255, 255, 255, 255)),
                           Disabled=((30, 34, 40, 120), (110, 120, 135, 150), (130, 140, 150, 160))).items():
    panel9s(256, 64, f, b, t, f'T_UI_Boton_{nme}_9S.png')
im, d = canvas(256, 24)
d.rectangle(L(1, 1, 254, 22), outline=(94, 160, 255, 230), width=2 * S)
done(im, 256, 24, 'UI', 'Kit', 'T_UI_Barra_Marco.png')
g = np.zeros((24, 256, 4), np.uint8)
g[..., :3] = 255
g[..., 3] = (255 * (0.78 + 0.22 * np.linspace(1, 0, 24))[:, None] * np.ones((1, 256))).astype(np.uint8)
Image.fromarray(g, 'RGBA').save(path('UI', 'Kit', 'T_UI_Barra_Relleno.png'))
g = np.zeros((64, 64, 4), np.uint8); g[..., :3] = (94, 160, 255); g[:, -1, 3] = 46; g[-1, :, 3] = 46
g[::16, :, 3] = np.maximum(g[::16, :, 3], 18); g[:, ::16, 3] = np.maximum(g[:, ::16, 3], 18)
Image.fromarray(g, 'RGBA').save(path('UI', 'Kit', 'T_UI_Rejilla_Tile.png'))
sb = np.zeros((96, 1024, 4), np.uint8); sb[..., :3] = 0
prof = np.clip(np.sin(np.linspace(0, np.pi, 1024)) * 2.2, 0, 1) ** 0.8
sb[..., 3] = (170 * prof[None, :]).astype(np.uint8)
Image.fromarray(sb, 'RGBA').save(path('UI', 'Kit', 'T_UI_Subtitulos_Banda.png'))
im, d = canvas(256, 8)
d.line(L(0, 4, 256, 4), fill=(94, 160, 255, 200), width=2 * S)
d.rectangle(L(0, 1, 18, 7), fill=(170, 215, 255, 255))
done(im, 256, 8, 'UI', 'Kit', 'T_UI_Divisor.png')
im, d = canvas(64, 64)
circ(d, 32, 32, 28, fill=(200, 55, 45, 255), outline=W, width=3 * S)
done(im, 64, 64, 'UI', 'Kit', 'T_UI_Insignia_Circulo.png')

# --- indicador de microfono (UI-03)
im, d = canvas(256, 256)
circ(d, 128, 128, 112, outline=W, width=6 * S)
circ(d, 128, 128, 96, outline=(255, 255, 255, 110), width=2 * S)
for k in range(24):
    a = math.radians(k * 15)
    r0, r1 = (118, 126) if k % 2 else (118, 130)
    d.line(L(128 + r0 * math.cos(a), 128 + r0 * math.sin(a), 128 + r1 * math.cos(a), 128 + r1 * math.sin(a)), fill=W, width=3 * S)
done(im, 256, 256, 'UI', 'Mic', 'T_UI_Mic_Anillo.png')
yy2, xx2 = np.mgrid[0:256, 0:256]
r = np.hypot(xx2 - 127.5, yy2 - 127.5) / 128
disc = np.zeros((256, 256, 4), np.uint8); disc[..., :3] = 255
disc[..., 3] = u8(np.clip(1 - sstep(0.62, 0.72, r), 0, 1) * 0.92 + (1 - sstep(0.72, 1.0, r)) * 0.25 * (r > 0.72))
Image.fromarray(disc, 'RGBA').save(path('UI', 'Mic', 'T_UI_Mic_Disco.png'))
glow = np.zeros((256, 256, 4), np.uint8); glow[..., :3] = 255; glow[..., 3] = u8((1 - sstep(0.2, 1.0, r)) ** 2 * 0.9)
Image.fromarray(glow, 'RGBA').save(path('UI', 'Mic', 'T_UI_Mic_Resplandor.png'))
im, d = canvas(16, 64)
d.rounded_rectangle(L(2, 2, 14, 62), radius=6 * S, fill=W)
done(im, 16, 64, 'UI', 'Mic', 'T_UI_Mic_BarraOnda.png')

# --- marcadores (UI-04)
im, d = canvas(128, 128)
d.polygon(L(64, 10, 110, 70, 80, 70, 80, 118, 48, 118, 48, 70, 18, 70), fill=W)
done(im, 128, 128, 'UI', 'Markers', 'T_Marker_Flecha.png')
im, d = canvas(128, 128)
d.polygon(L(64, 8, 120, 64, 64, 120, 8, 64), outline=W, width=7 * S)
circ(d, 64, 64, 10, fill=W)
done(im, 128, 128, 'UI', 'Markers', 'T_Marker_Objetivo.png')
im, d = canvas(128, 128)
circ(d, 64, 64, 54, fill=W)
done(im, 128, 128, 'UI', 'Markers', 'T_Marker_Aliado_Circulo.png')
im, d = canvas(128, 128)
d.polygon(L(64, 6, 122, 64, 64, 122, 6, 64), fill=W)
done(im, 128, 128, 'UI', 'Markers', 'T_Marker_Enemigo_Rombo.png')
im, d = canvas(256, 256)
for i, (rad, a) in enumerate([(120, 255), (92, 170), (64, 100), (36, 60)]):
    circ(d, 128, 128, rad, outline=(255, 255, 255, a), width=6 * S)
done(im, 256, 256, 'UI', 'Markers', 'T_Marker_Ping.png')
im, d = canvas(512, 512)
circ(d, 256, 256, 236, outline=W, width=10 * S)
circ(d, 256, 256, 206, outline=(255, 255, 255, 140), width=3 * S)
for k in range(8):
    a = math.radians(k * 45)
    d.line(L(256 + 236 * math.cos(a), 256 + 236 * math.sin(a), 256 + 190 * math.cos(a), 256 + 190 * math.sin(a)), fill=W, width=9 * S)
glow = Image.new('RGBA', (512 * S, 512 * S), (0, 0, 0, 0))
done(im, 512, 512, 'UI', 'Markers', 'T_Decal_AnilloDestino.png')
im, d = canvas(512, 512)
for k in range(36):
    d.arc(L(24, 24, 488, 488), k * 10, k * 10 + 6, fill=W, width=10 * S)
done(im, 512, 512, 'UI', 'Markers', 'T_Decal_Seleccion.png')

# --- fuentes
fd = '/usr/share/fonts/truetype/dejavu/'
for f in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'DejaVuSansMono.ttf', 'DejaVuSansMono-Bold.ttf'):
    shutil.copy(fd + f, path('UI', 'Fonts', f))
for lic in ('/usr/share/doc/fonts-dejavu-core/copyright', '/usr/share/doc/fonts-dejavu-core/LICENSE'):
    if os.path.exists(lic):
        shutil.copy(lic, path('UI', 'Fonts', 'LICENCIA_DejaVu.txt'))
        break
print('UI OK')

# ============================================================================ VFX sprites
def flipbook(fn, name, frames=16, cell=256):
    sh = np.zeros((cell * 4, cell * 4, 4), np.float32)
    for i in range(frames):
        r_, c_ = divmod(i, 4)
        sh[r_ * cell:(r_ + 1) * cell, c_ * cell:(c_ + 1) * cell] = fn(i / (frames - 1), cell, i)
    Image.fromarray(u8(sh), 'RGBA').save(path('VFX', 'Textures', name), optimize=True)


def polar(cell):
    y, x = np.mgrid[0:cell, 0:cell]
    x = (x - cell / 2 + 0.5) / (cell / 2); y = (y - cell / 2 + 0.5) / (cell / 2)
    return np.hypot(x, y), np.arctan2(y, x)


def fogonazo(t, cell, i):
    r, th = polar(cell)
    rng = np.random.default_rng(100 + i)
    spike = np.abs(np.cos(3 * th + rng.uniform(0, 6))) ** 2 * 0.7 + np.abs(np.cos(5 * th + rng.uniform(0, 6))) ** 3 * 0.5
    size = 0.22 + 0.55 * np.sin(np.pi * min(1, t * 1.25 + 0.1)) ** 0.7
    star = np.exp(-(r / (0.10 + size * spike * 0.8)) ** 1.6)
    core = np.exp(-(r / (0.08 + 0.10 * size)) ** 2)
    inten = (1 - t) ** 1.4
    a = np.clip(inten * (star + core), 0, 1)
    mixv = np.clip(core * 1.2, 0, 1)[..., None]
    rgb = np.array([1.0, 0.52, 0.12]) * (1 - mixv) + np.array([1.0, 0.96, 0.75]) * mixv
    return np.dstack([rgb, a])


def smoke(color, grow, speed):
    def fn(t, cell, i):
        r, th = polar(cell)
        nz1 = pn(cell, 1.3, 200 + i) * 0.6 + pn(cell, 0.8, 300 + i // 2) * 0.4
        R_ = 0.18 + grow * t ** 0.6
        mask = (1 - sstep(R_ * 0.55, R_, r + (nz1 - 0.5) * 0.35)) * np.clip(0.55 + 1.0 * nz1, 0, 1)
        a = mask * (1 - t) ** speed * 0.9
        sh = 0.55 + 0.45 * nz1
        rgb = np.array(color)[None, None, :] * sh[..., None]
        return np.dstack([rgb, np.clip(a, 0, 1)])
    return fn


flipbook(fogonazo, 'T_VFX_Fogonazo_Flipbook4x4.png')
flipbook(smoke((0.66, 0.66, 0.64), 0.85, 0.8), 'T_VFX_Humo_Flipbook4x4.png')
flipbook(smoke((0.58, 0.47, 0.34), 0.7, 1.1), 'T_VFX_Polvo_Flipbook4x4.png')
r, th = polar(256)
rng = np.random.default_rng(7)
sp = np.zeros((256, 256))
for k in range(14):
    a0 = rng.uniform(0, 2 * np.pi); ln = rng.uniform(0.45, 0.95)
    dang = np.abs(((th - a0 + np.pi) % (2 * np.pi)) - np.pi)
    sp = np.maximum(sp, np.exp(-(dang / 0.03) ** 2) * np.clip(1 - r / ln, 0, 1))
a = np.clip(sp + np.exp(-(r / 0.07) ** 2), 0, 1)
Image.fromarray(u8(np.dstack([np.ones((256, 256, 3)) * np.array([1.0, 0.8, 0.45]), a])), 'RGBA').save(path('VFX', 'Textures', 'T_VFX_Chispas.png'))
Image.fromarray(u8(np.dstack([np.ones((128, 128, 3)), (1 - sstep(0.0, 1.0, polar(128)[0])) ** 2])), 'RGBA').save(path('VFX', 'Textures', 'T_VFX_CirculoSuave.png'))
print('VFX OK')
