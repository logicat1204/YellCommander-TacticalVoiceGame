# -*- coding: utf-8 -*-
"""Paletas compartidas entre el generador de texturas y el de modelos."""

GRID = 8          # celdas por lado
CELL_PX = 64      # px por celda  -> atlas 512x512

CELLS = ['skin', 'skin_dark', 'uniform', 'uniform_dark', 'vest', 'plate', 'helmet', 'strap', 'boots', 'glove',
         'belt', 'pouch', 'pack', 'lens', 'frame', 'accent', 'cross_white', 'cross_red', 'metal', 'cloth',
         'sole', 'holster', 'mask', 'sand']
CI = {n: i for i, n in enumerate(CELLS)}


def cell_uv(idx, grid=GRID):
    """UV (u, v) del centro de la celda idx (origen UV abajo-izquierda)."""
    c, r = idx % grid, idx // grid
    return ((c + 0.5) / grid, 1.0 - (r + 0.5) / grid)


def hexc(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


_BASE = dict(skin='#C99A7A', skin_dark='#A47A5E', uniform='#59634A', uniform_dark='#434B38', vest='#3C4234',
             plate='#2B2E2A', helmet='#4E5A45', strap='#1F211E', boots='#3A2E25', glove='#2A2B28', belt='#2E3029',
             pouch='#4A4F3F', pack='#454B3A', lens='#1B2530', frame='#202220', accent='#2F7BFF',
             cross_white='#EDEDED', cross_red='#C4302B', metal='#6C7076', cloth='#7A7A62', sole='#161616',
             holster='#2D2A25', mask='#1E1F1D', sand='#B9A67A')

PALETTES = {
    'Alpha': dict(_BASE),
    'Bravo': dict(_BASE, uniform='#5B5F52', uniform_dark='#464A3F', vest='#363B33', helmet='#555B4C',
                  pack='#3E4338', accent='#19C7C7'),
    'Medico': dict(_BASE, vest='#6E7468', pack='#D8D8D2', helmet='#5A6650', accent='#F2F2F2',
                   pouch='#8A9082', cloth='#C9C9C0'),
    'Enemigo': dict(_BASE, skin='#B98B6C', uniform='#6B5E48', uniform_dark='#54483A', vest='#3A3330',
                    plate='#25201E', helmet='#4A4A47', pouch='#4D3F36', pack='#3D352E', boots='#2B231D',
                    accent='#D23A2F', mask='#161514', cloth='#5C5042', glove='#1E1C1A', belt='#2A2522'),
}

# (rugosidad, metalico) por celda
ORM_VALS = dict(skin=(0.62, 0), skin_dark=(0.66, 0), uniform=(0.92, 0), uniform_dark=(0.92, 0), vest=(0.85, 0),
                plate=(0.5, 0.2), helmet=(0.55, 0.05), strap=(0.85, 0), boots=(0.6, 0), glove=(0.7, 0),
                belt=(0.8, 0), pouch=(0.85, 0), pack=(0.88, 0), lens=(0.08, 0), frame=(0.5, 0.1),
                accent=(0.75, 0), cross_white=(0.8, 0), cross_red=(0.8, 0), metal=(0.35, 0.9), cloth=(0.95, 0),
                sole=(0.9, 0), holster=(0.7, 0), mask=(0.95, 0), sand=(0.95, 0))

# ----------------------------------------------------------------------------- armas
WCELLS = ['gunmetal', 'steel', 'poly_black', 'poly_tan', 'lens', 'rubber', 'wood', 'accent_o', 'sight', 'brass']
WCI = {n: i for i, n in enumerate(WCELLS)}
WPAL = dict(gunmetal='#2E3135', steel='#8B9096', poly_black='#1C1D1F', poly_tan='#8C7B5C', lens='#16313F',
            rubber='#121212', wood='#5B3C25', accent_o='#D9731E', sight='#0E0E0E', brass='#B58B3A')
WORM = dict(gunmetal=(0.4, 0.85), steel=(0.3, 0.95), poly_black=(0.65, 0), poly_tan=(0.7, 0), lens=(0.05, 0),
            rubber=(0.9, 0), wood=(0.6, 0), accent_o=(0.6, 0), sight=(0.5, 0.3), brass=(0.35, 0.9))

# ----------------------------------------------------------------------------- mapa
MAP_SIZE_M = 252.0
LAND_N = 1009
ZONES = {   # nombre: (x_m, y_m, radio_m)   origen arriba-izquierda; +X derecha, +Y abajo (vista cenital UE)
    'trinchera': (34, 126, 10), 'puerta_norte': (126, 22, 8), 'flanco_izquierdo': (100, 62, 12),
    'flanco_derecho': (100, 192, 12), 'puente': (126, 126, 10), 'colina': (175, 60, 15),
    'torre_vigia': (178, 58, 4), 'bunker_este': (214, 126, 12), 'punto_extraccion': (126, 232, 12),
}
