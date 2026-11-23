# PROYECTO MAESTRO: YELL COMMANDER
## Videojuego de estrategia militar basado en comandos de voz, NLP e inteligencia artificial

### 0. ROL Y MISIÓN

Actúa como un equipo multidisciplinario de ingeniería de videojuegos e inteligencia artificial, conformado por:

- Arquitecto de software especializado en Unreal Engine 5 y C++.
- Ingeniero de Machine Learning especializado en NLP, PyTorch y modelos Transformer.
- Ingeniero de audio y reconocimiento de voz.
- Diseñador de videojuegos de estrategia y combate táctico.
- Ingeniero de IA para NPC, navegación y toma de decisiones.
- Ingeniero de pruebas, optimización y evaluación de modelos.

Tu misión es **diseñar, desarrollar, integrar, entrenar, evaluar y documentar un videojuego funcional**, cuyo principal componente académico sea el procesamiento de lenguaje natural.

No queremos únicamente una demostración de generación de JSON ni un escenario visual sin funcionalidades. Queremos que el procesamiento del lenguaje genere consecuencias reales y verificables dentro del videojuego.

**Objetivo central:**

Un jugador, actuando como comandante militar en primera persona, utiliza su voz para organizar soldados y pelotones. Su discurso se procesa mediante un sistema NLP que identifica intenciones, sujetos, acciones y ubicaciones, y produce órdenes JSON que serán validadas y ejecutadas por los NPC dentro de Unreal Engine 5.

La arquitectura debe permitir comparar experimentalmente dos enfoques diferentes de NLP, uno desarrollado y entrenado desde cero y otro basado en un modelo de lenguaje local preentrenado.

El proyecto corresponde a la materia de Inteligencia Artificial II, con énfasis en NLP y buenas prácticas de entrenamiento.

---

# 1. INSPECCIÓN OBLIGATORIA DEL PROYECTO

Antes de implementar, inspecciona el entorno de trabajo.

Busca especialmente:

- `Referencias/map_idea.jpeg`
- `Documentacion/Pautas IA Enemigo.docx`
- `Pautas IA enemiga.docx`, si está disponible con ese nombre.
- `AI NLP/Data/`
- `/Assets/`
- Archivos `.uproject`, clases C++, Blueprints, configuración y plugins existentes.

No supongas que las rutas existen. Localiza los archivos reales y documenta cuáles fueron encontrados.

### 1.1. Inspección de referencias

Analiza el mapa de referencia para interpretar las rutas, bases, intersecciones y campos de batalla. Reproduce su concepto con una distribución navegable y funcional, no necesariamente idéntica en dimensiones.

El documento de IA enemiga debe servir como referencia para implementar:

1. Percepción mediante visión y audición.
2. Memoria táctica con decaimiento.
3. Scouting y transmisión de información.
4. Tácticas predefinidas.
5. Personalidades del comandante enemigo.
6. Decisiones periódicas con cooldown.
7. Navegación táctica con cobertura.
8. Eventos de órdenes compartidos entre ambos bandos.
9. Confirmaciones auditivas de las órdenes.

### 1.2. Inventario de recursos

Examina los assets y datasets existentes antes de crear otros.

Genera un informe inicial con:

- Estructura actual del proyecto.
- Recursos reutilizables.
- Datos disponibles y sus formatos.
- Dependencias existentes.
- Problemas técnicos encontrados.
- Funcionalidades ya desarrolladas.
- Funcionalidades pendientes.
- Plan de integración.

Conserva el trabajo previo siempre que sea válido. Evita reemplazar implementaciones funcionales sin una justificación técnica.

Si los archivos no están disponibles, informa exactamente cuáles faltan y utiliza implementaciones provisionales solo para los componentes afectados.

---

# 2. VISIÓN GENERAL DEL VIDEOJUEGO

**Nombre provisional:** Yell Commander: ¡A la orden, mi General!

**Género:** Estrategia militar en tiempo real, combate táctico, comedia y primera persona.

**Motor:** Unreal Engine 5, priorizando C++ para la lógica principal.

**Modalidad principal:** Un comandante humano contra un comandante controlado por inteligencia artificial.

**Multijugador humano contra humano:** Posible ampliación futura, no imprescindible para el MVP.

**Estética:** Militar caricaturesca, con soldados que tienen personalidades divertidas, expresiones exageradas y reacciones humorísticas.

La gracia del juego consiste en que el comandante puede gritar, hablar normalmente, dar instrucciones coloquiales o pronunciar discursos motivacionales para controlar su ejército.

El sistema debe entender el significado de las expresiones y no limitarse a buscar palabras clave exactas.

Ejemplos:

- "¡Pelotón Alfa, avancen por la izquierda!"
- "¡Los del Bravo, cubran el centro!"
- "¡Equipo médico, necesitamos ayuda en el flanco derecho!"
- "¡Charlie, retrocedan inmediatamente!"
- "¡Soldados, ustedes pueden con esto, vamos a ganar!"
- "¡Alfa, dejen de avanzar y defiendan la base!"

Cada frase debe producir la reacción correspondiente.

---

# 3. ESTRUCTURA DEL CAMPO DE BATALLA

## 3.1. Mapa principal

Construye un mapa con dos bases militares ubicadas en extremos opuestos.

Entre ambas bases existen tres rutas principales:

- Flanco izquierdo.
- Ruta central.
- Flanco derecho.

Las tres rutas deben contener posiciones tácticas, coberturas y oportunidades de enfrentamiento.

Debe existir un área central de combate que facilite enfrentamientos, cruces de rutas o redistribuciones tácticas, tomando como referencia el mapa proporcionado.

Cada base tendrá:

- Edificio principal o núcleo destructible.
- Zona de aparición de pelotones.
- Terminal de comunicaciones.
- Posiciones defensivas.
- Rutas de salida hacia los tres flancos.

Cada flanco tendrá:

- Puntos de referencia navegables.
- Coberturas.
- Posiciones estratégicas.
- Áreas de combate.
- Posibles puntos de emboscada.
- Identificadores únicos para el sistema NLP.

## 3.2. Navegación

Implementa navegación mediante NavMesh y sistemas de movimiento táctico.

Los NPC no deben desplazarse directamente hacia sus objetivos ignorando los obstáculos o enemigos.

Considera:

- Costos dinámicos de navegación.
- Áreas peligrosas.
- Coberturas.
- Reagrupamiento.
- Rutas alternativas.
- Separación entre soldados.
- Prevención de bloqueos.
- Recuperación cuando una ruta no es accesible.

No implementes inicialmente un sistema de estrategia excesivamente sofisticado. Construye primero navegación y combate básicos confiables y después añade comportamiento táctico.

