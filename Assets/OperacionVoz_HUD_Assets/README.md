# Operación Voz — Assets HUD del jugador (UE5)

Contenido (44 texturas PNG con alfa, estilo coherente con el paquete P0):

| Carpeta | Qué hay |
|---|---|
| `Minimapa/Iconos` | jugador, cono de visión, soldados Alpha/Bravo, médico, estructuras (flanco izq., flanco der., base aliada, base enemiga), indicador de borde |
| `Minimapa/Rutas` | tile de ruta, chevron, nodo, destino |
| `Minimapa/Marco` | marco circular, brújula N-E-S-O, máscara, fondo |
| `Comunicacion` | modo Walkie y modo Habla (insignias + glifos sueltos), icono de cambio |
| `Controles` | teclas R, V, M, E, F, Tab, Esc, Shift, Espacio, Enter, R pulsada/resaltada, tecla vacía 9-slice, prompt «[R] CAMBIAR MODO» |
| `Salud` | corazón Sano / Herido / Crítico + fondo, contorno, glow, máscara |
| `Datos` | `DT_HUD_Texturas.csv` (uso y tinte de cada textura), `DT_HUD_Salud.csv`, `DT_HUD_Minimapa_Estructuras.csv` |
| `Docs` | `GUIA_HUD_UE5.md`: ajustes de importación, material del minimapa, fórmulas, umbrales |
| `Previews` | `Mock_HUD_1920x1080.jpg`: composición de prueba con los propios assets |
| `Fuente_Generadores` | scripts Python que los generan |

Empieza por `Docs/GUIA_HUD_UE5.md`. El minimapa usa `Terrain/T_Minimapa_ValleAlfa.png` del paquete P0.
