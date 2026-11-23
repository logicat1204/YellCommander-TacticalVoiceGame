# Estado del prototipo

La revisión actual se concentra en la Fase 2. Se corrigió el descarte de audio al pulsar V. Se verificaron el dispositivo físico, la transcripción y el recorrido sintético hasta la ejecución en Valle Alfa. El modelo de transferencia C está disponible con `-Transfer` en el lanzador. [Plan por fases](PLAN_POR_FASES.md) · [Fase 1](../experiments/FASE_1_NLP.md) · [Fase 2](../results/FASE_2_VOZ.md).

| Área | Entrega |
|---|---|
| Nivel y mando | Valle Alfa en primera persona, tres rutas con NavMesh, dos bases, terminales, HUD y panel NLP |
| Voz y comunicación | Push-to-Talk con diagnóstico, Whisper Base local con VAD, confirmación y alcance de proximidad |
| NLP | BiGRU entrenada desde cero, ONNX de lote 1, Qwen local con gramática, DistilBERT ajustado, contrato v1 y evaluación por frase |
| Juego | Órdenes a pelotón o soldado, combate simulado, cobertura, médicos, moral, refuerzos, reaparición y fin de partida |
| Rival | Percepción parcial, memoria temporal, reportes demorados de exploración, cinco configuraciones tácticas y tres personalidades |
| Datos | Semilla auditada, 1.723 ejemplos adaptados o ampliados, prueba por familias y comparación de ambos enfoques |

## Trabajo pendiente

- Validar Push-to-Talk en una sesión con voz humana, incluido Play In Editor, y evaluar varios hablantes con voces bolivianas y ruido de juego. La prueba de integración usa WAV sintético.
- Ampliar y equilibrar el corpus humano. La cobertura sobre frases nuevas es baja, en especial cuando se aplica el acuerdo requerido por B en partida.
- Agregar escenarios automatizados específicos para pérdida del explorador antes de su reporte y expiración de la moral en juego.
- Importar los modelos y animaciones preparados en `Assets`. La arena actual es un prototipo geométrico. La navegación tiene cobertura básica y recuperación local. El coste dinámico del NavMesh y la supresión detallada siguen pendientes.
- Medir memoria y rendimiento con una sesión humana más larga y en distintas configuraciones de CPU y GPU. La exportación ONNX se verificó en CPU y permanece fuera del ejecutor de Unreal.

Los resultados y los comandos de reproducción se describen en [la validación técnica](../results/TEST_RESULTS.md) y [la comparación de NLP](../experiments/MODEL_COMPARISON.md).