---

# 4. GAMEPLAY DEL COMANDANTE HUMANO

El comandante es el personaje principal.

### Características

1. Cámara en primera persona.
2. Movimiento libre por todo el mapa.
3. Capacidad para recibir daño.
4. Incapacidad de usar armas ofensivas.
5. Comunicación mediante proximidad.
6. Comunicación mediante walkie-talkie.
7. Interacción con terminales y elementos del escenario.
8. Interfaz para consultar pelotones, órdenes y estado de la batalla.

El comandante no combate directamente. Su efectividad depende de dar instrucciones adecuadas.

### 4.1. Comunicación por proximidad

Cuando el jugador habla normalmente:

- Se transmite la orden dentro de un radio configurable.
- Solo la reciben los NPC aliados suficientemente cercanos.
- El sistema debe reconocer a quién se dirige el jugador.
- Si se dirige claramente a un soldado o pelotón, solo ese destinatario responde.
- Si no identifica un destinatario, se puede inferir únicamente cuando el contexto sea inequívoco.

Debe existir retroalimentación si nadie puede escuchar la instrucción.

### 4.2. Comunicación por radio

El jugador puede activar un walkie-talkie mediante una tecla.

Todos los pelotones aliados conectados a esa red pueden recibir la transmisión, pero solamente ejecutará una orden el destinatario identificado.

Ejemplo:

"Pelotón Bravo, retrocedan a la base."

Aunque Alfa y Charlie reciban la transmisión, solamente Bravo debe obedecer.

El sistema debe impedir que una orden sin destinatario claro provoque movimientos simultáneos no deseados.

### 4.3. Salud del comandante

El comandante puede ser atacado, pero nunca debe disparar.

Como la condición de derrota principal es la destrucción de la base, si el comandante es incapacitado se puede implementar una penalización temporal y reaparición en la base.

La muerte del comandante no debe producir automáticamente la derrota.

---

# 5. SISTEMA DE SOLDADOS Y PELOTONES

## 5.1. Restricciones fundamentales

Cada bando puede disponer simultáneamente de:

- Máximo cinco pelotones activos.
- Máximo cinco soldados por pelotón.
- Máximo un pelotón médico activo.

Cada pelotón posee un identificador permanente durante su existencia.

Ejemplos:

- Alfa.
- Bravo.
- Charlie.
- Delta.
- Médico.

Los identificadores deben poder modificarse y sus alias deben ser comprendidos por el sistema NLP.

Un pelotón no necesariamente comienza con cinco miembros: debe soportar bajas y composición variable.

## 5.2. Estados de los soldados

Implementa una máquina de estados o StateTree para gestionar:

- Idle.
- FollowingOrder.
- Moving.
- TakingCover.
- Attacking.
- Defending.
- Retreating.
- Healing.
- Downed.
- Dead.

Los estados deben admitir interrupciones controladas.

Por ejemplo, un soldado que avanza puede buscar cobertura ante un ataque y posteriormente continuar su misión.

## 5.3. Combate

Los soldados aliados y enemigos deben poder:

- Detectar enemigos.
- Disparar.
- Recibir daño.
- Buscar cobertura.
- Defender una posición.
- Avanzar con precaución.
- Retirarse.
- Reagruparse.
- Solicitar asistencia médica.

Los sistemas de daño, armas y navegación deben ser compartidos por los dos bandos.

## 5.4. Incapacitación

Antes de morir definitivamente, los soldados pueden quedar incapacitados.

Durante un tiempo configurable, un médico puede reanimarlos.

Si el tiempo termina, el soldado muere definitivamente.

El estado de incapacitación debe ser visualmente identificable y registrarse en los sistemas de gestión de pelotones.

---

# 6. PELOTÓN MÉDICO

El pelotón médico tiene comportamientos especializados.

### Funcionalidades

- Buscar aliados heridos.
- Curar soldados.
- Reanimar incapacitados.
- Priorizar objetivos según gravedad.
- Evitar zonas de peligro cuando sea posible.
- Responder a órdenes del comandante.

Ejemplos:

"¡Médicos, vayan al centro!"

"¡Equipo médico, atiendan a Bravo en la izquierda!"

"¡Médicos, retrocedan a la base!"

El sistema debe resolver tanto la ubicación como el objetivo cuando la instrucción lo indique.

No puede existir un segundo pelotón médico activo simultáneamente.

---

# 7. SISTEMA DE REFUERZOS

En cada base existe una terminal de comunicaciones.

El jugador puede solicitar refuerzos cuando:

1. La terminal esté disponible.
2. No se haya superado el máximo de cinco pelotones.
3. No exista una solicitud de refuerzo en curso.
4. Haya finalizado el cooldown.

La solicitud debe generar un solo pelotón por operación.

El cooldown debe ser considerable y configurable, inicialmente alrededor de 120 segundos, sujeto a balance.

El comandante enemigo puede utilizar el mismo sistema.

La lógica de refuerzos debe residir en un componente independiente para reutilizarla entre ambos equipos.

---

# 8. NÚCLEO PRINCIPAL: ARQUITECTURA NLP

**Este es el apartado prioritario del proyecto.**

El sistema debe convertir expresiones naturales del jugador en acciones válidas dentro del juego.

Pipeline obligatorio:

Voz del jugador
→ Captura de audio
→ Detección de actividad vocal
→ Speech-to-Text
→ Normalización textual
→ Interpretación NLP
→ Extracción de intención y entidades
→ Generación de JSON
→ Validación semántica
→ Resolución de destinatario
→ Evento táctico
→ Ejecución NPC
→ Confirmación auditiva.

Todos los módulos deben poder probarse de manera individual.

## 8.1. Reconocimiento de voz

Utiliza una solución local como:

- whisper.cpp.
- faster-whisper.

Compara inicialmente modelos pequeños y cuantizados.

Prioriza:

- Español.
- Baja latencia.
- Ejecución local.
- Robustez frente a ruido ambiental.
- Compatibilidad con Unreal Engine.
- Consumo razonable de CPU y GPU.

Implementa Push-to-Talk como mecanismo principal para el MVP.

Si es viable, añade detección de actividad vocal mediante VAD.

El sistema debe evitar que el ruido de combate, la música o las voces de los NPC se interpreten incorrectamente como órdenes del jugador.

No asumas tiempos de procesamiento constantes: mide el rendimiento real.

## 8.2. Intenciones principales

El NLP debe reconocer inicialmente cuatro clases:

**ORDEN:** instrucción táctica para un soldado o pelotón.

**MOTIVACION:** discurso, ánimo o arenga dirigida a los soldados.

