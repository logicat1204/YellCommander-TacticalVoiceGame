# Texturas de props: atlas de paleta + ORM + emisiva + pantallas del terminal. Uso: gen_props_tex.py <out_textures_dir>
import sys, os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import hexc
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
PC = [('olive', '#5A6347', .75, .15), ('olive_dark', '#3F4733', .8, .1), ('tan', '#9B8A66', .85, 0), ('metal_dark', '#3A3D40', .5, .8),
      ('metal_light', '#8A8F94', .35, .9), ('rubber', '#1A1A1A', .9, 0), ('led_green', '#2BD968', .3, 0), ('led_red', '#E5322B', .3, 0),
      ('led_amber', '#F0A81E', .3, 0), ('stencil_yellow', '#D9B21E', .7, 0), ('stencil_white', '#E8E8E0', .7, 0), ('rust', '#7A4B2E', .9, .3),
      ('wood', '#6B4A2C', .8, 0), ('canvas', '#6E7355', .95, 0), ('canvas_dark', '#545A41', .95, 0), ('black', '#101010', .6, 0),
      ('screen_dark', '#0B1A12', .1, 0), ('key_gray', '#4A4D50', .6, 0), ('copper', '#B06C3A', .4, .9), ('red', '#8C2A22', .6, .2),
      ('glass', '#16313F', .05, 0)]
bc = Image.new('RGB', (512, 512), (0, 0, 0)); orm = Image.new('RGB', (512, 512), (255, 255, 0)); em = Image.new('RGB', (512, 512), (0, 0, 0))
for i, (n, h, r, m) in enumerate(PC):
    c, rw = i % 8, i // 8; box = (c * 64, rw * 64, c * 64 + 64, rw * 64 + 64)
    bc.paste(hexc(h), box); orm.paste((255, int(r * 255), int(m * 255)), box)
    if n.startswith('led_'):
        em.paste(hexc(h), box)
bc.save(OUT + '/T_Props_BC.png'); orm.save(OUT + '/T_Props_ORM.png'); em.save(OUT + '/T_Props_E.png')
open(OUT + '/T_Props_Celdas.txt', 'w').write('\n'.join(f'{i}\t{c[0]}' for i, c in enumerate(PC)))

F = '/usr/share/fonts/truetype/'
def font(p, s): return ImageFont.truetype(os.path.expanduser('~/.fonts/') + p, s)

def screen(name, accent, status, active=True):
    W, H = 1024, 640
    im = Image.new('RGB', (W, H), (6, 14, 10)); d = ImageDraw.Draw(im)
    if not active:
        for y in range(H):
            v = int(10 + 8 * (1 - y / H)); d.line([(0, y), (W, y)], fill=(v, v + 4, v + 2))
        d.polygon([(0, 0), (W * .45, 0), (0, H * .5)], fill=(22, 28, 26)); im.save(f'{OUT}/{name}.png'); return
    g = tuple(int(c * .25) for c in accent)
    for x in range(0, W, 32): d.line([(x, 0), (x, H)], fill=(10, 30, 20))
    for y in range(0, H, 32): d.line([(0, y), (W, y)], fill=(10, 30, 20))
    d.rectangle([0, 0, W, 70], fill=g); d.text((28, 35), 'TERMINAL DE REFUERZOS', font=font('Oswald-Bold.ttf', 40), fill=accent, anchor='lm')
    d.text((W - 28, 35), status, font=font('ShareTechMono-Regular.ttf', 28), fill=accent, anchor='rm')
    cx, cy = 250, 345                                   # radar
    for r in (60, 120, 180): d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=accent, width=3)
    d.line([(cx - 190, cy), (cx + 190, cy)], fill=g, width=2); d.line([(cx, cy - 190), (cx, cy + 190)], fill=g, width=2)
    rng = random.Random(5)
    for k in range(7):
        a = rng.uniform(0, 6.28); r = rng.uniform(30, 170); x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(47, 123, 255))
    d.polygon([(cx, cy), (cx + 180 * math.cos(-1.0), cy + 180 * math.sin(-1.0)), (cx + 180 * math.cos(-0.55), cy + 180 * math.sin(-0.55))], fill=g)
    d.polygon([(cx - 10, cy + 10), (cx + 10, cy + 10), (cx, cy - 12)], fill=(255, 255, 255))
    for i, t in enumerate(('1  REFUERZO · COMBATE', '2  REFUERZO · MÉDICO', 'E  CONFIRMAR LLAMADA')):
        y0 = 120 + i * 105; col = accent if i < 2 else (255, 190, 40)
        d.rounded_rectangle([510, y0, 990, y0 + 80], 10, outline=col, width=4, fill=(10, 36, 24) if i < 2 else (50, 36, 8))
        d.text((540, y0 + 40), t, font=font('Oswald-Bold.ttf', 36), fill=col, anchor='lm')
    d.text((510, 470), 'LLEGADA ESTIMADA', font=font('Oswald-Medium.ttf', 28), fill=accent, anchor='lm')
    d.text((990, 470), '00:45', font=font('ShareTechMono-Regular.ttf', 44), fill=(255, 255, 255), anchor='rm')
    d.rectangle([510, 505, 990, 530], outline=accent, width=3); d.rectangle([514, 509, 740, 526], fill=accent)
    d.text((28, 610), 'ENLACE SEGURO  ·  CANAL 7  ·  SEÑAL 4/5', font=font('ShareTechMono-Regular.ttf', 24), fill=accent, anchor='lm')
    for y in range(0, H, 4): d.line([(0, y), (W, y)], fill=(0, 0, 0))  # scanlines
    im = Image.blend(im, im.filter(ImageFilter.GaussianBlur(1.2)), .35)
    im.save(f'{OUT}/{name}.png')
screen('T_Terminal_Pantalla_Activa', (60, 230, 130), 'EN LÍNEA')
screen('T_Terminal_Pantalla_Alerta', (235, 70, 55), 'SIN ENLACE')
screen('T_Terminal_Pantalla_Apagada', (0, 0, 0), '', False)
print('tex ok')
