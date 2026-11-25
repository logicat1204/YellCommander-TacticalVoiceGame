# Compone un HUD de prueba con los assets (verificacion visual). Uso: python3 mock_hud.py <hud_root> <terrain_minimap.png>
import sys, math
import numpy as np
from PIL import Image, ImageDraw
ROOT, MAPF = sys.argv[1], sys.argv[2]
import os; os.chdir(ROOT)
M = Image.open(MAPF).convert('RGBA'); mpx = M.width / 252.0
W, H = 1920, 1080
arr = np.zeros((H, W, 3), np.uint8); yy = np.linspace(0, 1, H)[:, None]
arr[..., 0] = 120 - 50 * yy; arr[..., 1] = 135 - 60 * yy; arr[..., 2] = 110 - 55 * yy
bg = Image.fromarray(arr, 'RGB').convert('RGBA')
A = lambda p: Image.open(p).convert('RGBA')
SC = 0.78; D = int(512 * SC); R = int(218 * SC); view_m = 110.0; ppm = R / view_m; player = (100, 126)
u, v = np.meshgrid(np.arange(D) - D / 2, np.arange(D) - D / 2)
sx = np.clip(((player[0] + (-v) / ppm) * mpx).astype(int), 0, M.width - 1)
sy = np.clip(((player[1] + u / ppm) * mpx).astype(int), 0, M.height - 1)
samp = Image.fromarray(np.array(M)[sy, sx], 'RGBA')
mask = A('Minimapa/Marco/T_MM_Mascara_Circular.png').convert('L').resize((D, D))
mm = A('Minimapa/Marco/T_MM_Fondo_Circular.png').resize((D, D)); mm.paste(samp, (0, 0), mask)


def place(icon, wm, size=44, clamp=True):
    px, py = (wm[1] - player[1]) * ppm, -(wm[0] - player[0]) * ppm      # mirando al este
    dist = math.hypot(px, py); lim = R - size * 0.5 - 6
    if clamp and dist > lim: px, py = px * lim / dist, py * lim / dist
    mm.alpha_composite(A(icon).resize((size, size), Image.LANCZOS), (int(D / 2 + px - size / 2), int(D / 2 + py - size / 2)))


route = [(100, 126), (126, 126), (170, 126), (214, 126)]
pts = [(D / 2 + (p[1] - player[1]) * ppm, D / 2 - (p[0] - player[0]) * ppm) for p in route]
tile = A('Minimapa/Rutas/T_MM_Ruta_Tile.png')
for a, b in zip(pts, pts[1:]):
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 22)); ang = math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
    for k in range(n):
        t = (k + .5) / n; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
        tt = Image.new('RGBA', (40, 40)); tt.paste(tile.resize((40, 10)), (0, 15)); tt = tt.rotate(ang, resample=Image.BICUBIC)
        mm.alpha_composite(tt, (int(x - 20), int(y - 20)))
I = 'Minimapa/Iconos/T_MM_'
place('Minimapa/Rutas/T_MM_Ruta_Destino.png', (214, 126), 46)
place(I + 'Estructura_BaseAliada.png', (34, 126), 50); place(I + 'Estructura_FlancoIzq.png', (100, 62), 46)
place(I + 'Estructura_FlancoDer.png', (100, 192), 46); place(I + 'Estructura_BaseEnemiga.png', (214, 126), 50)
cone = A(I + 'Cono_Vision.png').resize((int(D * .5),) * 2)
tint = Image.new('RGBA', cone.size, (47, 123, 255, 255)); tint.putalpha(cone.getchannel('A').point(lambda v: int(v * .7)))
mm.alpha_composite(tint, (D // 2 - cone.width // 2, D // 2 - cone.height // 2))
for nm, p in (('Soldado_Alpha', (90, 116)), ('Soldado_Alpha', (92, 138)), ('Soldado_Bravo', (84, 126)),
              ('Soldado_Bravo', (80, 146)), ('Medico', (82, 108))):
    place(I + nm + '.png', p, 36)
place(I + 'Jugador.png', player, 40, False)
mm.alpha_composite(A('Minimapa/Marco/T_MM_Brujula_Rotante.png').resize((D, D)).rotate(90, resample=Image.BICUBIC))
mm.alpha_composite(A('Minimapa/Marco/T_MM_Marco_Circular.png').resize((D, D)))
bg.alpha_composite(mm, (W - D - 40, 40))
for i, n in enumerate(['Sano', 'Herido', 'Critico']):
    bg.alpha_composite(A(f'Salud/T_Heart_{n}.png').resize((120, 120)), (48 + i * 130, H - 170))
bg.alpha_composite(A('Comunicacion/T_Comm_Modo_Habla.png').resize((120, 120)), (48, H - 310))
bg.alpha_composite(A('Comunicacion/T_Comm_Modo_Walkie.png').resize((120, 120)), (178, H - 310))
bg.alpha_composite(A('Controles/T_Prompt_R_CambiarModo.png').resize((390, 72)), (W - D - 40 + (D - 390) // 2, 40 + D + 14))
bg.convert('RGB').save('Previews/Mock_HUD_1920x1080.jpg', quality=92)