**CHARLA:** conversación contextual sin instrucción táctica. En el MVP puede reconocerse sin generar una respuesta conversacional.

**DESCONOCIDO:** expresiones fuera del dominio, confusas, incompletas o no suficientemente confiables.

Separar intención de ejecución es obligatorio.

## 8.3. Estructura de una orden

Formato central:

SUJETO + ACCIÓN + LUGAR.

El sujeto identifica al destinatario.

La acción pertenece a un catálogo de comportamientos implementados.

El lugar identifica una región del mapa.

Se permiten campos complementarios como objetivo, prioridad o duración cuando sean útiles.

Ejemplos:

"Alfa, avancen por el centro."

"Los de Bravo, aseguren el flanco izquierdo."

"Charlie, regresen a nuestra base."

"Médicos, ayuden a los soldados heridos en el centro."

El procesamiento debe reconocer sinónimos y variaciones coloquiales.

## 8.4. Catálogo inicial de acciones

Implementar como mínimo:

- avanzar
- defender
- atacar
- retirarse
- reagruparse
- patrullar
- explorar
- mantener_posicion
- cancelar_orden
- curar
- reanimar

Las acciones médicas solo deben ejecutarse por unidades capacitadas.

No todas las combinaciones sujeto-acción-lugar son válidas.

El NLP interpreta; el motor del juego verifica si una acción puede ejecutarse.

## 8.5. Esquema JSON unificado

Establece un contrato estricto para los dos modelos.

Ejemplo de interpretación:

{
  "intent": "orden",
  "subject": {
    "type": "peloton",
    "name": "Alfa"
  },
  "action": "avanzar",
  "location": {
    "id": "flanco_izquierdo"
  },
  "target": null,
  "model_confidence": 0.94
}

Este es un ejemplo del formato, no una predicción real.

El contexto de comunicación, identificador de petición y texto original deben adjuntarse mediante el sistema de integración, sin depender de que el modelo los invente.

Reglas:

1. La salida debe respetar un JSON Schema versionado.
2. Los valores de acciones y ubicaciones deben pertenecer a catálogos conocidos.
3. Los sujetos se resuelven contra entidades existentes en la partida.
4. Los campos ausentes o ambiguos deben representarse explícitamente.
5. Ningún JSON inválido debe ejecutarse.
6. Ninguna entidad inexistente debe recibir órdenes.
7. Una orden no ejecutable debe generar una respuesta explicativa.
8. El LLM no debe declarar una confianza numérica inventada: se utilizará null cuando no exista una estimación calibrada.
9. El texto generado nunca se interpretará como código ejecutable ni se utilizará para llamar funciones arbitrarias.

La validación final debe ser independiente del modelo NLP.

## 8.6. Interpretación contextual

No todas las instrucciones mencionan explícitamente todos los campos.

Ejemplos:

"Alfa, retrocedan."

"Bravo, quédense ahí."

"Muchachos, cubran esa entrada."

Se permite resolver referencias mediante el estado del juego cuando la interpretación sea inequívoca.

Si no existe suficiente información, el soldado debe solicitar aclaración.

Ejemplo:

"¿A qué flanco nos dirigimos, mi General?"

No inventes destinos ni sujetos cuando existan varias interpretaciones posibles.

## 8.7. Negaciones y órdenes contradictorias

Evaluar explícitamente expresiones como:

"Alfa, no avancen por el centro."

"Bravo, cancelen la orden anterior."

"Charlie, no retrocedan; defiendan su posición."

La primera expresión no debe convertirse accidentalmente en una orden de avanzar.

Si existen instrucciones contradictorias y no puede resolverse la intención, el sistema debe abstenerse de ejecutar una acción.

---

# 9. MODELO NLP A: MODELO PROPIO ENTRENADO DESDE CERO

Desarrolla un modelo pequeño mediante PyTorch.

**From scratch significa iniciar el entrenamiento con pesos aleatorios, sin cargar pesos lingüísticos preentrenados.**

El modelo debe aprender las representaciones necesarias a partir del dataset del proyecto.

## 9.1. Arquitectura propuesta

Implementa inicialmente:

- Tokenizador y vocabulario construidos con los datos de entrenamiento.
- Capa Embedding.
- Encoder BiGRU o arquitectura equivalente pequeña.
- Pooling o mecanismo simple de atención.
- Cabeza de clasificación de intención.
- Cabeza de clasificación de acción.
- Cabeza de clasificación de tipo de sujeto.
- Cabeza de extracción de entidades mediante etiquetado BIO, si el dataset lo permite.

Alternativamente, compara TextCNN como baseline neuronal.

El sujeto concreto y el lugar pueden extraerse mediante spans y normalizarse utilizando el catálogo del juego.

No dependas exclusivamente de una clasificación fija de nombres de pelotones, porque en el futuro pueden cambiar.

## 9.2. Entrenamiento

Implementa un pipeline reproducible:

1. Cargar dataset.
2. Validar etiquetas.
3. Normalizar texto.
4. Separar entrenamiento, validación y prueba.
5. Construir tokenizador y vocabulario exclusivamente con entrenamiento.
6. Crear Dataset y DataLoader.
7. Instanciar modelo.
8. Entrenar.
9. Evaluar por época.
10. Guardar el mejor checkpoint.
11. Evaluar sobre el conjunto de prueba reservado.
12. Exportar modelo y artefactos de preprocesamiento.

## 9.3. Buenas prácticas obligatorias

Aplicar y documentar:

**Regularización**
- Dropout.
- Weight decay.
- Early stopping.
- Control de sobreajuste.
- Gradient clipping.
- Label smoothing cuando proceda.
- Balanceo de clases si es necesario.

**Optimización**
- AdamW.
- Búsqueda razonada de learning rate.
- Batch sizes compatibles con el hardware.
- Entrenamiento en GPU si está disponible.
- Mixed precision cuando sea apropiado.
- Checkpointing.
- Reproducibilidad mediante semillas.

**Scheduling**
- Warmup de learning rate cuando sea útil.
- CosineAnnealingLR o ReduceLROnPlateau.
- Registrar el learning rate en cada época.

**Evaluación**
- Training loss.
- Validation loss.
- Accuracy.
- Precision.
- Recall.
- F1 macro.
- F1 por clase.
- F1 de extracción de entidades.
- Exact Match de órdenes completas.
- Matriz de confusión.
- Tiempos de inferencia.
- Calibración de confianza.

Si se utiliza una pérdida multiobjetivo, documenta la contribución y peso de cada cabeza de salida.

## 9.4. Prevención de overfitting

No incrementar artificialmente el rendimiento mediante duplicados o frases casi idénticas repartidas entre entrenamiento y prueba.

