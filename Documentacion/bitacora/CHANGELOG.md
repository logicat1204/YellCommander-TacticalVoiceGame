# Bitácora de implementación

## 20 de noviembre de 2026

- Fase 0. Inventario de UE 5.8, referencias, assets y seed. Definición del contrato `command-v1.schema.json`.
- Fases 1 y 2. Corpus por familias, BiGRU multitarea, adaptador Qwen, servicio local, Whisper Base, Push-to-Talk y evaluación en `AI NLP/yell`.
- Fases 3 a 5. Valle Alfa, comandante, radio, validación, NavMesh, HUD, unidades, enfermería, refuerzos y rival en `WarCommanderDemo/Source/WarCommanderDemo/Yell`.
- Fase 6. Validación del esquema, tests unitarios, escenario de automatización Unreal y evaluación de ambos modelos sobre una prueba compartida.
- Diagnóstico. Se acotó la gramática de Qwen tras encontrar combinaciones JSON incompatibles. La partida exige acuerdo entre modelos para las propuestas de orden y arenga de B. Se guardaron las evaluaciones individuales y la simulación de esa política.
- Validación final. Se sustituyó la síntesis experimental de Unreal por tres réplicas en español tras reproducir un fallo con el audio desactivado. Se verificaron la compilación, el recorrido WAV a Alfa, una orden textual de B a Bravo y la captura de rendimiento D3D12.

Consulta `IMPLEMENTATION_STATUS.md` y `../results/TEST_RESULTS.md` para ver el alcance verificado.

### Revisión de la Fase 1

- Se archivó el prompt íntegro en `PROYECTO_MAESTRO.md` y se añadió un plan que distingue las fases y sus evidencias.
- Se amplió el corpus, se congelaron dos pruebas textuales y se ajustó DistilBERT en español mediante PyTorch. A y B conservaron sus roles originales.
- Se añadieron consola A/B/C, cuaderno ejecutable, exportación del dataset, resultados por frase y pruebas.
- Se revisó la captura de la sesión del usuario. WASAPI abre el dispositivo y las grabaciones fallidas se rechazan antes de STT. Se documentó la hipótesis de discontinuidad y la validación física de Fase 2.

### Revisión de la Fase 2

- El sondeo físico confirmó la marca de discontinuidad en el primer paquete. La captura conserva ese audio y cancela ante cortes posteriores o pérdida de foco.
- F3 muestra los datos de captura. Los registros vinculan el diagnóstico, la transcripción y el resultado por identificador de solicitud.
- Whisper distingue falta de señal, ruido sin voz y transcripción incierta. `-Transfer` habilita C en la partida que abre el lanzador.
- Se guardaron los resultados de STT y los registros de radio y proximidad. [Informe de voz](../results/FASE_2_VOZ.md).
