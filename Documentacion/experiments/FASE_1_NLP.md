# Fase 1 del prototipo NLP textual

Se conservan los dos enfoques del proyecto maestro. A es la BiGRU entrenada desde pesos aleatorios y B es Qwen 1.5B Q4_K_M local con prompting y gramática. C implementa el experimento de transferencia del apartado 11. Es un DistilBERT preentrenado en español, revisión `1db4091`, ajustado en PyTorch. Las tres salidas pasan por el contrato `command-v1.schema.json`. [Modelo base de Geotrend](https://huggingface.co/Geotrend/distilbert-base-es-cased/tree/1db4091).

## Dataset

| Partición | Frases | Propósito |
|---|---:|---|
| Entrenamiento | 2.176 | Semilla compatible, corpus previo y nuevas familias de órdenes, charla, motivación y abstención |
| Validación | 219 | Selección del checkpoint y calibración |
| Prueba v1 | 172 | Comparación con la prueba histórica reservada |
| Prueba v2 | 125 | Nuevas familias coloquiales, conversaciones, arengas, negaciones y órdenes múltiples |

Se verificaron las 11 acciones y las 4 intenciones en cada partición. El constructor conserva la procedencia, familia, texto, etiqueta semántica y BIO. Revisa conflictos y excluye de entrenamiento formulaciones normalizadas que aparezcan en validación o prueba, incluso tras sustituir nombres y ubicaciones. El corpus conserva variaciones sintéticas con pérdida de puntuación y tildes. La prueba v2 incluye 12 muestras de cada intención no táctica. Queda por construir una prueba con transcripciones de hablantes reales. [Auditoría y huellas de las particiones](../../AI%20NLP/Data/fase1-v2/audit.json).

La distribución final quedó en 80,8 % de entrenamiento, 8,1 % de validación y 11,0 % de prueba contando los dos conjuntos. Se preservó la prueba histórica y se agruparon las familias nuevas antes de asignarlas. La proporción 70/15/15 del prompt se usa como referencia para la siguiente ampliación.

## Ajuste fino de C

Se entrenaron el último bloque del Transformer y tres cabezas nuevas. Los embeddings y cinco bloques conservaron sus pesos. C clasifica intención y acción y asigna etiquetas BIO al primer subtoken de cada palabra. La entrada sustituye las menciones explícitas por marcadores de unidad y zona. Las entidades extraídas se resuelven con el catálogo actual.

La corrida usó semilla 421, CPU, lote 32, dropout 0,20, AdamW, learning rates de 0,00006 para el bloque y 0,0009 para las cabezas, weight decay 0,015, label smoothing 0,02 y clipping 1,0. La pérdida usa pesos 1,0, 1,5 y 0,65. Se ajustaron 7.120.919 de 63.198.743 parámetros en 163,6 s. Se eligió la época 4, con coincidencia de validación de 71,2 % antes del umbral. La parada temprana detuvo la corrida tras la época 7.

En el chequeo de pesos, el tensor de consulta del bloque congelado registró diferencia máxima 0 y el del bloque ajustado 0,0119. El paquete de pesos C ocupa 252,8 MB. Una lectura puntual registró 570 MiB de memoria residente para Python, PyTorch y el modelo después de inferencia. [Historial de entrenamiento](../results/fase1/entrenamiento-c.json), [verificación de pesos](../results/fase1/verificacion-c.json).

## Resultados textuales

Cada fila usa las mismas frases dentro de su prueba. Se aplicó el filtro textual compartido y el umbral 0,70 a los modelos calibrados. Qwen produce confianza nula. La tasa de propuestas erróneas cuenta las órdenes con un JSON semántico discrepante sobre todas las frases.

| Prueba | Modelo | JSON exacto | Orden exacta | Propuesta errónea | Latencia mediana / p95 |
|---|---|---:|---:|---:|---:|
| v1 | A · BiGRU original | 12,2 % | 8,8 % | 2,3 % | 2,4 / 4,9 ms |
| v1 | A · BiGRU reentrenada | 42,4 % | 40,9 % | 8,1 % | 1,0 / 1,4 ms |
| v1 | B · Qwen | 30,2 % | 28,9 % | 44,2 % | 2.120 / 3.065 ms |
| v1 | C · DistilBERT | 37,8 % | 34,0 % | 3,5 % | 25,6 / 33,1 ms |
| v2 | A · BiGRU original | 14,4 % | 2,2 % | 1,6 % | 2,6 / 4,8 ms |
| v2 | A · BiGRU reentrenada | 36,0 % | 27,0 % | 5,6 % | 1,0 / 1,5 ms |
| v2 | B · Qwen | 47,2 % | 36,0 % | 35,2 % | 2.114 / 2.515 ms |
| v2 | C · DistilBERT | 49,6 % | 40,4 % | 6,4 % | 23,8 / 30,7 ms |

En v2, C acertó el JSON completo en 62 de 125 ejemplos y se abstuvo correctamente en 11 de los 12 casos desconocidos. Todavía confunde formulaciones como «Alfa, que nadie rebase el lado derecho», que propuso como retirada. En F1 macro de intención de v2, B alcanzó 70,7 % y C 57,9 %. El cuaderno y los archivos por frase incluyen matrices de confusión, precisión, recall, F1 de entidades y calibración ECE/Brier. Las latencias son de CPU y hubo otras tareas locales concurrentes en algunas mediciones.

La BiGRU reentrenada volvió a iniciar con pesos aleatorios y recibió la misma partición de entrenamiento que C. La mejora de A respecto a su versión original muestra el aporte del corpus. La BiGRU reentrenada obtuvo el mejor JSON exacto en v1, y DistilBERT obtuvo el mejor resultado en v2. El contraste usa una corrida y protocolos de optimización propios de cada arquitectura. [Entrenamiento de A con el corpus ampliado](../results/fase1/entrenamiento-a-v2.json), [predicciones A reentrenada en v2](../results/fase1/evaluation-A-reentrenado-v2.json).

Se valida C como candidato textual. La captura y transcripción física quedan en Fase 2. La ejecución de las nuevas propuestas en Unreal se revisa en el escenario de integración correspondiente.

## Reproducir

1. Usa el entorno existente con PyTorch. En otra máquina prepara `.venv` con Python 3.14 y PyTorch CPU siguiendo el README. Instala las dependencias con `uv pip install --python .venv/Scripts/python.exe -r 'AI NLP/requirements-fase1.txt'`.
2. Coloca `config.json`, `tokenizer_config.json`, `vocab.txt` y `model.safetensors` de Geotrend en `AI NLP/models/distilbert-base-es-cased`. El SHA-256 de los pesos usados fue `748E54FF0D7341B8281AFA1B1B47A58AA0A735DE4DBB5FE49DC1B50EF1FDBCC5`.
3. Desde `AI NLP`, usa `python -m yell.phase1_data` para exportar el corpus y `python -m yell.train_transfer` para entrenar. El cuaderno llama al mismo entrenamiento con `REENTRENAR_C = True`.
4. Ejecuta `python -m yell.evaluate --model C --dataset v2` para medir. También admite A y B. B requiere llama.cpp en localhost. Usa `--llama-port` para indicar otro puerto. Entrena la segunda BiGRU con `python -m yell.train --dataset fase1-v2` y evalúala con `--model A --checkpoint models/scratch-fase1.pt --dataset v2`. Usa `--out` para conservar las evaluaciones de ambas variantes.
5. Ejecuta `python -m unittest discover -s tests -v` desde `AI NLP`. Pasaron 14 pruebas, incluida la carga de C con una orden válida y una negación.

[Cuaderno](../../AI%20NLP/Fase_1_Ajuste_fino.ipynb) · [Predicciones C v1](../results/fase1/evaluation-C-v1.json) · [Predicciones C v2](../results/fase1/evaluation-C-v2.json) · [Diagnóstico de micrófono](../results/DIAGNOSTICO_MICROFONO.md)