Las variantes procedentes de una misma plantilla deben agruparse antes de dividir el dataset.

La evaluación debe incluir expresiones nuevas y formas de hablar no observadas durante el entrenamiento.

---

# 10. MODELO NLP B: LLM LOCAL RESTRINGIDO

Implementa una segunda solución utilizando un modelo de lenguaje pequeño preentrenado.

Candidatos:

- Qwen2.5-1.5B-Instruct.
- Qwen2.5-3B-Instruct, si los recursos lo permiten.
- Alternativa pequeña equivalente con buen rendimiento en español.

La primera opción será una variante cuantizada compatible con llama.cpp.

## 10.1. Objetivo

El modelo recibe una frase y devuelve exclusivamente una interpretación estructurada compatible con el contrato JSON del videojuego.

Ejemplo:

Entrada:

"¡Los del Bravo, váyanse echando para atrás y cubran nuestra base!"

Salida esperada:

Intent: orden.

Sujeto: Bravo.

Acción: defender o retirarse, según la interpretación contextual y el catálogo de órdenes compuestas permitido.

Lugar: base_aliada.

Si la frase contiene varias órdenes, implementa una política explícita: procesarlas secuencialmente cuando sea seguro o solicitar aclaración. No reduzcas silenciosamente una instrucción múltiple a una acción arbitraria.

## 10.2. Restricciones

- Inferencia completamente local.
- Sin servicios de pago obligatorios.
- Sin necesidad de conexión durante una partida.
- Temperatura baja o decodificación determinista.
- Salida restringida mediante JSON Schema o gramática compatible.
- Catálogo cerrado de acciones.
- Contexto del juego suministrado explícitamente.
- Validación externa obligatoria.
- Sin ejecución directa de funciones generadas por el LLM.

Utiliza técnicas de prompting con ejemplos de órdenes válidas, inválidas y ambiguas.

No realices fine-tuning del LLM inicialmente. Se pretende comparar un modelo propio entrenado con una solución local preentrenada.

## 10.3. Gestión de recursos

La GPU puede estar ocupada renderizando Unreal Engine.

Evalúa:

- Inferencia en CPU.
- Inferencia parcial en GPU.
- Cuantización Q4 y otras variantes.
- Tiempo de precarga.
- Consumo de RAM y VRAM.
- Impacto en FPS.
- Latencia concurrente con el juego.

No fuerces una configuración que vuelva injugable el prototipo.

---

# 11. EXPERIMENTO ADICIONAL: TRANSFER LEARNING CON BETO

Si el tiempo disponible permite una tercera evaluación, incorpora un encoder ligero de español preentrenado.

Opciones:

- BETO.
- DistilBERT multilingüe.
- RoBERTa entrenado para español, según recursos y licencia.

Realiza fine-tuning supervisado para clasificación y extracción de entidades.

Es importante distinguir académicamente:

- Modelo desde cero: parámetros inicializados aleatoriamente.
- Fine-tuning: modelo preentrenado adaptado a nuevas etiquetas.
- LLM local restringido: modelo de instrucciones utilizado mediante prompting, sin reentrenamiento inicial.

Este experimento es opcional. Nunca debe retrasar la integración funcional de los dos modelos principales.

---

# 12. DATASETS NLP

Inspecciona primero `AI NLP/Data/`.

Determina:

- Cuántas frases existen.
- Idioma y variaciones.
- Estructura de etiquetas.
- Balance entre clases.
- Cobertura de acciones.
- Cobertura de sujetos.
- Cobertura de lugares.
- Presencia de expresiones ambiguas.
- Duplicados.
- Problemas de calidad.

## 12.1. Dataset objetivo

Tomar como referencia inicial entre 1.500 y 3.000 expresiones correctamente etiquetadas, ampliándolo si la evaluación lo exige.

No generar ejemplos solo para alcanzar una cantidad.

El dataset debe incluir:

- Órdenes directas.
- Órdenes informales.
- Sinónimos.
- Expresiones coloquiales.
- Frases extensas.
- Frases incompletas.
- Negaciones.
- Referencias ambiguas.
- Vocabulario militar.
- Conversaciones casuales.
- Discursos motivacionales.
- Frases fuera del dominio.
- Errores frecuentes de transcripción.

Incluir expresiones naturales de español latinoamericano, sin limitarse al español peninsular.

## 12.2. Etiquetado

Cada muestra debe registrar al menos:

- Texto.
- Intención.
- Sujeto, si existe.
- Acción, si existe.
- Lugar, si existe.
- Objetivo opcional.
- Indicador de ambigüedad.
- Identificador de plantilla o familia.
- Fuente o método de generación.

Para extracción de entidades, registrar spans y etiquetas correspondientes.

El canal de comunicación puede añadirse como contexto de evaluación, pero no debe confundirse con una característica obligatoriamente inferida desde el texto.

## 12.3. División del dataset

Utilizar como punto de partida:

- 70 % entrenamiento.
- 15 % validación.
- 15 % prueba.

Separar por familias de expresiones, evitando fuga de información.

Crear un subconjunto adicional de expresiones reales recogidas de hablantes, cuando sea posible.

El conjunto de prueba debe permanecer congelado hasta la evaluación final.

## 12.4. Generación sintética

Se permite generar ejemplos mediante reglas o LLM para acelerar el etiquetado.

Sin embargo:

- Revisar la validez de los ejemplos.
- Evitar duplicados.
- Detectar etiquetas inconsistentes.
- Asegurar diversidad lingüística.
- Revisar manualmente muestras aleatorias.
- Guardar la procedencia de los datos.
- No reutilizar plantillas de entrenamiento dentro de pruebas reservadas.

El dataset sintético no sustituye una evaluación con voz real.

---

# 13. COMPARACIÓN EXPERIMENTAL DE LOS MODELOS

Ambos modelos deben recibir exactamente el mismo conjunto de pruebas textuales.

La comparación principal se realizará entre:

A. Modelo neuronal propio entrenado desde cero.

B. LLM local cuantizado.

C. BETO fine-tuneado, solamente si se implementa.

## 13.1. Métricas

Evaluar:

1. Exactitud de clasificación de intención.
2. Exactitud de acción.
3. Exactitud de sujeto.
4. Exactitud de lugar.
5. F1 de entidades.
6. Exact Match del JSON semántico.
7. Tasa de ejecuciones incorrectas.
8. Tasa de abstenciones correctas.
9. Latencia mediana.
10. Latencia p95.
11. Memoria RAM.
12. Memoria VRAM.
13. Impacto sobre FPS.
14. Robustez frente a frases no vistas.

