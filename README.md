# Yell Commander

## Decisiones y conversaciones de soldados

### Peticiones simultáneas y medición

Puedes enviar hasta cuatro transmisiones sin esperar a que termine la primera. El contador del HUD separa las solicitudes activas de las respuestas de audio pendientes. Los audios se reproducen uno a uno en el orden en que llegan las respuestas. Una confirmación nueva nunca sustituye al audio que está sonando. **F4** silencia la voz. Mientras mantienes **V**, los audios que todavía esperan en cola se inician después de soltar la tecla.

**F3** muestra los tiempos de la última respuesta. Para comparar varias pruebas, Unreal guarda en su carpeta `Saved` tres registros con el mismo `request_id`.

| Archivo | Qué mide |
|---|---|
| `YellVoice.jsonl` | Tiempo de pulsación, duración capturada, señal y fallos de captura |
| `YellOrders.jsonl` | Whisper Base y Small, espera por etapa, decisión, primer token de Gemma, síntesis Kokoro, vuelta HTTP y transcripción |
| `YellAudio.jsonl` | Entrada en cola, inicio y fin de reproducción. El inicio registra cuánto pasó desde soltar V o enviar el texto |

Desde `AI NLP`, ejecuta `..\.venv-decision\Scripts\python.exe -m yell.report_latency --ultimas 30` para ver p50, p95 y tamaño de muestra por modelo, entrada y tipo de respuesta. Si Unreal escribió los archivos en otra carpeta, usa `--saved "ruta a Saved"`. En las órdenes de voz, compara `whisper_base_ms` con `whisper_reintento_ms`. En la charla, compara `primer_token_ms`, `charla_ms` y `tts_ms`. Si la espera domina, mira cuántas solicitudes había activas y distingue la cola del modelo de la cola de reproducción.

El servicio comparte una instancia por modelo entre las cuatro solicitudes. La transcripción, la decisión, la generación de diálogo y la síntesis admiten trabajo en distintas etapas al mismo tiempo. Cada etapa procesa una solicitud a la vez. [Medición de cuatro solicitudes](Documentacion/results/NLP_CONCURRENCIA.json).

Para probar este modo desde el lanzador habitual ejecuta `pwsh -File .\Scripts\Start-YellCommander.ps1 -Decisiones`. Después de publicar los pesos desde el cuaderno, el lanzador lo selecciona automáticamente en un arranque normal.

Abre [Decisiones GPU](AI%20NLP/Decisiones_GPU.ipynb) con el kernel **Yell Decisiones CUDA**. Con `ENTRENAR = False` comprueba dos minibatches y guarda un checkpoint separado de prueba. Para realizar tu entrenamiento, cambia a `ENTRENAR = True` y ejecuta el cuaderno completo. La última celda permite editar la frase, los nombres de los soldados y el sector. El mejor modelo se guarda en `AI NLP/models/decisiones/run-*`; `actual.txt` selecciona la corrida publicada. Los JSONL de entrenamiento, validación y prueba se encuentran en `AI NLP/Data/decisiones`.

Lanza este modo con `pwsh -File .\Scripts\Start-Decisiones.ps1`. La opción `-OnlyService` deja disponible el servicio para pruebas. Tras entrenar vuelve a iniciar el lanzador para cargar los pesos nuevos. Antes del primer entrenamiento hay una vista previa con órdenes frecuentes. Prueba con **T** «Alex, andá a cuidar el medio», «Alfa, que nadie pase por el medio» y «Alex, ¿cómo estás?». **V** permite hacer lo mismo por voz, **R** cambia de canal y **F3** muestra la decisión. En radio, un pelotón actúa como grupo y un solo integrante contesta la charla. En proximidad se aplica el alcance del juego. Un nombre sobre cada aliado cercano identifica quién puede responder.

El modo D usa la plantilla enviada por Unreal. El clasificador elige entre charla y las once acciones usando el texto con marcadores de unidad y lugar. Los nombres, lugares y pacientes se resuelven a identificadores de partida. El servicio devuelve `decision` con el esquema español y traduce la orden al contrato v1 de Unreal en `command`. Para «acá» usa el sector de mapa más cercano al comandante al iniciar la orden. La salida del modelo conversacional alimenta solo el texto visible y la voz. Una falta de señal en el micrófono conserva su diagnóstico de captura.

