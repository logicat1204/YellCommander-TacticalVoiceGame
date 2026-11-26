# SujetoLugar · NLP oficial de Yell Commander

SujetoLugar interpreta las órdenes y conversaciones de la partida en `127.0.0.1:18766`. El lanzador recomendado es **Jugar.cmd** en la raíz. El acceso directo de esta carpeta también arranca el mismo servicio. Consulta la [instalación](../../README.md#instalación-en-otra-pc) si es la primera vez.

## Lanzador y modelos de charla

Ejecuta el lanzador desde la raíz del proyecto con las opciones que necesites.

```powershell
.\Jugar.cmd
.\Jugar.cmd -SoloServicio
.\Jugar.cmd -Gemma4
.\Jugar.cmd -Postura
```

El inicio normal lee `modelo_charla` de [configuracion.json](configuracion.json). El valor predeterminado es `gemma2`, que usa Gemma 2 2B por LM Studio en el puerto 1234. El valor `gemma4` usa Gemma 4 E2B-it en su propio servidor local, en el puerto 18767. Los parámetros `-Gemma2` y `-Gemma4` permiten elegir el modelo para una ejecución.

El modo Gemma 4 usa el backend CUDA 12 de LM Studio con 2048 tokens de contexto, 15 capas en GPU por defecto y caché KV Q8. Puedes reducir las capas con `-CapasGPU 10` o usar `-CapasGPU 0` si tienes un ejecutable CPU compatible de llama.cpp en `AI NLP/models/llama`. `-VozCPU` hace que Whisper use CPU. El script de descarga verifica el SHA256 del archivo GGUF. [Pesos de Gemma 4 E2B-it Q4_K_M](https://huggingface.co/lmstudio-community/gemma-4-E2B-it-GGUF/blob/eed445ccfb8aef2e279df1a97e133baf06e443b4/gemma-4-E2B-it-Q4_K_M.gguf)

## Detener los servicios

```powershell
.\Jugar.cmd -Detener
.\Jugar.cmd -Detener -CerrarLMStudio
```

`-Detener` cierra SujetoLugar y su servidor Gemma 4, si está activo. Con Gemma 2, descarga el modelo si el lanzador lo cargó y detiene el servidor de LM Studio si el lanzador lo inició. El cierre normal de la partida aplica la misma limpieza. Si detienes los servicios desde otra consola, la ventana de Unreal queda abierta.

`-CerrarLMStudio` detiene también el servidor de LM Studio si ya estaba abierto antes de jugar. Conserva abierta la aplicación de escritorio. Si usaste `-SoloServicio -PuertoServicio 18768`, indica el mismo puerto al detener esa sesión.

## Interpretación

El extractor resuelve un destinatario y un destino según los soldados, pelotones y sectores disponibles. Una gramática y un clasificador de palabras y fragmentos de caracteres reconocen peticiones de movimiento. En el modo predeterminado, avanzar, explorar y defender llevan al grupo al sitio indicado. Si el destino es la base enemiga, el juego recibe la acción de ataque necesaria para dañar el núcleo. `-Postura` habilita la orden de mantener y defender un lugar. Los médicos actúan con sus reglas de partida. El clasificador de movimiento deriva otras peticiones de acción a la conversación.

Un nombre ambiguo, dos destinos o una petición incompleta impiden ejecutar la orden. Whisper puede reintentar con Small y recurrir a CPU cuando falta memoria CUDA. La primera consulta a cada modelo incluye su tiempo de carga.

Para conversar, Gemma recibe el nombre, la historia, la salud y el estado del soldado disponible. Kokoro usa una voz fija para cada indicativo. En proximidad el volumen cae con la distancia. Por radio se conserva la dirección del emisor y el filtro de radio. En Windows, Kokoro se inicializa en CPU para evitar conflictos con el cargador CUDA de Whisper.

## Entrenar y comprobar

Abre [SujetoLugar_Educativo.ipynb](SujetoLugar_Educativo.ipynb) o [SujetoLugar.ipynb](SujetoLugar.ipynb) con `.venv-decision`. La última celda permite probar frases propias. El entrenamiento usa un umbral elegido con validación y guarda los pesos en `modelos/intencion.joblib`. Reinicia el servicio para cargar los pesos actualizados.

```powershell
.\.venv-decision\Scripts\python.exe -m unittest discover -s .\Variantes\SujetoLugar -p test_slots.py -v
.\.venv-decision\Scripts\python.exe .\Variantes\SujetoLugar\probar_partida.py --salida .\Variantes\SujetoLugar\logs\prueba.json
```

`probar_partida.py` requiere el servicio activo. Comprueba órdenes por texto y voz y registra el primer token de Gemma, la síntesis de Kokoro y el audio devuelto. Durante el juego puedes consultar los tiempos con **F3** y comparar varias peticiones desde `AI NLP` con `..\.venv-decision\Scripts\python.exe -m yell.report_latency --ultimas 100`.

`comparar.py` y los archivos de resultados de esta carpeta conservan la comparación experimental con los clasificadores anteriores.