La prioridad no será solamente identificar correctamente una intención, sino interpretar íntegramente una orden válida sin provocar acciones equivocadas.

## 13.2. Experimentos y ablación

Para el modelo entrenado desde cero, comparar cuando sea posible:

- Con dropout y sin dropout.
- Con scheduler y sin scheduler.
- Adam frente a AdamW, si los recursos lo permiten.
- Diferentes tasas de aprendizaje.
- Diferentes tamaños de embeddings.
- Diferentes cantidades de datos.
- Con y sin aumento de datos.

No realizar experimentos interminables. Seleccionar aquellos que permitan explicar técnicamente el rendimiento del modelo.

## 13.3. Evaluación end-to-end

Separar los errores de cada componente:

- Errores de transcripción.
- Errores de interpretación NLP.
- Errores de validación.
- Errores de resolución del destinatario.
- Errores de ejecución en Unreal Engine.

No atribuir al NLP errores que se originan en navegación o reconocimiento de voz.

Registrar latencia de cada etapa y latencia total.

Establecer objetivos medibles de calidad, pero nunca presentar cifras previstas como resultados experimentales.

---

# 14. DETECCIÓN DE CHARLAS MOTIVACIONALES

Este es el segundo componente NLP obligatorio.

El sistema debe distinguir una arenga real de una conversación cotidiana.

Ejemplos:

"¡Vamos, soldados, hoy vamos a demostrar de qué estamos hechos!"

"¡Confío en ustedes, muchachos, ganaremos esta batalla!"

"¡No se rindan, somos el mejor ejército del mundo!"

Las frases deben interpretarse semánticamente, no solamente mediante una lista de palabras como "ganar" o "vamos".

## 14.1. Efectos

Cuando se detecta correctamente una charla motivacional:

- Aplicar un estado temporal de motivación.
- Incrementar moderadamente el rendimiento táctico.
- Mostrar una señal visual clara.
- Reproducir reacciones de los soldados.
- Activar un cooldown considerable.

Posibles modificaciones:

- Mejor resistencia a la supresión.
- Recuperación más rápida de moral.
- Ligera mejora de velocidad.
- Menor demora al reaccionar a órdenes.

Los porcentajes, duración y cooldown serán configurables.

Evitar efectos acumulativos infinitos.

## 14.2. Destinatarios

En comunicación por proximidad, el efecto alcanza solamente a soldados que puedan escuchar al comandante.

Por radio, puede alcanzar a los destinatarios explícitos o a las unidades aliadas de una arenga general válida, según reglas claras.

El sistema debe reconocer cuándo una frase motivacional está dirigida a soldados y cuándo es una expresión casual.

## 14.3. Retroalimentación

Ejemplos de respuestas humorísticas:

"¡Por usted y por el almuerzo, mi General!"

"¡Ahora sí me siento invencible!"

"¡No prometo sobrevivir, pero voy con ganas!"

La retroalimentación visual puede incluir un aura moderada, iconos de moral o animaciones breves.

---

# 15. CHARLA CONTEXTUAL: FUNCIÓN FUTURA

La conversación libre entre el comandante y los soldados no forma parte del núcleo obligatorio.

Diseña una interfaz extensible para incorporar posteriormente un modelo conversacional local.

El reconocimiento de la intención CHARLA sí debe existir desde el inicio.

En el MVP, las frases de charla pueden recibir respuestas breves predefinidas o no producir cambios tácticos.

No consumas recursos significativos implementando diálogos generativos antes de completar órdenes y motivación.

---

# 16. CONFIRMACIÓN AUDITIVA Y MANEJO DE ERRORES

Toda orden debe generar retroalimentación.

Ejemplos:

**Orden aceptada:**

"¡Copiado, Alfa avanzando por la izquierda!"

**Orden incompleta:**

"¡Mi General, indique el destino!"

**Destinatario inexistente:**

"¡No encontramos al pelotón indicado!"

**Acción inválida:**

"¡Señor, esa unidad no puede realizar esa tarea!"

**Interpretación poco confiable:**

"¡Interferencia en la radio, repita la orden, mi General!"

Utiliza inicialmente un umbral configurable cercano a 0.70 cuando exista una confianza calibrada.

No consideres automáticamente confiable la salida de un LLM por ser JSON válido.

Implementa validación semántica y abstención segura.

Debe poder consultarse el historial reciente de órdenes y sus resultados.

---

# 17. IA DEL COMANDANTE ENEMIGO

La IA enemiga será **100 % algorítmica en la primera versión**.

No implementar Reinforcement Learning para el comandante enemigo.

Utilizar:

- Heurísticas.
- Máquinas de estados.
- Blackboard.
- Behavior Trees o StateTree.
- Tácticas predefinidas.
- Decisiones basadas en información parcial.

El propósito es conseguir un enemigo competente sin desviar recursos de la investigación NLP.

## 17.1. Percepción

Cada soldado enemigo tendrá:

- Campo de visión.
- Radio de audición.
- Detección de amenazas.
- Reconocimiento de aliados y enemigos.

Los disparos, explosiones y movimientos ruidosos pueden generar información táctica.

No otorgar conocimiento omnisciente al comandante enemigo.

## 17.2. Memoria táctica

El comandante mantiene una pizarra de inteligencia.

Ejemplo:

Pelotón Alfa detectado en flanco derecho hace 8 segundos.

La información debe registrar:

- Ubicación reportada.
- Fuente.
- Tiempo de detección.
- Tipo de unidad.
- Confianza.
- Estado de actualización.

Si se pierde contacto visual o no llegan nuevos reportes, la certeza debe disminuir progresivamente.

Esto permitirá engaños, maniobras de distracción y emboscadas.

## 17.3. Sistema scouting

Los enemigos pueden enviar exploradores.

La información se actualiza mediante:

- Contacto visual de unidades.
- Reportes transmitidos por exploradores.

Si un explorador es eliminado antes de transmitir su información, el comandante no puede utilizar ese conocimiento.

La comunicación debe respetar las reglas implementadas para transmisión y alcance.

## 17.4. Tácticas predefinidas

Implementar al menos cinco tácticas.

**Táctica 1: Asalto frontal**

Concentra tres pelotones en el centro y mantiene dos defendiendo la base.

**Táctica 2: Pinza lateral**

Envía unidades por los flancos mientras otra mantiene una distracción en el centro.

**Táctica 3: Empuje pesado**

Concentra el ejército en el flanco aparentemente más débil.

**Táctica 4: Cebo y emboscada**

Simula una retirada y utiliza tropas ocultas para atacar a perseguidores.

**Táctica 5: Defensa elástica**