Gemma 2 2B Instruct Q4_K_M se sirve localmente por LM Studio. Kokoro sintetiza en español a 24 kHz mediante CUDA. Puedes ajustar el servidor, identificador de modelo, voz por perfil, velocidad, longitud y personalidad en [la configuración de charla](AI%20NLP/yell/dialogue.json). En radio se aplica un filtro de banda. En proximidad el sonido se reproduce en el actor que habla. **F4** controla la reproducción de voz.

### Reproducir el entorno de decisiones

Se verificaron el cuaderno en GPU con dos minibatches, la orden individual dirigida a Juan y la reproducción de la respuesta de Alex en Valle Alfa. La evidencia distingue la vista previa de los pesos que entrenes. También registra latencia, muestreo de VRAM y coste de los primeros 120 fotogramas de una partida D3D12 a 960 × 540. [Resultados de integración](Documentacion/results/DECISIONES_DIALOGO.json).

En esta máquina se preparó `.venv-decision` por separado. Para reproducirlo en una instalación CUDA compatible ejecuta desde la raíz:

```powershell
uv venv --python 3.11 .venv-decision
uv pip install --python .venv-decision/Scripts/python.exe torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python .venv-decision/Scripts/python.exe -r 'AI NLP/requirements-decisiones.txt'
uv pip uninstall --python .venv-decision/Scripts/python.exe onnxruntime
uv pip install --python .venv-decision/Scripts/python.exe --reinstall --no-deps onnxruntime-gpu==1.20.2
.\.venv-decision\Scripts\python.exe -m ipykernel install --user --name yell-decisiones --display-name 'Yell Decisiones CUDA'
```

