# Operación Voz / Yell Commander — Props de ambiente + Terminal de refuerzos (UE5)

| Archivo (`Models/UE5_StaticMeshes/`) | Qué es | Tris | Tamaño m (X×Y×Z) |
|---|---|---|---|
| `SM_Terminal_Refuerzos` | Terminal militar de campaña sobre mesa plegable: teclado, antena, micrófono de mano, luces de estado y botón rojo. Pantalla con material propio (2 slots). **Para llamar refuerzos.** | 1362 | 1.0×0.62×1.53 |
| `SM_Cajas_Municion_Pila` | Pila de 7 cajas de munición | 1204 | 1.24×0.87×0.71 |
| `SM_Barril_Combustible` | Barril de combustible rojo con banda blanca | 480 | 0.59×0.6×0.9 |
| `SM_Mastil_Radio` | Mástil de radio de 6,3 m con 3 tirantes, caja de equipo y luz roja | 568 | 4.24×3.67×6.29 |
| `SM_Tienda_Militar` | Tienda de campaña (solo exterior, no enterable). Puerta hacia +X | 228 | 5.86×4.26×2.21 |
| `SM_Alambrada_4m` | Tramo de alambrada de púas de 4 m | 1320 | 4.12×0.12×1.16 |

Todos: 1 malla, UV 0-1 sin solapes de pivote, colisión convexa `UCX_` incluida (importa con *Auto Generate Collision* desactivado), escala real (1 m = 100 uu), pivote en la base y centro.

## Texturas (`Textures/`)
* `T_Props_BC / ORM / E` — atlas de paleta 512² (celdas de 64 px; listado en `T_Props_Celdas.txt`). ORM: R=AO, G=Rugosidad, B=Metálico. `T_Props_E` es la máscara emisiva (solo los LED).
* `T_Terminal_Pantalla_Activa / Alerta / Apagada` — 1024×640 para el slot `M_Terminal_Pantalla`. Cambia entre ellas con un parámetro de textura en la instancia del material (p. ej. *Alerta* cuando no hay señal).

## Montaje en UE5
1. Importa los FBX (Import Materials: ON; luego reasigna). Crea `M_Props` con BC + ORM (+ emisivo `T_Props_E`, intensidad ~4) y `M_Terminal_Pantalla` (Emissive = textura × 1.5, Base Color negro).
2. Texturas: BC sRGB ON; ORM y E sin sRGB para ORM (E con sRGB ON); *Filter = Nearest* en el atlas evita el sangrado entre celdas.
3. **Terminal:** el frente (pantalla/teclado) mira a +X en UE tras importar. Añade un Blueprint `BP_TerminalRefuerzos` con un componente de interacción (tecla E) cerca del frente, dispara tu evento de "pedir refuerzos" y cambia la pantalla (Activa → Alerta/Apagada). Los textos de la pantalla (1 combate, 2 médico, E confirmar) son orientativos: ajústalos a tu diseño. Si necesitas texto dinámico, usa un Render Target o un widget 3D sobre el plano de pantalla.
4. El mástil tiene su pivote en el pie; los tirantes y estacas salen de la colisión a propósito.

## Qué falta / límites
* No probado dentro de UE5 (sí reimportado en Blender: 1 malla, UV, materiales y UCX correctos).
* Los textos de la pantalla del terminal están horneados en español; las fuentes usadas (Oswald, Share Tech Mono) son OFL.
* Son props estáticos de bajo poligonaje con estética plana (paleta), coherente con el paquete P0; sin desgaste/suciedad.
* Previews en `Previews/`; scripts generadores en `Fuente_Generadores/`.