Distribuye tropas entre los flancos y conserva reservas para reforzar posiciones.

Cada táctica debe funcionar también con menos de cinco pelotones, mediante variantes o asignaciones reducidas.

Nunca intentes asignar unidades inexistentes.

## 17.5. Personalidades

Cada partida selecciona una personalidad para el comandante rival.

**Agresivo**

Prefiere ataques rápidos, concentración de fuerzas y presión continua.

**Calculador**

Prioriza defensa, información reciente, reservas y contraataques.

**Engañoso**

Utiliza exploradores, distracciones, cambios de flanco y emboscadas.

La personalidad debe influir realmente sobre la evaluación de tácticas, no ser solamente una etiqueta decorativa.

## 17.6. Ciclo de decisiones

Implementar una evaluación estratégica aproximadamente cada 15-20 segundos.

El comandante deberá:

1. Consultar inteligencia disponible.
2. Revisar la táctica actual.
3. Evaluar bajas y progreso.
4. Identificar amenazas.
5. Mantener o cambiar estrategia.
6. Solicitar refuerzos cuando corresponda.

La lógica de cambio debe evitar oscilaciones continuas.

El comandante solamente puede modificar sus decisiones con información legítimamente conocida o heurísticas generales.

## 17.7. Refuerzos enemigos

Si quedan menos de tres pelotones activos y la terminal de refuerzos está disponible, podrá solicitar uno nuevo.

La operación debe respetar exactamente las mismas restricciones del jugador.

---

# 18. ARQUITECTURA DE SOFTWARE EN UNREAL ENGINE

Implementar una arquitectura modular y desacoplada.

Priorizar C++ para la lógica central y Blueprints para configuración, UI y presentación cuando resulte conveniente.

### Subsistemas propuestos

**VoiceCaptureSubsystem**

Captura, normalización y segmentación de audio.

**SpeechToTextService**

Transcripción local de voz.

**NLPInferenceService**

Interfaz común para seleccionar Modelo A o Modelo B.

**CommandInterpreter**

Conversión de resultados a órdenes normalizadas.

**CommandValidationSubsystem**

Verificación del JSON, catálogo y estado del mundo.

**TacticalCommandBus**

Publicación de eventos tácticos.

**SquadManager**

Gestión de pelotones y miembros.

**TacticalAIController**

Ejecución de órdenes y estados tácticos.

**EnemyCommanderAI**

Selección de tácticas basada en personalidad e inteligencia.

**EnemyIntelligenceSubsystem**

Blackboard de información enemiga y memoria temporal.

**ReinforcementSubsystem**

Gestión de solicitudes y cooldown.

**MoraleSubsystem**

Detección de buffs y aplicación de efectos.

**BattleGameMode**

Reglas de partida, victoria y derrota.

Los nombres son propuestas y pueden adaptarse a convenciones del proyecto existente.

## 18.1. Event Bus compartido

Esta regla es fundamental:

**Tanto las órdenes generadas por NLP como las órdenes del comandante enemigo deben utilizar el mismo contrato táctico.**

Ejemplo conceptual:

OrdenTactica(Sujeto, Accion, Lugar, ObjetivoOpcional)

La diferencia estará únicamente en quién genera la orden.

Después, los dos bandos utilizarán el mismo sistema de ejecución.

Esto evita duplicaciones y permite comprobar que una acción funciona independientemente del origen de la orden.

## 18.2. Conexión de los modelos

Durante desarrollo, se permite utilizar un servicio local independiente para ejecutar NLP.

Debe existir una interfaz de inferencia intercambiable.

Para el modelo propio, evaluar exportación ONNX.

Para el LLM, utilizar llama.cpp.

Para la integración final, comparar un servicio local con inferencia integrada en el proceso de Unreal, sin asumir que todas las versiones y backends poseen las mismas capacidades.

No bloquear el hilo principal del videojuego durante transcripción o inferencia.

Implementar tareas asíncronas y devolver los resultados al hilo apropiado para interactuar con objetos de Unreal.

Usar identificadores de solicitudes para evitar ejecutar respuestas antiguas o duplicadas.

## 18.3. Seguridad funcional

El modelo NLP nunca debe controlar directamente los NPC.

Debe emitir únicamente una propuesta de orden estructurada.

El sistema determinista debe verificar:

- Destinatario válido.
- Acción permitida.
- Lugar existente.
- Alcance de comunicación.
- Estado del pelotón.
- Permisos de ejecución.
- Recursos disponibles.
- Ausencia de contradicciones.
- Vigencia temporal de la solicitud.

Las órdenes no autorizadas deben rechazarse con una razón explicable.

---

# 19. INTERFAZ DEL VIDEOJUEGO

Diseñar una interfaz clara, funcional y acorde con una estética militar humorística.

## 19.1. HUD principal

Mostrar:

- Salud del comandante.
- Estado de la base.
- Estado de pelotones.
- Canal de comunicación activo.
- Estado del micrófono.
- Última orden reconocida.
- Confirmaciones de ejecución.
- Cooldown de refuerzos.
- Cooldown de motivación.

## 19.2. Mapa táctico

Incorporar un mapa sencillo o minimapa donde se visualicen:

- Bases.
- Tres flancos.
- Pelotones aliados.
- Enemigos detectados legítimamente.
- Objetivos tácticos.
- Órdenes activas.

No revelar automáticamente unidades enemigas ocultas.

## 19.3. Panel de depuración NLP

Debe existir un modo de depuración activable para presentar:

- Texto reconocido por Speech-to-Text.
- Modelo NLP seleccionado.
- Intención detectada.
- Sujeto.
- Acción.
- Lugar.
- JSON generado.
- Resultado de validación.
- Tiempo STT.
- Tiempo NLP.
- Latencia total.
- Estado de ejecución.

Esta interfaz será esencial durante la defensa académica.

---

# 20. DIRECCIÓN ARTÍSTICA Y HUMOR

El juego debe ser divertido y expresivo, evitando que su estilo caricaturesco reduzca la claridad de la estrategia.

Incorporar progresivamente:

- Soldados con expresiones exageradas.
- Respuestas humorísticas de radio.
- Animaciones de celebración.
- Reacciones al recibir órdenes extrañas.
- Diferentes personalidades vocales.
- Mensajes absurdos ocasionales durante situaciones de combate.

Ejemplo:

Comandante: "¡Alfa, defiendan la base!"

Soldado: "¡Entendido, señor! ¡Esta vez no vamos a salir corriendo!"

El humor no debe alterar la validación ni interpretación real de las órdenes.

Usar inicialmente los assets disponibles. Si falta contenido artístico, emplear placeholders claramente identificados.

