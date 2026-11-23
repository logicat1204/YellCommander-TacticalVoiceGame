# Guía de importación a UE5 (orden recomendado)

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
