# Guía Mixamo → UE5

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