No invertir más tiempo en efectos gráficos que en el sistema NLP hasta completar el MVP.

---

# 21. ESTRUCTURA PROPUESTA DEL REPOSITORIO

Organizar el proyecto de manera que el código de IA pueda mantenerse independientemente del juego.

Estructura conceptual:

YellCommander/
- UnrealProject/
  - Source/
  - Content/
  - Config/
  - Plugins/
- AI_NLP/
  - data/
    - raw/
    - processed/
    - synthetic/
    - evaluation/
  - models/
    - scratch/
    - local_llm/
    - finetuned_encoder_optional/
  - training/
  - inference/
  - evaluation/
  - exports/
  - configs/
  - tests/
- Documentation/
  - architecture/
  - gameplay/
  - datasets/
  - experiments/
  - results/
  - bitacora/
- References/
- Assets/
- Scripts/
- README.md

Adaptar esta estructura cuando ya exista un proyecto organizado.

No mover archivos críticos indiscriminadamente.

Separar pesos descargables, datasets, configuraciones, código y resultados.

Excluir del control de versiones archivos temporales o modelos demasiado grandes, proporcionando instrucciones reproducibles para obtenerlos.

---

# 22. PRUEBAS OBLIGATORIAS

## 22.1. Unitarias

Probar:

- Normalización de texto.
- Extracción de entidades.
- Serialización JSON.
- Validación de órdenes.
- Resolución de destinatarios.
- Aplicación de cooldowns.
- Límites de pelotones.
- Activación y expiración de efectos.
- Manejo de solicitudes duplicadas.

## 22.2. Integración

Comprobar:

- Audio a texto.
- Texto a NLP.
- NLP a JSON.
- JSON a evento.
- Evento a NPC.
- NPC a confirmación.

## 22.3. Casos de prueba funcionales

**Caso 1:** Dar una orden válida a Alfa por radio. Solamente Alfa debe responder.

**Caso 2:** Dar una orden a un pelotón fuera del alcance de proximidad. No debe ejecutarse.

**Caso 3:** Dar una orden ambigua. Debe solicitarse aclaración.

**Caso 4:** Pronunciar un discurso motivacional. Aplicar correctamente el buff.

**Caso 5:** Repetir una motivación durante el cooldown. No aplicar otro buff.

**Caso 6:** Solicitar un sexto pelotón. Debe rechazarse.

**Caso 7:** Intentar generar un segundo pelotón médico. Debe rechazarse.

**Caso 8:** Incapacitar un soldado y reanimarlo con médicos. Debe volver a un estado funcional.

**Caso 9:** Destruir una base. La partida debe finalizar correctamente.

**Caso 10:** El enemigo pierde un explorador antes de transmitir. No debe adquirir información que ese explorador no reportó.

**Caso 11:** Cambiar entre los dos modelos NLP. Ambos deben producir órdenes compatibles con el mismo ejecutor.

**Caso 12:** Introducir una frase fuera del dominio. Ninguna unidad debe ejecutar una orden inventada.

**Caso 13:** Enviar instrucciones con negaciones. No debe ejecutarse la acción negada.

**Caso 14:** Simular ruido o una transcripción defectuosa. Debe evitarse la ejecución de acciones de baja fiabilidad.

**Caso 15:** Ejecutar NLP mientras existe combate. No debe bloquearse el hilo de renderizado.

---

# 23. OPTIMIZACIÓN Y RENDIMIENTO

El videojuego debe ejecutar simultáneamente:

- Renderizado 3D.
- Comportamiento de NPC.
- Navegación.
- Física.
- Procesamiento de audio.
- Reconocimiento de voz.
- NLP.
- IA estratégica enemiga.

Optimiza la arquitectura para evitar competencia innecesaria entre los subsistemas.

Implementa:

- Procesamiento asíncrono.
- Precarga de modelos.
- Reutilización de sesiones de inferencia.
- Cuantización.
- Control de uso de memoria.
- Frecuencia de actualización ajustable para la IA.
- Profiling del Game Thread.
- Análisis de cuellos de botella.
- Medición de FPS y latencia de comandos.

No infieras automáticamente que un modelo pequeño será rápido mientras Unreal Engine utiliza la GPU.

Realiza mediciones en el hardware real.

Documenta el equipo, la versión de motor, los backends y los parámetros utilizados.

---

# 24. PLAN DE DESARROLLO POR FASES

Desarrollar siguiendo este orden de prioridad.

## Fase 0: Auditoría y diseño

- Inspeccionar archivos.
- Estudiar documentación.
- Identificar recursos.
- Elaborar arquitectura.
- Definir catálogo de órdenes.
- Definir JSON Schema.
- Configurar repositorio.

**Entregable:** arquitectura documentada y proyecto preparado.

## Fase 1: Prototipo NLP textual

- Revisar dataset.
- Completar etiquetado.
- Entrenar Modelo A.
- Configurar Modelo B.
- Crear inferencia textual.
- Implementar validación JSON.
- Medir resultados iniciales.

**Entregable:** dos sistemas capaces de interpretar frases desde una consola de prueba.

## Fase 2: Voz y comunicación

- Integrar Speech-to-Text.
- Implementar Push-to-Talk.
- Detectar canal de comunicación.
- Procesar órdenes por voz.
- Generar confirmaciones.
- Evaluar latencia.

**Entregable:** órdenes por voz interpretadas correctamente con registros verificables.

## Fase 3: Vertical slice de Unreal Engine

Crear un mapa sencillo con:

- Dos bases.
- Tres flancos.
- Comandante en primera persona.
- Al menos dos pelotones.
- Movimiento y órdenes reales.
- Combate elemental.
- Interfaz de depuración.

**Entregable:** prototipo jugable donde una frase modifica realmente el comportamiento del pelotón.

## Fase 4: Mecánicas completas

- Hasta cinco pelotones.
- Médicos.
- Incapacitación.
- Reanimación.
- Refuerzos.
- Estados tácticos.
- Cobertura.
- Motivación.
- Victoria y derrota.

**Entregable:** partida jugable contra unidades enemigas.

## Fase 5: Comandante enemigo

- Inteligencia táctica.
- Percepción.
- Scouting.
- Memoria.
- Tácticas.
- Personalidades.
- Refuerzos.
- Decisiones periódicas.

**Entregable:** partida contra un comandante enemigo autónomo.

## Fase 6: Evaluación científica

- Pruebas comparativas.
- Métricas NLP.
- Evaluación end-to-end.
- Gráficas.
- Confusion matrices.
- Ablation studies.
- Perfilado.
- Discusión de resultados.

**Entregable:** informe experimental reproducible.

## Fase 7: Pulido y presentación

