# Resultados de pruebas de Yell Commander

## Entorno

Windows 11, Unreal Engine 5.8.4, Visual Studio 2022 con MSVC 14.44, Intel Core i5-13420H, 16 GB de RAM y NVIDIA GeForce RTX 4050 Laptop. BiGRU, Qwen 1.5B Q4_K_M y Whisper usaron CPU. PyTorch 2.10.0 y faster-whisper 1.2.1 se ejecutaron con Python 3.14.3.

## Pruebas automatizadas

| Prueba | Resultado observado |
|---|---|
| Suite Python | 10 de 10 correctas. Incluye esquema JSON, aliases, familias disjuntas, negaciones, WAV y acuerdo |
| `YellCommander.Contrato` | Correcta. Comprueba catálogo, confianza, campos inesperados, límite de cinco pelotones, médico único y cooldown |
| `YellCommander.Partida` | Correcta con el servicio de voz. Comprueba comandante, tres destinos navegables, movimiento real de Alfa, exclusividad de destinatario individual y de pelotón, fuera de alcance, duplicados, destino ausente, motivación, selección médica, reanimación y victoria |
| Compilación Editor Win64 | Correcta en Unreal Engine 5.8.4 |
| Réplicas | Tres `SoundWave` en español importadas en el proyecto. Una prueba sin dispositivo de audio sigue ejecutando y registrando órdenes |

La prueba de partida inyectó un WAV sintético por la misma ruta HTTP que utiliza Unreal después de capturar el micrófono. Whisper produjo «Alpha, avancem por el centro». A resolvió Alfa, avanzar y centro, y Unreal aplicó la orden únicamente a Alfa. El registro dio 718 ms para STT, 5,8 ms para NLP y 731 ms desde el envío de la solicitud hasta la respuesta del juego. Ese tiempo comienza con el WAV listo.

La repetición con D3D12, audio de Windows y el Modelo B también aprobó `YellCommander.Contrato` y `YellCommander.Partida`. El juego envió «Bravo, defiendan nuestra base», aplicó defender a Bravo y registró 3.447 ms de ida y vuelta. Qwen y la BiGRU coincidieron en los campos semánticos. [Registros de las dos órdenes](casos-ue.jsonl), [captura de Valle Alfa](valle-alfa.png).

## Reconocimiento de voz

Se usaron cinco frases sintetizadas en español latinoamericano, con y sin ruido blanco añadido de 12 dB, y un WAV de silencio. Tanto Tiny como Base trabajaron con cómputo int8 en CPU. El conjunto pequeño permite comprobar el recorrido y observar fallos.

| Modelo | WER limpio | WER con ruido | STT mediana limpia / con ruido |
|---|---:|---:|---:|
| Whisper Tiny | 78,3 % | 69,6 % | 405 / 347 ms |
| Whisper Base | 69,6 % | 52,2 % | 737 / 638 ms |

Ambos descartaron el silencio. Se seleccionó Base por su menor WER en estas muestras. La mayoría de las frases completas se transcribieron con errores o se descartaron. Queda medir el micrófono físico con personas y ruido ambiental real. [Resultados de voz por muestra](voice.json).

## Perfil de ejecución

Unreal CSV Profiler capturó el nivel a 1280 × 720 con D3D12 y la RTX 4050, fuera de pantalla. Se excluyeron los primeros 120 fotogramas. Para la prueba con B se estimó el intervalo activo a partir de la hora UTC de respuesta y del tiempo de ida y vuelta. La ventana de inferencia se recortó para reducir el error de alineación.

| Ventana de una partida con B | Fotogramas | Mediana de fotograma | p95 de fotograma | FPS a partir de la mediana | Game Thread mediano |
|---|---:|---:|---:|---:|---:|
| Antes de la solicitud | 1.249 | 6,31 ms | 7,93 ms | 158,6 | 3,06 ms |
| Durante la inferencia | 335 | 8,74 ms | 10,79 ms | 114,5 | 4,42 ms |

Se observaron 335 fotogramas durante la ventana de inferencia. La variación incluye el avance de la partida y el uso concurrente de CPU, por lo que corresponde a una comparación descriptiva de una sola captura. En una lectura del sistema posterior a la prueba, llama-server alcanzó un pico de 1.721 MiB de RAM residente y Python con BiGRU y Whisper alcanzó 484 MiB. Los modelos se configuraron para CPU. Quedó pendiente medir el consumo de VRAM de Unreal de forma aislada. [Resumen del perfil](renderer.json).

## Reproducción

Con el servicio iniciado, ejecuta `Automation RunTests YellCommander` en Valle Alfa con `-game`. Las opciones `-YellTestService` y `-YellTestWave="ruta"` verifican la llamada HTTP de voz. `-YellTestModelB` selecciona Qwen para la orden textual de la prueba. El servicio debe estar activo en el equipo durante estas variantes.

La comparación de ambos modelos y la ablación de dropout se documentan con resultados por frase, curvas y matriz de confusión. [Comparación experimental](../experiments/MODEL_COMPARISON.md).
