# Plan y validación por fases

La especificación íntegra se conserva en [Proyecto maestro](../PROYECTO_MAESTRO.md). Cada revisión parte del apartado 24 y contrasta los requisitos funcionales de la fase con las pruebas del apartado 22 y los criterios de aceptación del apartado 27.

| Fase | Entregable del prompt | Estado de revisión |
|---|---|---|
| 0 | Auditoría, catálogo, esquema y arquitectura | Existe con evidencia en la auditoría y en el contrato v1 |
| 1 | Prototipo NLP textual con dos enfoques y evaluación inicial | Revisada. A se conserva como modelo desde cero. B sigue siendo Qwen cuantizado. C añade el ajuste fino supervisado del apartado 11 |
| 2 | Captura física, STT, Push-to-Talk, canal y confirmación | Revisión actual. Dispositivo verificado en Windows y recorrido de audio validado con WAV sintético. Queda una prueba interactiva con voz humana |
| 3 | Orden que cambia el comportamiento en el mapa UE5 | Existe un prototipo previo. La revisión por fases vuelve a este escenario después de la voz |
| 4 | Partida con médicos, moral, refuerzos y fin de batalla | Existe una versión básica y falta revisar los casos específicos del prompt |
| 5 | Rival algorítmico con memoria, reportes y tácticas | Existe una versión básica y falta validar el descarte de reportes y los cambios de táctica |
| 6 | Evaluación científica reproducible del sistema completo | Hay mediciones textuales y un perfil preliminar de Unreal. Voz real y mediciones repetidas siguen pendientes |
| 7 | Arte, interfaz, optimización y defensa académica | Pendiente |

## Criterios de la Fase 1

- Auditar la semilla, ampliar el español coloquial y congelar las pruebas por familias.
- Ejecutar A y B en la consola con el contrato compartido. Implementar C como experimento complementario de transferencia, con PyTorch y cuaderno.
- Guardar pesos, tokenizador, hiperparámetros, curva por época y predicciones por frase.
- Ejecutar pruebas de órdenes válidas, negación, ambigüedad, charla, arenga y entradas fuera del dominio. Comparar con exactamente las mismas frases.
- Registrar la precisión y los errores para decidir en otra fase qué modelo conviene usar en partida.

[Auditoría inicial](../datasets/AUDITORIA.md) · [Informe Fase 1](../experiments/FASE_1_NLP.md) · [Diagnóstico de V](../results/DIAGNOSTICO_MICROFONO.md)

## Criterios de la Fase 2

- Verificar la entrada física y diagnosticar el inicio y los cortes de captura.
- Probar STT, orden interpretada, alcance del canal y confirmación en Valle Alfa.
- Registrar tiempos de STT, NLP y respuesta del juego por solicitud.
- Probar silencio, ruido, transcripciones inciertas y negaciones. Validar el recorrido interactivo con voz humana en juego y en Play In Editor.

[Informe Fase 2](../results/FASE_2_VOZ.md).