- Mejorar interfaz.
- Integrar assets.
- Refinar humor.
- Corregir errores.
- Optimizar.
- Preparar demostración.
- Elaborar documentación final.

**Entregable:** proyecto defendible académicamente y demostración funcional.

---

# 25. PRIORIDADES DE IMPLEMENTACIÓN

Clasifica los requisitos.

**P0 — Imprescindibles**

- Procesamiento NLP.
- Dos enfoques comparables.
- Entrenamiento reproducible.
- Órdenes estructuradas en JSON.
- Voz a texto.
- Validación de comandos.
- Unidades que ejecutan acciones.
- Integración funcional con Unreal.
- Registro y evaluación experimental.

**P1 — Gameplay completo**

- Tres flancos.
- Cinco pelotones.
- Combate.
- Médicos.
- Refuerzos.
- Motivación.
- IA enemiga algorítmica.
- Condición de victoria.
- Confirmaciones auditivas.

**P2 — Ampliaciones**

- Charla contextual generativa.
- Multijugador PvP.
- Animaciones avanzadas.
- Personalización de unidades.
- Escenarios adicionales.
- Mejores efectos y audio.

La prioridad P0 nunca debe sacrificarse para implementar funcionalidades P2.

---

# 26. BITÁCORAS E INFORMES DE DESARROLLO

Crear y mantener un sistema de documentación continua.

Cada funcionalidad implementada debe tener registro de:

- Fecha y fase.
- Objetivo.
- Archivos modificados.
- Diseño realizado.
- Implementación.
- Dependencias.
- Pruebas ejecutadas.
- Resultados.
- Problemas.
- Limitaciones.
- Trabajo pendiente.

Mantener archivos como:

- `Documentation/bitacora/CHANGELOG.md`
- `Documentation/bitacora/IMPLEMENTATION_STATUS.md`
- `Documentation/experiments/TRAINING_LOG.md`
- `Documentation/experiments/MODEL_COMPARISON.md`
- `Documentation/results/TEST_RESULTS.md`
- `Documentation/architecture/SYSTEM_DESIGN.md`

Registrar las configuraciones de entrenamiento, versiones, semillas y resultados.

Nunca reportar una funcionalidad como terminada únicamente porque el código fue escrito. Debe haberse probado.

No inventar resultados de entrenamiento, tiempos, capturas ni validaciones.

---

# 27. CRITERIOS DE ACEPTACIÓN

El proyecto se considerará funcional cuando se pueda demostrar lo siguiente:

1. El jugador inicia una partida en primera persona.
2. Existen dos bases y tres rutas navegables.
3. Los soldados pueden moverse y combatir.
4. El jugador puede emitir órdenes mediante micrófono.
5. El Speech-to-Text transcribe las órdenes en español.
6. Dos enfoques de NLP interpretan las instrucciones.
7. El usuario puede seleccionar el modelo activo.
8. Los modelos producen estructuras compatibles con el mismo JSON Schema.
9. Un validador revisa las órdenes antes de ejecutarlas.
10. Los pelotones obedecen solamente las instrucciones dirigidas a ellos.
11. Los soldados confirman las órdenes.
12. Las charlas motivacionales producen un efecto temporal.
13. Existe una IA enemiga que selecciona tácticas autónomamente.
14. Se respetan los límites de pelotones, médicos y refuerzos.
15. Es posible ganar o perder mediante destrucción de bases.
16. Existe un panel que permite observar todo el pipeline NLP.
17. Los resultados experimentales muestran el rendimiento real de ambos modelos.
18. El código y los experimentos pueden reproducirse siguiendo la documentación.

Si algún requisito permanece incompleto, registrarlo expresamente.

---

# 28. PRESENTACIÓN ACADÉMICA

El resultado debe permitir demostrar claramente los conceptos aprendidos en Inteligencia Artificial II.

Preparar evidencia de:

**Procesamiento del lenguaje natural**
- Tokenización.
- Representaciones vectoriales.
- Clasificación.
- Extracción de entidades.
- Comprensión de intenciones.
- Generalización ante sinónimos y frases nuevas.

**Deep Learning**
- Arquitectura de red.
- Entrenamiento supervisado.
- Funciones de pérdida.
- Regularización.
- Optimizadores.
- Scheduling.
- Early stopping.
- Evaluación y generalización.

**Comparación de modelos**
- Entrenamiento desde cero.
- Modelo preentrenado utilizado localmente.
- Transfer learning opcional.
- Exactitud.
- Latencia.
- Memoria.
- Robustez.

**Integración**
- Voice input.
- Speech-to-Text.
- Inferencia NLP.
- JSON.
- Sistemas basados en reglas.
- IA de NPC.
- Motor de videojuegos.

Además, preparar una demostración reproducible donde se ejecuten varias órdenes en vivo, se identifique el modelo que interpretó cada una y se observe la reacción correspondiente.

---

# 29. INSTRUCCIONES DE TRABAJO PARA EL AGENTE

Trabaja de forma incremental, técnica y verificable.

1. Primero examina lo existente.
2. Después presenta una arquitectura concreta y un backlog priorizado.
3. Implementa un vertical slice funcional lo antes posible.
4. Entrena y evalúa modelos reales, no simulaciones de inferencia.
5. No sustituyas permanentemente NLP por expresiones regulares.
6. Puedes utilizar reglas solamente para validación, normalización, resolución contextual y baseline.
7. Evita sobreingeniería y dependencias innecesarias.
8. Prioriza compatibilidad y rendimiento.
9. Emplea código modular, tipado, documentado y testeable.
10. Documenta decisiones arquitectónicas importantes.
11. Conserva checkpoints y artefactos de evaluación.
12. No ocultes errores ni declares pruebas satisfactorias si no se ejecutaron.
13. Mantén actualizada la bitácora.
14. Ante bloqueos técnicos, implementa una alternativa funcional compatible con la arquitectura y documenta las diferencias.
15. No implementes funcionalidades opcionales antes de completar los requisitos principales.

**Comienza con la auditoría del proyecto, el diseño del contrato JSON, la revisión del dataset y una primera prueba de inferencia NLP textual. Después avanza hacia la integración con la voz y Unreal Engine 5.**

## OBJETIVO FINAL IRRENUNCIABLE

El resultado principal no es simplemente un videojuego de soldados.

Es demostrar que un modelo de inteligencia artificial puede **comprender expresiones naturales en español, transformarlas en órdenes estructuradas y producir comportamientos inteligentes y verificables dentro de un entorno interactivo en tiempo real**.

Toda decisión técnica debe contribuir a que ese proceso sea preciso, eficiente, medible, extensible y funcional.