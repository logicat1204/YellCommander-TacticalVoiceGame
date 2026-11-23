# Operación Voz — Assets Prioridad 0 para Unreal Engine 5

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
| `Textures/Tileable/` | 6 materiales PBR sin costuras (concreto, tierra, saco, roca, metal, pasto): BaseColor, Normal DirectX y ORM | materiales |
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
| `SK_Soldado_Aliado` | Soldado | 6.288 | 1.88 × 0.49 × 1.8 |
| `SK_Soldado_Medico` | Soldado | 6.208 | 1.88 × 0.51 × 1.8 |
| `SK_Soldado_Enemigo` | Soldado | 6.152 | 1.88 × 0.48 × 1.8 |
| `SM_Rifle_Asalto` | Arma | 680 | 0.05 × 0.92 × 0.27 |
| `SM_Pistola` | Arma | 196 | 0.03 × 0.23 × 0.17 |
| `SM_Bunker_Enemigo_Intacto` | Bunker | 884 | 10.15 × 7.22 × 6.0 |
| `SM_Bunker_Enemigo_Danado` | Bunker | 1.796 | 10.15 × 7.95 × 6.0 |
| `SM_Bunker_Enemigo_Destruido` | Bunker | 2.468 | 9.52 × 8.31 × 3.16 |
| `SM_Trinchera_Recta_4m` | Trinchera | 80 | 4.0 × 4.8 × 1.72 |
| `SM_Trinchera_Esquina` | Trinchera | 60 | 4.8 × 4.8 × 1.72 |
| `SM_Trinchera_Final` | Trinchera | 80 | 4.0 × 4.8 × 1.72 |
| `SM_Saco_Arena` | Sacos | 120 | 0.49 × 0.31 × 0.18 |
| `SM_Sacos_Muro_2m_Bajo` | Sacos | 1.320 | 1.99 × 0.31 × 0.49 |
| `SM_Sacos_Muro_2m_Alto` | Sacos | 2.160 | 1.99 × 0.31 × 0.79 |
| `SM_Sacos_Esquina_Bajo` | Sacos | 2.400 | 1.99 × 2.07 × 0.49 |
| `SM_Rocas_PuertaNorte_01` | Roca | 1.280 | 5.54 × 5.08 × 4.81 |
| `SM_Rocas_PuertaNorte_02` | Roca | 1.280 | 5.23 × 6.87 × 3.2 |
| `SM_Rocas_PuertaNorte_03` | Roca | 1.280 | 4.23 × 3.36 × 2.32 |
| `SM_Rocas_PuertaNorte_Muro` | Roca | 1.280 | 13.63 × 4.08 × 3.6 |

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
- Comprobación de UVs, materiales y tamaños; colisiones `UCX_` convexas en cada malla estática salvo las armas (objetos que se sostienen: añade su colisión en UE solo si la necesitas).
- Reimportación del FBX de Mixamo en Blender para comprobar escala (1,80 m) y orientación.
- Pendiente de tu lado: importar en UE5 y subir a Mixamo. Si el personaje o el arma quedan rotados, ver la nota de orientación en las guías.

## Primeros pasos

1. `Docs/GUIA_Importacion_UE5.md` — terreno, texturas, mallas, datos, UI y VFX en el orden recomendado.
2. `Docs/GUIA_Mixamo.md` — subir los soldados, descargar animaciones e importarlas en UE5.
