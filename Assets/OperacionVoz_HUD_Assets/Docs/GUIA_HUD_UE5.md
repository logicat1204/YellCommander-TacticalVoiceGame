# Guía de uso del HUD — Operación Voz (UE5)

## 1. Ajustes de textura al importar
| Grupo | Texturas | Ajustes |
|---|---|---|
| Color UI | todas las `T_MM_*`, `T_Comm_*`, `T_Key_*`, `T_Prompt_*`, `T_Heart_*` | Texture Group **UI**, Compression **UserInterface2D (RGBA8)**, Mip Gen **NoMipmaps**, sRGB **ON**, Never Stream ON |
| Máscaras | `T_MM_Mascara_Circular`, `T_Heart_Mascara` | Compression **Masks** (o Grayscale), sRGB **OFF** |
| Ruta | `T_MM_Ruta_Tile` | Address X **Wrap**; en el Brush de UMG, Tiling **Horizontal** |
| 9-slice | `T_Key_Vacia_9S` | Draw As **Box**, Margin 0.25 |

Los iconos blancos (columna *Tinte = Sí* en `Datos/DT_HUD_Texturas.csv`) se colorean con `Color and Opacity`.

## 2. Minimapa (círculo, mapa rotante)
Capas de abajo a arriba, todas 512×512 (escala el widget completo, p. ej. 300–400 px):
1. `T_MM_Fondo_Circular`
2. Mapa: **Image** con un material UI que muestrea `Terrain/T_Minimapa_ValleAlfa.png` (del paquete P0) y usa `T_MM_Mascara_Circular` como Opacity Mask.
3. Ruta (`T_MM_Ruta_Tile` / `Flecha` / `Nodo` / `Destino`), estructuras, soldados, médicos.
4. `T_MM_Cono_Vision` (teñido azul, α≈0.6) y `T_MM_Jugador` (siempre centrados).
5. `T_MM_Brujula_Rotante` (rotar −Yaw) y encima `T_MM_Marco_Circular` (fijo).

**Material del mapa** (parámetros): `PlayerUV = (X, Y) / 25200` (el mapa mide 252 m = 25 200 uu, origen en la esquina del Landscape), `ZoomUV = RadioVisión_uu / 25200`, `Yaw`.
`UV = PlayerUV + Rotar((UVpantalla − 0.5) · 2 · ZoomUV, Yaw)`; en esta convención la imagen X = mundo X e imagen Y = mundo Y.

**Posición de cada icono** (Canvas Panel, anclaje centro): con `rel = PosMundo − PosJugador`,
`fwd = (cos Yaw, sin Yaw)`, `right = (−sin Yaw, cos Yaw)`:
`pantalla = ( dot(rel,right), −dot(rel,fwd) ) · (RadioPx / RadioVisión_uu)`.
Si `|pantalla| > RadioPx − margen`, recorta al borde (o usa `T_MM_Indicador_Borde`). Visión inicial sugerida: 110 m ≈ 11 000 uu.

### Qué se ve (y qué no)
* Solo el jugador, sus tropas (Alpha, Bravo, médicos), ruta y estructuras.
* **Ningún enemigo móvil**: no repliques posiciones enemigas al cliente del minimapa.
* `T_MM_Estructura_BaseEnemiga` es una **estructura fija** (la pediste en la lista). Si prefieres cero información enemiga, simplemente no la instancies.

Posiciones de estructuras: `Datos/DT_HUD_Minimapa_Estructuras.csv` (coinciden con `DT_Zonas`: base aliada = Trinchera, base enemiga = BunkerEste).

## 3. Modo de comunicación
Dos insignias de 256 px, se muestran de forma excluyente:
* `T_Comm_Modo_Walkie` (ámbar, radio) · `T_Comm_Modo_Habla` (azul, boca + ondas de voz).
* Animación sugerida al pulsar **R**: escala 0.85→1.0 con `T_Comm_Icono_Cambio` rotando 180° y fundido cruzado de 0.15 s.
* Los glifos blancos sueltos (`T_Comm_Glifo_*`) sirven si quieres otro fondo o color.

## 4. Teclas en pantalla
`T_Prompt_R_CambiarModo` es el prompt listo. Para el resto de acciones usa `T_Key_*` (R, V, M, E, F, Tab, Esc, Shift, Espacio, Enter) + un TextBlock UMG con la etiqueta (así se localiza). Variantes de R: `Pressed` (pulsada) y `Resaltada` (borde azul, p. ej. tutorial). La asignación de teclas distinta de R es solo una propuesta; cámbiala en tu esquema de controles.

## 5. Salud del comandante (corazón)
| Estado | Textura | Rango propuesto | Latido |
|---|---|---|---|
| Sano | `T_Heart_Sano` | > 60 % | — |
| Herido | `T_Heart_Herido` | 25–60 % | 0.8 Hz |
| A punto de morir | `T_Heart_Critico` | < 25 % | 1.6 Hz |

Cada estado cambia de **forma** además de color (grieta + vendaje / corazón partido + gota), así que se distingue también con daltonismo. Usa histéresis de ~3 % para evitar parpadeo entre estados. Para el latido: `T_Heart_Pulso_Glow` teñido de rojo detrás del corazón, escala 1.0→1.15.

## 6. Licencias
Todo es original, generado por código (`Fuente_Generadores/`). El texto horneado en teclas usa DejaVu Sans Bold (licencia Bitstream Vera/DejaVu, uso libre; ver `UI/Fonts/LICENCIA_DejaVu.txt` del paquete P0).