Kokoro y faster-whisper declaran dependencias que instalan el módulo ONNX Runtime de CPU en la misma ruta que el de GPU. Los dos últimos pasos de `uv` dejan el proveedor CUDA como implementación activa. Mantén en `AI NLP/models` el encoder español de la Fase 1 y Whisper Base/Small. Para el diálogo coloca `kokoro-v1.0.onnx` y `voices-v1.0.bin` como `dialogo/kokoro.onnx` y `dialogo/voices.bin`. En LM Studio importa el archivo con `lms import "AI NLP/models/dialogo/gemma-2-2b-it-Q4_K_M.gguf" --hard-link --user-repo bartowski/gemma-2-2b-it-GGUF -y`. El lanzador carga el modelo en GPU y mantiene el identificador `yell-gemma`. [Pesos de Kokoro](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0) · [Gemma cuantizado](https://huggingface.co/bartowski/gemma-2-2b-it-GGUF).

Juego de estrategia en primera persona para Unreal Engine 5.8. El comandante dirige pelotones mediante frases en español. Valle Alfa integra el micrófono, modelos NLP locales, un contrato JSON y un ejecutor compartido por los dos bandos.

## Fase 1 y cuaderno de ajuste fino

Abre [Fase 1 · Ajuste fino](AI%20NLP/Fase_1_Ajuste_fino.ipynb) con el intérprete `.venv/Scripts/python.exe`. El cuaderno permite inspeccionar el dataset, repetir el ajuste fino de DistilBERT en español, comparar A/B/C y probar frases propias. Usa `REENTRENAR_C = True` para volver a entrenar. [Informe textual](Documentacion/experiments/FASE_1_NLP.md) · [Proyecto maestro](Documentacion/PROYECTO_MAESTRO.md) · [Plan por fases](Documentacion/bitacora/PLAN_POR_FASES.md).

```powershell
Push-Location 'AI NLP'
..\.venv\Scripts\python.exe -m yell.evaluate --model C --text 'Médicos, atiendan a Bravo en el centro'
Pop-Location
```

La Fase 2 corrige la captura con V y documenta el sondeo del micrófono, las pruebas con Whisper y las latencias. [Informe de voz](Documentacion/results/FASE_2_VOZ.md) · [Diagnóstico del micrófono](Documentacion/results/DIAGNOSTICO_MICROFONO.md).

## Iniciar en Windows

Desde la raíz del proyecto, ejecuta el lanzador. Abre el juego en una ventana y conserva los servicios locales hasta que cierres la partida.

```powershell
pwsh -File .\Scripts\Start-YellCommander.ps1
```

El proyecto Unreal está en `WarCommanderDemo\WarCommanderDemo.uproject`. Valle Alfa genera la arena al comenzar la partida. Si el editor se instaló en otra carpeta, pasa su ejecutable como `-UnrealEditor`. Añade `-Transfer` para habilitar DistilBERT (C) en F2 en la partida que abre el lanzador. Para probar A con texto, utiliza `-NoLLM -NoVoice`. Para supervisar el servicio mientras usas Play en el editor, utiliza `-OnlyService`. Los servicios usan los puertos locales 18765 (voz y NLP) y 8081 (llama.cpp).

### Controles

| Tecla | Acción |
|---|---|
| WASD y ratón | Moverse y mirar en primera persona |
| Espacio | Saltar |
| V | Hablar mientras se mantiene pulsada. Soltar para enviar |
| T | Escribir una frase. Enter envía y Esc cierra |
| R | Cambiar entre radio y proximidad |
| F2 | Cambiar entre los modelos cargados por el lanzador |
| F3 | Mostrar diagnóstico del micrófono, texto, JSON, latencias e historial |
| F4 | Activar o silenciar las respuestas habladas |
| E / F | Pedir un pelotón de refuerzo / médico cerca de la terminal |
| F5 | Reiniciar después de victoria o derrota |

Prueba «Alfa, avancen por el centro», «Bravo, defiendan nuestra base» y «Soldados, ustedes pueden con esto, vamos a ganar». La radio exige un pelotón o soldado explícito para las órdenes. «Soldado Alfa dos, avancen por el centro» se dirige únicamente a Alfa-2. En proximidad solo participan soldados al alcance y un destinatario implícito requiere un único pelotón disponible. Una arenga general válida puede afectar a varios pelotones. El registro de ejecución se guarda en `WarCommanderDemo/Saved/YellOrders.jsonl`.

El servicio reconoce directamente órdenes frecuentes cuando puede interpretar la frase completa. Las demás pasan al modelo elegido en F2. A usa los pesos de la BiGRU reentrenada en la Fase 1 cuando están instalados. Para ejecutar una propuesta de orden o arenga de Qwen, el servicio compara primero con A. Si discrepan y está instalado el verificador DistilBERT, también puede confirmar la propuesta con C. El registro incluye `nlp_route`, `verified_by` y los tiempos de voz y NLP.

Mantén pulsada V y empieza a hablar cuando aparezca **GRABANDO**. Esa indicación se activa al recibir muestras del dispositivo. El lanzador usa Whisper Base para la primera lectura. Si la transcripción queda incierta o fuera de la gramática rápida, vuelve a escuchar el mismo audio con Whisper Small cuando está instalado. El registro de voz conserva el texto inicial y el elegido. Para reproducir la prueba con A y B, inicia el lanzador con `-OnlyService` y ejecuta `..\.venv\Scripts\python.exe -m yell.bench_partida` desde `AI NLP`. [Validación de voz y NLP](Documentacion/results/REVISION_VOZ_NLP.md).

«Alfa, avancen hacia adelante a atacar» y «Bravo, vayan a destruir la base del enemigo» ordenan atacar el núcleo rival. El pelotón prioriza el núcleo cuando queda visible y a su alcance. «Bravo, adelante» indica avanzar hacia la base rival. «Alfa, ataquen el flanco izquierdo» conserva el destino indicado. También puedes decir «Médicos, al centro» o «Médicos, vayan a curar al centro». En radio, empieza con el nombre del destinatario.

Desde `AI NLP`, `..\.venv\Scripts\python.exe -m yell.bench_live_commands` comprueba ocho frases con las tres selecciones de modelo y mide la interpretación en el servicio local. Si existe el WAV de Alfa de la Fase 2, también mide una solicitud completa de voz.

F3 muestra el pico de señal mientras mantienes V. Al soltar, muestra el audio recibido y el motivo si se descarta. El diagnóstico también se registra en `WarCommanderDemo/Saved/YellVoice.jsonl`. Cuando se envía audio al servicio, el identificador de solicitud vincula la captura con su resultado.

### Preparar otra máquina

1. Instala Unreal Engine 5.8, Visual Studio 2022 con C++ y Windows SDK, Python 3.14 y uv. Desde la raíz, instala las dependencias y entrena el modelo A.

   ```powershell
   uv venv --python 3.14 .venv
   uv pip install --python .venv/Scripts/python.exe --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple torch==2.10.0
   uv pip install --python .venv/Scripts/python.exe faster-whisper==1.2.1 jsonschema==4.26.0
   $env:PYTHONUTF8 = '1'
   Push-Location 'AI NLP'
   ..\.venv\Scripts\python.exe -m yell.train
   Pop-Location
   ```

2. Extrae la distribución Windows CPU de llama.cpp (`b12556` para la reproducción) en `AI NLP/models/llama`. Guarda el archivo oficial `qwen2.5-1.5b-instruct-q4_k_m.gguf` en la misma carpeta. Copia `config.json`, `model.bin`, `tokenizer.json` y `vocabulary.txt` de Whisper Base multilingüe en `AI NLP/models/whisper-base`. La descarga inicial requiere conexión. La ejecución usa los archivos locales. [llama.cpp b12556](https://github.com/ggml-org/llama.cpp/releases/tag/b12556), [Qwen GGUF](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/tree/main), [Whisper Base](https://huggingface.co/Systran/faster-whisper-base/tree/main).

3. Compila el objetivo `WarCommanderDemoEditor`, configuración `Development Editor` para Win64, desde Visual Studio o el `Build.bat` del motor. El nivel es `/Game/Yell/ValleAlfa`. Los modelos descargados, artefactos intermedios de UE y el entorno Python se excluyen con `.gitignore`.

## Pruebas y evaluación

```powershell
Push-Location 'AI NLP'
..\.venv\Scripts\python.exe -m unittest discover -s tests -v
..\.venv\Scripts\python.exe -m yell.evaluate --model A --text 'Alfa, avancen por el centro'
..\.venv\Scripts\python.exe -m yell.evaluate --model A
..\.venv\Scripts\python.exe -m yell.evaluate --model B
Pop-Location
```

Para evaluar B, deja llama.cpp levantado con el lanzador en otra terminal. Ambos evaluadores recorren el mismo conjunto de prueba y registran salida cruda, resultado tras las reglas de validación, precisión, F1, matrices de confusión, coincidencia semántica y latencia. En Unreal se pueden ejecutar `YellCommander.Contrato` y `YellCommander.Partida` usando el nivel Valle Alfa en modo `-game`. Para probar el HTTP desde Unreal, añade `-YellTestService` con el servicio activo. Añade `-YellTestModelB` para el segundo modelo o `-YellTestWave="ruta al WAV"` para la prueba por audio.

Las réplicas de radio en español están en `/Game/Yell/Audio`. Para regenerarlas, instala `espeakng-loader==0.2.4` y ejecuta `python -m yell.voice_bench --reply-dir RUTA` desde `AI NLP`. Después ejecuta `WarCommanderDemo/Scripts/import_radio_replies.py` en Unreal Editor con `YELL_REPLY_SOURCE` apuntando a esa carpeta. Los módulos `yell.export_model` y `yell.plot_results` usan ONNX y Matplotlib, respectivamente.

La [auditoría inicial](Documentacion/datasets/AUDITORIA.md), el [diseño](Documentacion/architecture/SYSTEM_DESIGN.md), el [estado del prototipo](Documentacion/bitacora/IMPLEMENTATION_STATUS.md) y los [resultados de pruebas](Documentacion/results/TEST_RESULTS.md) describen el alcance y la validación.
