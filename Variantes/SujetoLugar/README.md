# Variante de sujeto y lugar

En la partida normal, D conserva su clasificador de acciones y los pesos publicados en el cuadernillo original. La variante tiene pesos, cuadernillo, configuración de charla y lanzador propios. Ambos usan el mismo mapa, micrófono, catálogo de soldados y contrato HTTP que valida Unreal.

## Entrar al juego

Desde la raíz del proyecto, ejecuta uno de estos comandos por partida.

```powershell
.\Scripts\Start-Decisiones.ps1
.\Variantes\SujetoLugar\Iniciar.ps1
.\Variantes\SujetoLugar\Iniciar.ps1 -Postura
.\Variantes\SujetoLugar\Iniciar.ps1 -Gemma4
```

La primera línea abre la versión habitual. La segunda lee `modelo_charla` de [configuracion.json](configuracion.json). Usa `gemma4` para Gemma 4 E2B-it o `gemma2` para Gemma 2. La tercera activa además las posturas. Los parámetros `-Gemma2` y `-Gemma4` eligen el modelo durante una ejecución. Usa V para grabar y T para escribir. Prueba «Juan, andá al puente», «Bravo, cubran nuestra base», «Alfa, ataquen la base rival» y «Juan, ¿cuánta salud te queda?». Cierra la partida anterior para liberar sus modelos antes de comparar en la RTX 4050.

El perfil experimental escucha en 18766 y el juego lo selecciona con `-YellSujetoLugar`. Gemma 4 tiene su propio servidor local en 18767. El lanzador usa el backend CUDA 12 de LM Studio, texto, 2048 tokens, 15 capas en GPU, Flash Attention y caché KV Q8. Puedes ajustar las capas con `-CapasGPU 10`, elegir STT por CPU con `-VozCPU` o levantar únicamente el servicio con `-SoloServicio`. El GGUF lleva un SHA256 verificado antes de publicarse. [Pesos de Gemma 4 E2B-it Q4_K_M](https://huggingface.co/lmstudio-community/gemma-4-E2B-it-GGUF/blob/eed445ccfb8aef2e279df1a97e133baf06e443b4/gemma-4-E2B-it-Q4_K_M.gguf)

## Detener los servicios

Desde otra consola en la raíz del repositorio, usa uno de estos comandos mientras el lanzador esté en marcha.

```powershell
.\Variantes\SujetoLugar\Jugar.cmd -Detener
.\Variantes\SujetoLugar\Jugar.cmd -Detener -CerrarLMStudio
```

También puedes usar `Iniciar.ps1` con los mismos parámetros. `-Detener` finaliza el servicio SujetoLugar y su servidor Gemma 4. Con Gemma 2, descarga el modelo si el lanzador lo cargó y detiene el servidor de LM Studio si el lanzador lo inició. El cierre normal de la partida aplica la misma limpieza. Al detener los servicios desde otra consola, la ventana de Unreal queda abierta.

`-CerrarLMStudio` solicita además cerrar el servidor local de LM Studio si estaba abierto antes de jugar. Intenta descargar el alias `yell-gemma` y el cierre del servidor también afecta las demás aplicaciones conectadas a ese servidor. Puedes seguir usando la aplicación de escritorio.

Si arrancaste con `-SoloServicio -PuertoServicio 18768`, indica también `-PuertoServicio 18768` para detener esa sesión.

## Qué interpreta

El extractor resuelve un único destinatario y un único destino contra el catálogo de la partida. «Acá» depende de la ubicación del jugador. Una gramática breve y un clasificador lineal de palabras y fragmentos de caracteres reconocen peticiones de movimiento. En el perfil simple avanzar, atacar, explorar y defender llevan al grupo al sitio indicado. El adaptador usa la acción de ataque en el núcleo rival porque el juego la exige para dañarlo. El modo `-Postura` permite mandar defender un destino. Para ejecutar acciones diferenciadas de curación, reanimación, cancelación o patrulla repetida, utiliza el perfil habitual.

Un nombre ambiguo, dos destinos o una petición incompleta quedan fuera de las órdenes ejecutables. Whisper Base se ejecuta una vez por transmisión. La segunda lectura con Small se reserva para baja calidad acústica, una intención dudosa o datos de la orden que podrían haberse perdido. La variante comprueba memoria CUDA al cargar cada reconocedor y puede recurrir a CPU. El primer uso incluye la carga de cada modelo. La cola admite cuatro solicitudes y conserva la reproducción secuencial.

En la variante, cada soldado recibe una historia al aparecer. La charla usa su salud, sus bajas confirmadas y si tiene un rival a la vista. La voz Kokoro queda fijada por indicativo. En proximidad se atenúa con la distancia. Por radio se conserva la dirección del emisor y el filtro de radio.

## Entrenar y medir

Abre [SujetoLugar.ipynb](SujetoLugar.ipynb) con el entorno del proyecto `.venv-decision`. La selección del umbral usa validación. El entrenamiento solo escribe los pesos de esta carpeta. La última celda acepta frases libres. Las versiones adicionales de dependencias están en [requirements.txt](requirements.txt).

```powershell
.\.venv-decision\Scripts\python.exe .\Variantes\SujetoLugar\comparar.py texto
.\.venv-decision\Scripts\python.exe .\Variantes\SujetoLugar\comparar.py voz --por-etapas
.\.venv-decision\Scripts\python.exe .\Variantes\SujetoLugar\probar_partida.py --salida .\Variantes\SujetoLugar\logs\prueba.json
```

La prueba de texto calcula coincidencia de destinatario y lugar sobre el mismo conjunto y cuenta falsos movimientos. Para el modelo con postura informa también el acierto completo. La prueba de voz sintetiza los mismos 20 WAV para los tres perfiles, con negaciones, preguntas, una orden plural, ruido y silencio. El perfil «anterior» reproduce el criterio antiguo de activar Small. Con `--por-etapas` se precalienta y mide cada reconocedor por separado y se reproduce su salida a través del servicio. La latencia es la suma del STT medido y del procesamiento HTTP interno. Excluye la captura, la carga inicial y la charla. Estas pruebas de desarrollo se complementan con las partidas de micrófono real.

El último comando requiere la variante en ejecución y prueba también Gemma y Kokoro. Guarda el texto devuelto, el tiempo al primer token, el TTS y los bytes de audio. Durante el juego, F3 muestra la última transmisión. El registro `WarCommanderDemo/Saved/YellOrders.jsonl` guarda el perfil, la primera transcripción, el motivo del reintento, la lectura alternativa, el dispositivo utilizado y la decisión final. Para comparar hasta el inicio audible, ejecuta desde `AI NLP` el comando `..\.venv-decision\Scripts\python.exe -m yell.report_latency --ultimas 100`.
