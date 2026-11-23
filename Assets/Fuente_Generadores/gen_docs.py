# -*- coding: utf-8 -*-
import sys, os, csv
R = sys.argv[1]


def w(rel, txt):
    p = os.path.join(R, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(txt)


stats = list(csv.reader(open(os.path.join(R, 'Docs', 'Estadisticas_Modelos.csv'), encoding='utf-8')))[1:]
tabla = '\n'.join(f'| `{r[0]}` | {r[1]} | {int(r[2]):,} | {r[4]} × {r[5]} × {r[6]} |'.replace(',', '.') for r in stats)

w('README.md', f'''# Operación Voz — Assets Prioridad 0 para Unreal Engine 5

Paquete generado para el demo «Operación Voz» (control de escuadrones por voz con NLP). Contiene los **assets P0** de la
tabla del guion técnico, listos para importar en **UE5** y, en el caso de los soldados, listos para subir a **Mixamo**
y recibir animaciones gratuitas.

> **Qué es y qué no es.** Todo se generó de forma procedural (Blender 5.0 headless + Python). El estilo es **low-poly estilizado**,
> pensado para una cámara táctica cenital. No hay material de terceros salvo la fuente DejaVu (licencia libre incluida).
> **No se pudo probar** dentro de UE5 ni subiendo a Mixamo desde aquí: la sección «Verificación» dice qué sí se comprobó.

## Estructura

| Carpeta | Contenido | IDs del guion |
|---|---|---|
| `Models/Mixamo_Upload/` | Soldados en **T-pose** (FBX + textura) y un `.zip` por personaje para subir directo a Mixamo | A3D-01, A3D-02 |
| `Models/UE5_StaticMeshes/` | FBX para UE5 con colisión `UCX_`: armas, búnker (3 estados), trinchera modular, sacos de arena, rocas del paso norte | A3D-03, 04, 06, 09 |
| `Terrain/` | Heightmap 16-bit 1009×1009, 3 capas de pintura, minimapa y referencia de zonas | A3D-05, UI-05 |
| `Textures/Tileable/` | 5 materiales PBR sin costuras (BaseColor, Normal DirectX, ORM) + pasto | materiales |
| `Textures/Soldado/` `Textures/Armas/` | Atlas de paleta 512² por escuadrón (Alpha, Bravo, Médico, Enemigo) + ORM | A3D-01/02/09 |
| `UI/` | Kit HUD (9-slice), 17 íconos, indicador de micrófono, marcadores, decals, fuentes | UI-01…05, UI-07, VFX-03 |
| `VFX/Textures/` | Flipbooks 4×4 (fogonazo, humo, polvo), chispas, círculo suave | VFX-01 (sprites) |
| `Config/` `Data/` | Gameplay Tags, Data Tables (CSV) + `OvDataRows.h`, JSON Schema, dataset NLP semilla | DAT-01…06 |
| `Docs/` | Guías de Mixamo e importación a UE5, estadísticas, licencias | — |
| `Previews/` | Renders de verificación | — |
| `Fuente_Generadores/` | Scripts que generan todo (para ajustar y regenerar) | — |

## Modelos (triángulos y tamaño en metros, ancho × largo × alto)

| Asset | Grupo | Triángulos | Tamaño (m) |
|---|---|---|---|
{tabla}

Los soldados miden 1,80 m; con los brazos en T abarcan 1,88 m. Unidades: **1 unidad de Blender = 1 m = 100 uu** en UE5.

## Lo que NO incluye (y por qué)

- **Animaciones (ANI-01…05):** las descargas de Mixamo requieren iniciar sesión con tu cuenta Adobe, así que no se pueden bajar desde aquí.
  `Docs/GUIA_Mixamo.md` lista qué descargar y con qué ajustes.
- **Archivos `.uasset`** (materiales, Niagara, Blueprints, Animation Blueprints, Behavior Trees): solo se crean dentro del editor de UE.
  Se entregan las texturas/sprites y la guía para armarlos; los materiales se arman con los mapas incluidos.
- **Audio:** no estaba en la lista P0 de assets; queda para el paso de sonidos.
- **Dataset NLP:** es una **semilla** de 1.510 ejemplos por plantillas (intención + etiquetas BIO). Sirve para arrancar, no para medir rendimiento final.

## Verificación realizada

- Renders con Cycles de todos los modelos (carpeta `Previews/`) para revisar forma, proporciones y paletas.
- Comprobación de UVs, materiales y tamaños; colisiones `UCX_` convexas generadas para cada malla estática.
- Reimportación del FBX de Mixamo en Blender para comprobar escala (1,80 m) y orientación.
- Pendiente de tu lado: importar en UE5 y subir a Mixamo. Si el personaje o el arma quedan rotados, ver la nota de orientación en las guías.

## Primeros pasos

1. `Docs/GUIA_Importacion_UE5.md` — terreno, texturas, mallas, datos, UI y VFX en el orden recomendado.
2. `Docs/GUIA_Mixamo.md` — subir los soldados, descargar animaciones e importarlas en UE5.
''')

w('Docs/GUIA_Mixamo.md', '''# Guía Mixamo → UE5

Mixamo es gratuito con una cuenta Adobe (mixamo.com). Revisa los términos vigentes de Adobe antes de publicar el juego.

## 1. Subir los personajes
Archivos listos: `Models/Mixamo_Upload/SK_Soldado_Aliado_Mixamo.zip`, `SK_Soldado_Medico_Mixamo.zip`, `SK_Soldado_Enemigo_Mixamo.zip`.
Cada zip contiene el FBX y su textura. En Mixamo: **Upload Character** → seleccionar el `.zip`.

Los modelos cumplen lo que pide el auto-rigger: humanoide en **T-pose**, brazos horizontales, piernas ligeramente separadas,
una sola malla por personaje, un solo material, 1,80 m de alto, mirando al frente, con dedos separados.

## 2. Auto-Rigger
1. Colocar los marcadores: barbilla, muñecas, codos, rodillas e ingle.
2. Si Mixamo ofrece elegir la complejidad del esqueleto, usar el estándar (con dedos): las manos ya tienen cuatro dedos y pulgar.
3. Confirmar y revisar la vista previa con una animación.

Repetir con los tres soldados. Todos usan el mismo rig estándar de Mixamo, así que **las animaciones se descargan una sola vez**
y sirven para los tres.

## 3. Animaciones P0 (ANI-01 … ANI-05)
Los nombres exactos pueden cambiar; busca por palabras clave:

| ID guion | Qué buscar en Mixamo |
|---|---|
| ANI-01 Idle (de pie / agachado / tumbado) | «rifle idle», «crouch idle», «prone idle» |
| ANI-02 Locomoción | «rifle walk», «rifle run», «crouch walk», «crawl» |
| ANI-03 Disparar / recargar | «firing rifle», «shooting», «reload» |
| ANI-04 Daño y muerte | «hit reaction», «death» (2 variantes) |
| ANI-05 Curar | «medic», «kneel», «treating», «crouch interact» |

Ajustes de descarga:
- Primera descarga (por cada personaje): **Format FBX for Unreal (.fbx)**, **Skin: With Skin**, 30 fps.
- Resto de animaciones: **Without Skin**, 30 fps, sin reducción de keyframes.
- Marcar **In Place** en caminar/correr/agachado: el movimiento lo da el NavMesh, no la animación.

## 4. Importar a UE5
1. Importar el FBX «With Skin» del soldado aliado → se crea la malla esquelética, su `Skeleton` y su `Physics Asset`.
2. Importar los otros dos soldados y, en el diálogo, elegir **ese mismo Skeleton** (comparten jerarquía).
3. Importar las animaciones «Without Skin» eligiendo ese Skeleton.
4. Si el personaje aparece 100× más grande o pequeño: ajustar **Import Uniform Scale** (0,01 o 100).
5. Si queda girado: **Import Rotation** (Yaw ±90° o 180°).
6. Los huesos pueden verse como `mixamorig_RightHand` (UE cambia los dos puntos por guion bajo).

## 5. Texturas y materiales
Cada personaje usa un atlas de paleta 512² (`Textures/Soldado/T_Soldado_<Variante>_BC.png`) más `T_Soldado_ORM.png` compartido.
Crea **un material maestro** `M_Soldado` y **3-4 Material Instances** que solo cambian el BaseColor
(Alpha = azul, Bravo = turquesa, Médico = blanco, Enemigo = rojo). Filtro de textura «Nearest» o mips por defecto, ambos sirven.

## 6. Armas
Añade un socket en la mano derecha del esqueleto (por ejemplo `mixamorig_RightHand`) y adjunta `SM_Rifle_Asalto`.
El origen del rifle está en la empuñadura y el cañón apunta hacia adelante (+X en UE).

## 7. Esqueleto para el combate cenital
Con cámara cenital basta con: idle, caminar, correr, agachado (idle y caminar), disparar, recargar, daño y 2 muertes.
Más adelante puedes añadir animaciones de gesto (señal de mano, hablar por radio) del mismo catálogo.
''')

w('Docs/GUIA_Importacion_UE5.md', '''# Guía de importación a UE5 (orden recomendado)

Versión sugerida: UE 5.4 o posterior. Unidades: 1 m = 100 uu.

## 1. Datos y Gameplay Tags
1. Copiar `Config/DefaultGameplayTags.ini` a `<Proyecto>/Config/` (o fusionarlo si ya existe).
2. Copiar `Data/OvDataRows.h` a `Source/<Modulo>/Data/` y compilar.
3. Importar cada CSV como **DataTable** eligiendo la estructura: `DT_Zonas`→`FZonaRow`, `DT_Comandos`→`FComandoRow`,
   `DT_Unidades`→`FUnidadRow`, `DT_Oleadas`→`FOleadaRow`, `DT_Replicas`→`FReplicaRow`.
4. `Data/ComandoTactico.schema.json` es el contrato del payload del NLP.

## 2. Texturas
| Tipo | Archivos | Ajustes en UE |
|---|---|---|
| Color | `*_BC.png` | sRGB activado |
| Normal | `*_N.png` | Compression «Normalmap». Convención **DirectX** (la de Unreal): no invertir el verde |
| ORM | `*_ORM.png` | sRGB **desactivado**, Compression «Masks». R = oclusión, G = rugosidad, B = metálico |
| Paletas | `Textures/Soldado`, `Textures/Armas` | las celdas son planas; con mips normales funciona |
| UI | `UI/**` | Texture Group «UI», sin mips |

Las mallas ya traen UV en «repeticiones de textura» (1 UV = 1 tile), así que **no hace falta escalar UV en el material**.
Tamaño real de un tile: concreto 2,0 m · tierra 2,0 m · roca 2,2 m · saco 0,8 m · metal 1,0 m.

## 3. Materiales (se crean en el editor)
Material base PBR: `BC → Base Color`, `ORM.R → Ambient Occlusion`, `ORM.G → Roughness`, `ORM.B → Metallic`, `N → Normal`.
Crea `M_Concreto`, `M_Metal`, `M_Tierra`, `M_Saco`, `M_Roca` (los FBX los nombran así) y `M_Soldado`, `M_Armas` para las paletas.

## 4. Mallas estáticas
Importar `Models/UE5_StaticMeshes/*.fbx` con: Auto Generate Collision **desactivado** (ya traen `UCX_`),
Generate Lightmap UVs **desactivado** (Lumen), Combine Meshes activado, Import Uniform Scale 1.
Nanite es opcional; conviene para el búnker y las rocas.
Si algún asset queda rotado 90°/180°, ajustar **Import Rotation**.

Pivotes: el búnker, la trinchera y los sacos tienen el origen en el centro del suelo; el rifle y la pistola, en la empuñadura.
Trinchera: piezas modulares de 4 m (`Recta_4m`, `Esquina`, `Final`); la esquina conecta un extremo en -X con otro en +Y.

## 5. Terreno «Valle Alfa»
1. Modo Landscape → **Import from File**.
2. Heightmap: `Terrain/Heightmap_ValleAlfa_1009.png` (16-bit). También está el `.r16` crudo.
3. Resolución 1009×1009. Sección 63×63 quads, 1 sección por componente (16×16 componentes).
4. **Escala X = 25, Y = 25, Z = 10**; ubicación (0, 0, 0). Resultado: 252 m × 252 m con alturas entre -6 y +17 m.
5. Capas: crear `Pasto`, `Tierra`, `Roca` y asignar `Terrain/Layers/L_Pasto.png`, `L_Tierra.png`, `L_Roca.png`.
6. Material de terreno con **Landscape Layer Blend** usando las texturas `Pasto`, `Tierra` y `Roca`.
7. Las coordenadas de `DT_Zonas` están en uu relativas a esa esquina. La imagen `Terrain/Referencia_Zonas_ValleAlfa.png`
   muestra dónde está cada zona (arriba = norte). `Terrain/T_Minimapa_ValleAlfa.png` es el minimapa listo.

El terreno es un mapa de 9 zonas: trinchera (oeste), puerta norte (paso entre rocas), flancos, puente (paso en el barranco),
colina con torre, búnker este (meseta) y punto de extracción (sur). Faltan los modelos de puente y torre de vigía (no eran P0).

## 6. UI (UMG)
| Archivo | Uso | Margen 9-slice |
|---|---|---|
| `T_UI_Panel_9S.png` (128²) | paneles | 0,16 |
| `T_UI_Panel_Ligero_9S.png` | paneles ligeros | 0,16 |
| `T_UI_Boton_*_9S.png` (256×64) | botones: Normal, Hover, Pressed, Disabled | 0,05 H / 0,19 V |
| `T_UI_Barra_Marco` + `Relleno` | barras de vida (tintar el relleno) | — |
| `Icons/T_Icon_*.png` | íconos blancos: tintar en el widget | — |
| `Mic/*` | `WBP_MicIndicator`: anillo, disco, resplandor, barras de onda | — |
| `Markers/*` | flecha, objetivo, ping, aliado (círculo), enemigo (rombo), decals | — |

Paleta: azul técnico `#5EA0FF`, rojo `#D23A2F`, ámbar `#D99A1E`, verde `#2E7D4F`, fondo `#0A1A34`.
Fuentes: `UI/Fonts/` (DejaVu Sans, Bold y Mono; licencia incluida). Importar como Font Face.

`T_Decal_AnilloDestino.png` y `T_Decal_Seleccion.png`: materiales de tipo **Deferred Decal**, Translucent, con el color como parámetro.

## 7. VFX (Niagara)
Hay flipbooks de **4×4 cuadros** listos para el módulo SubUV:
- `T_VFX_Fogonazo_Flipbook4x4` → Sprite Renderer aditivo, vida 0,08 s.
- `T_VFX_Humo_Flipbook4x4` y `T_VFX_Polvo_Flipbook4x4` → translúcido, vida 0,6–1,2 s.
- `T_VFX_Chispas` y `T_VFX_CirculoSuave` → impactos y destellos de curación/daño.

## 8. Escena de prueba mínima
Landscape → un `SM_Bunker_Enemigo_Intacto` en `bunker_este` → piezas de trinchera y sacos en `trinchera` →
rocas en `puerta_norte` → un soldado aliado con animación idle de Mixamo.
''')

w('Docs/Licencias.md', '''# Licencias

- **Modelos, texturas, terreno, íconos, UI, sprites VFX, datos y scripts:** creados específicamente para este proyecto con
  generación procedural. No contienen material de terceros.
- **Fuentes `UI/Fonts/` (DejaVu):** licencia libre de Bitstream Vera / DejaVu. El texto de licencia se incluye junto a las fuentes.
- **Animaciones de Mixamo:** no se incluyen. Se descargan con tu cuenta Adobe y se rigen por los términos de Mixamo vigentes.
- **Herramientas usadas para generar:** Blender (`bpy` 5.0.1), Python, NumPy, SciPy y Pillow.
''')
print('docs OK')
