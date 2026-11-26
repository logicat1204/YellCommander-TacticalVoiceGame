# Yell Commander

Juego de estrategia en primera persona para Unreal Engine 5.8. En Valle Alfa das órdenes en español a soldados o pelotones por voz o texto. **SujetoLugar** interpreta la orden y Unreal la ejecuta. También puedes conversar con los soldados y escuchar sus respuestas.

## Jugar en Windows

Con la [instalación preparada](#instalación-en-otra-pc), haz doble clic en **Jugar.cmd** en la raíz del proyecto. El lanzador abre el menú principal y levanta el servicio local de voz y NLP. En **Jugar**, elige **Fácil**, **Normal** o **Difícil**. El rival recibe informes cada 7, 3,5 o 1,25 segundos, respectivamente. En dificultades altas inicia ataques con una ventaja menor. Puedes ajustar la sensibilidad, la calidad gráfica y el volumen desde **Configuración**.

El [archivo de configuración](Variantes/SujetoLugar/configuracion.json) elige el modelo de charla. **Gemma 2 2B** es el predeterminado. Puedes seleccionar **Gemma 4 E2B** o usar las opciones del [lanzador SujetoLugar](Variantes/SujetoLugar/README.md). Si trabajas desde Unreal Editor, inicia primero el servicio con el siguiente comando y luego abre Valle Alfa.

```powershell
.\Jugar.cmd -SoloServicio
```

El cierre normal de la partida detiene los procesos que inició el lanzador. Desde otra consola puedes solicitar el cierre con `-Detener`.

```powershell
.\Jugar.cmd -Detener
```

### Controles

| Tecla | Acción |
|---|---|
| WASD y ratón | Moverse y mirar |
| Espacio | Saltar |
| Esc | Abrir o cerrar el menú de pausa |
| V | Mantener pulsada para hablar y soltar para enviar |
| T | Escribir una frase. Enter envía y Esc cierra |
| R | Cambiar entre radio y proximidad |
| Clic derecho | Mantener pulsado para usar los binoculares |
| E / F | Pedir un pelotón de refuerzo o un médico cerca de la terminal |
| F3 | Consultar diagnóstico, transcripción y latencias |
| F4 | Activar o silenciar las respuestas habladas |
| F5 | Volver al menú principal después de una victoria o derrota |

Valle Alfa tiene un camino central y dos flancos unidos por cinco cruces. El minimapa muestra las rutas transitables y las tropas aliadas. Los médicos de cada bando comparten 200 puntos de curación y una reanimación. Ambas reservas se recargan cada cinco minutos.

## Órdenes y conversación

Prueba «Alfa, avancen por el centro», «Juan, andá al puente», «Bravo, ataquen la base rival» o «Alex, ¿cuánta salud te queda?». Por radio, nombra al soldado o al pelotón. En proximidad, el alcance determina quién puede recibir la orden o contestar. Mantén **V** pulsada y empieza a hablar cuando aparezca **GRABANDO**.

1. **Entrada.** Whisper Base transcribe el audio. Whisper Small se reserva para una lectura dudosa. El texto escrito entra directamente.
2. **Decisión.** SujetoLugar combina reglas y regresión logística sobre rasgos TF-IDF. Resuelve un destinatario y un lugar con el catálogo de la partida. Para «acá», usa el sector más cercano al comandante.
3. **Salida.** Las órdenes llegan a Unreal en JSON por el servicio local en el puerto 18766. En una conversación, Gemma redacta la respuesta y Kokoro la convierte en voz.

La radio admite hasta cuatro solicitudes o audios pendientes y reproduce las respuestas una por una. Los registros de `WarCommanderDemo/Saved` vinculan la captura (`YellVoice.jsonl`), las etapas de interpretación (`YellOrders.jsonl`) y la reproducción (`YellAudio.jsonl`) mediante `request_id`.

## Instalación en otra PC

Necesitas **Unreal Engine 5.8**, Visual Studio con la carga de trabajo de desarrollo de juegos en C++ y el SDK de Windows, **Python 3.11** mediante `uv` y **LM Studio** con su CLI `lms` para Gemma 2. El arranque con CUDA requiere una GPU NVIDIA compatible. Para transcribir por CPU puedes usar `.\Jugar.cmd -VozCPU`.

1. Prepara el entorno local desde la raíz del proyecto con estos comandos.

   ```powershell
   uv venv --python 3.11 .venv-decision
   uv pip install --python .venv-decision/Scripts/python.exe torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
   uv pip install --python .venv-decision/Scripts/python.exe -r 'Variantes/SujetoLugar/requirements.txt'
   ```

2. Coloca los modelos multilingües de Whisper en `AI NLP/models/whisper-base` y `AI NLP/models/whisper-small`. Guarda `kokoro-v1.0.onnx` y `voices-v1.0.bin` como `AI NLP/models/dialogo/kokoro.onnx` y `AI NLP/models/dialogo/voices.bin`. Descarga Gemma 2 2B Instruct Q4_K_M e impórtalo en LM Studio. El lanzador lo carga con el identificador `yell-gemma`. [Whisper Base](https://huggingface.co/Systran/faster-whisper-base/tree/main) · [Whisper Small](https://huggingface.co/Systran/faster-whisper-small/tree/main) · [Archivos de Kokoro](https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0) · [Gemma 2 GGUF](https://huggingface.co/bartowski/gemma-2-2b-it-GGUF)
3. Compila el objetivo `WarCommanderDemoEditor` en **Development Editor / Win64** y abre [WarCommanderDemo.uproject](WarCommanderDemo/WarCommanderDemo.uproject) o ejecuta `Jugar.cmd`. Si instalaste el editor en otra ruta, pasa `-UnrealEditor "ruta\UnrealEditor.exe"` al lanzador.

El repositorio incluye el [clasificador entrenado](Variantes/SujetoLugar/modelos/intencion.joblib). Puedes iniciar una partida con esos pesos.

## Entrenamiento y pruebas

El [cuaderno educativo](Variantes/SujetoLugar/SujetoLugar_Educativo.ipynb) explica cómo se prepara el dataset, cómo se entrena el clasificador y cómo probar frases propias. El [cuaderno de entrenamiento](Variantes/SujetoLugar/SujetoLugar.ipynb) y las [instrucciones de pruebas y latencia](Variantes/SujetoLugar/README.md) usan el mismo código que el juego.

Los cuadernos, informes y resultados de las primeras fases se conservan como [documentación histórica](Documentacion/bitacora/PLAN_POR_FASES.md).
