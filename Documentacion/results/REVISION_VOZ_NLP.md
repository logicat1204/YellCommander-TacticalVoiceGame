# Revisión de voz y NLP en partida

En la sesión revisada, las 29 solicitudes de voz vinculadas al micrófono llegaron con estado de captura `listo`. La mediana de la diferencia entre tiempo pulsado y audio recibido fue de 226 ms. El registro permite medir esa diferencia, pero no localizar las sílabas perdidas. «Rabo», «Labo» y «Brabo» aparecieron en el lugar del destinatario de órdenes completas. El HUD ahora muestra **GRABANDO** al recibir muestras. El servicio permite recuperar variantes observadas de un indicativo solo en voz, con el pelotón disponible y una orden completa reconocida.

## Comprensión textual

El servicio prefería los primeros pesos de A incluso cuando estaba instalada la BiGRU reentrenada con 2.176 frases. Ahora carga esa segunda versión y la usa también para verificar Qwen. Si A discrepa de una propuesta de B, DistilBERT puede confirmarla cuando está instalado. La comparación siguiente reproduce las decisiones con las predicciones archivadas para las mismas 125 frases reservadas de la Fase 1. Cada acierto exige que coincidan intención, destinatario, acción, lugar y objetivo.

| Configuración | Respuestas exactas | Órdenes propuestas con algún campo erróneo |
|---|---:|---:|
| A original | 18/125 | 2/125 |
| A reentrenado | 45/125 | 7/125 |
| B confirmado por A original | 27/125 | 0/125 |
| B confirmado por A reentrenado | 35/125 | 0/125 |
| B confirmado por A reentrenado o C | 43/125 | 0/125 |

Las métricas corresponden a la interpretación por los modelos, antes de aplicar las reglas rápidas de partida. A recupera más órdenes y también propone más órdenes equivocadas en esta prueba. B todavía se abstiene con frecuencia. [Comparación por configuración](fase2/comparacion-politicas.json).

## Reconocimiento de voz

Whisper Small multilingüe está instalado en `AI NLP/models/whisper-small`. El lanzador lo usa como segundo intento sobre el mismo WAV si Base necesita ayuda. El segundo intento conserva las negaciones, condiciones, destinatarios y lugares reconocidos en el primero cuando el servicio detecta que las lecturas discrepan sobre ellos. El JSON registra ambas decisiones con `first_transcript`, `retried` y `used_retry`. Para instalar el modelo en otra máquina se necesitan `model.bin`, `config.json`, `tokenizer.json` y `vocabulary.txt`. [Distribución de Whisper Small](https://huggingface.co/Systran/faster-whisper-small).

La comparación inicial usó ocho clips sintetizados con la misma voz. Small transcribió «Bravo, defiendan nuestra base» y «Alfa, ataquen la base enemiga». Base produjo «La voz de fiendas muestra va a ser» en el primero y se abstuvo en el segundo. Small también produjo la variante «Médicos, vaya al centro», que la gramática de partida admite. [Transcripciones y tiempos por clip](fase2/voz-base-small.json).

La prueba HTTP utiliza seis audios y tres textos con cada selección A y B. Comprueba el significado de salida completo, incluidas una negación, una charla y una orden de defensa sin lugar. Para reproducirla, ejecuta `python -m yell.bench_partida` desde `AI NLP` con el servicio y llama.cpp activos. Los tiempos de servicio incluyen STT y NLP. La voz sintetizada permite repetir el ensayo. La precisión con distintas voces humanas sigue pendiente de medición. [Respuestas de partida](fase2/partida-nlp-voz.json).
