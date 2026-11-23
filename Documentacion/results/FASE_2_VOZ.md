# Fase 2 · Voz y comunicación

La revisión cubre Speech-to-Text, Push-to-Talk, canal, órdenes habladas, confirmación y latencia del apartado 24. El micrófono físico entregó muestras en modo juego. Dos pruebas con audio sintético verificaron la integración desde el búfer de captura hasta la respuesta de Valle Alfa. Queda pendiente una partida con voz humana y una prueba interactiva en Play In Editor. [Proyecto maestro](../PROYECTO_MAESTRO.md).

## Captura en Windows

WASAPI entregó 115 paquetes y 1.150 ms de audio a 48 kHz y dos canales. Marcó el primer paquete como discontinuo, sin más marcas durante el sondeo. El código anterior descartaba la toma completa al recibir esa marca. La captura admite la discontinuidad inicial y cancela si se produce otra después, si pierde el foco o si alcanza el límite de 12 s. Así evita enviar una orden incompleta. El sondeo del dispositivo contó muestras y descartó el audio antes de cualquier envío. [Diagnóstico](DIAGNOSTICO_MICROFONO.md) · [Registro de Unreal](fase2/casos-ue.json).

F3 muestra el nivel de señal durante la captura. Al soltar V, muestra el tiempo de pulsación, el audio recibido y la causa de descarte si corresponde. El historial `Saved/YellVoice.jsonl` guarda estadísticas de captura, y `Saved/YellOrders.jsonl` guarda la transcripción, la orden, el resultado y la latencia. Ambos registros se pueden cruzar por `request_id`. El WAV se transmite al servicio local en memoria.

## Transcripción y latencia

La prueba usó cuatro frases sintetizadas con eSpeak NG en español latinoamericano, una repetición de Alfa con ruido blanco a 12 dB, ruido blanco solo y silencio digital. Los percentiles incluyen seis casos por modelo, tras un calentamiento y excluyendo únicamente el silencio digital. Las cifras representan tiempo de STT en esta máquina.

| Whisper | p50 | p95 | Resultado para «Alfa, avancen por el centro» |
|---|---:|---:|---|
| Tiny | 389 ms | 1.699 ms | A y C se abstuvieron con y sin ruido a 12 dB |
| Base | 573 ms | 838 ms | A y C interpretaron la orden con y sin ruido a 12 dB |

Base conservó la negación en «Alfa, no avancen por el centro» e interpretó la arenga mediante A y C. Marcó «Bravo, defiendan nuestra base» como transcripción incierta. El servicio descartó ruido y silencio antes de NLP. Se mantiene Base como predeterminado por el resultado para Alfa. El tamaño y origen de la muestra limitan los percentiles a esta prueba. [Resultados por frase](fase2/voz-sintetica.json).

## Prueba de integración

| Caso | STT | NLP | De soltar V a la respuesta simulada | Resultado de Unreal |
|---|---:|---:|---:|---|
| C · radio | 837 ms | 28 ms | 878 ms | Alfa recibió la orden de avanzar al centro y el juego confirmó |
| A · proximidad fuera de alcance | 732 ms | 4 ms | 748 ms | El juego indicó que ningún soldado recibió la transmisión |

La automatización reprodujo el mismo WAV de 2,33 s en 219 paquetes y marcó el primero como discontinuo. La medición empieza al terminar esa captura simulada y acaba al publicar la respuesta visual. No incluye el tiempo de hablar ni mide el inicio del sonido de confirmación. El endpoint HTTP interpretó el mismo WAV con A, B y C. El tiempo de servicio de Qwen B fue de 7,27 s en una petición local. C se abstuvo ante la frase negada y distinguió el ruido del silencio. [Captura y resultado por solicitud](fase2/casos-ue.json) · [Respuestas HTTP](fase2/http-voz.json).

La compilación Win64 `Development Editor` terminó correctamente. Pasaron 18 pruebas Python y cuatro pruebas Unreal en Valle Alfa. La prueba `YellCommander.Voz.Captura` cubre también falta de muestras, captura breve, señal débil, interrupción y cortes después del arranque.

## Reproducción

Desde la raíz, abre el juego con `pwsh -File .\Scripts\Start-YellCommander.ps1 -Transfer`. F2 permite elegir C. Selecciona radio con R, mantén V mientras dices «Alfa, avancen por el centro» y suelta al terminar. F3 muestra la transcripción, la interpretación, el resultado y los tiempos. Para repetir la comparación sintética, ejecuta `..\.venv\Scripts\python.exe -m yell.phase2_voice` desde `AI NLP` con `espeakng-loader==0.2.4`, los checkpoints A y C y los modelos `whisper-tiny` y `whisper-base` en `AI NLP/models`.

Para repetir la automatización Unreal, usa Valle Alfa en modo juego con `-ExecCmds="Automation RunTests YellCommander"` y `-TestExit="Automation Test Queue Empty"`. Con el servicio local iniciado, agrega `-YellTestService` y `-YellTestWave="ruta a alfa.wav"`. Usa `-YellTestModelC` para radio con C o `-YellTestNearby` para la prueba fuera de alcance con A. `-YellProbeMicrophone` habilita el sondeo físico durante la automatización.
