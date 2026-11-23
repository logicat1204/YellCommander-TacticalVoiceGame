# Arquitectura de Yell Commander

## Procesamiento de una orden

1. Unreal registra la frase escrita o los fotogramas de micrófono mientras se mantiene V. Conserva el canal y el origen del inicio de la pulsación. El búfer acepta una discontinuidad en el primer paquete, cancela ante un corte posterior y convierte una toma válida en WAV PCM mono.
2. El backend de loopback utiliza Whisper Base con VAD y filtros de silencio y confianza acústica. Python precarga el motor de transcripción si se configura la voz. El servicio llama al intérprete de órdenes cuando la transcripción supera estos filtros.
3. A usa una BiGRU en PyTorch con pesos aleatorios, embeddings de tokens y trigramas del corpus de entrenamiento. Las cabezas predicen intención, acción, presencia de sujeto y BIO. B llama por loopback a Qwen 1.5B Q4_K_M mediante llama.cpp, con temperatura cero y gramática JSON. C usa DistilBERT en español con ajuste fino supervisado y se activa con `-Transfer`.
4. Los tres generan `AI NLP/Data/command-v1.schema.json`. B acota la gramática según los nombres y lugares mencionados y las combinaciones permitidas. Un filtro externo vuelve a comprobar el catálogo y se abstiene ante negaciones e instrucciones múltiples. A aplica el umbral 0,70 a la menor de las probabilidades calibradas de intención y acción. B declara confianza nula. Como Qwen produjo acciones semánticamente erróneas en la prueba, el servicio de partida envía una orden o arenga de B solo si A coincide. Los evaluadores de consola miden cada modelo por separado.
5. Al completar el HTTP asíncrono, Unreal vuelve a validar el tipo y catálogo de los campos, además de comprobar el id, vigencia, canal, alcance, disponibilidad de pelotón, aptitud médica y navegación. Una retirada sin destino explícito vuelve a la base. Las órdenes de movimiento requieren ubicación.
6. `FYellTacticalEvent` comunica órdenes de ambos bandos al mismo ejecutor. El HUD muestra el resultado, el canal y el modelo. Unreal guarda las etapas en JSONL y reproduce una réplica corta en español de aprobación, aclaración o moral cuando hay audio.

El contrato admite pelotones e indicativos individuales, como `Alfa-2`. Unreal envía al servicio los nombres que existen en la sesión. Las selecciones con varios destinatarios tácticos requieren repetir la orden por separado.

## Mundo y partida

Valle Alfa genera tres carriles, cruces, terminales, coberturas y dos núcleos sobre un mapa dedicado. Unreal construye Recast NavMesh dinámicamente. Los soldados de ambos equipos usan controladores de IA, metas por formación, evitación y estados de acción. La salud, el daño y los tiempos son reglas de simulación del juego. La incapacitación del comandante activa reaparición y la destrucción de un núcleo decide el resultado.

El comandante rival tiene cinco configuraciones de órdenes, tres perfiles y un ciclo de 17 segundos. La visión requiere cono y línea libre, la audición de los efectos de combate usa un radio de juego y los reportes caducan. Los exploradores esperan tres segundos antes de reportar. Un explorador incapacitado en ese intervalo pierde el reporte pendiente. El minimapa del jugador filtra los contactos rivales por observaciones aliadas.

Los refuerzos comparten límites y cooldown por equipo. La motivación dura 18 s, aumenta velocidad y reduce daño recibido. Dura menos que su cooldown de 50 s. Los médicos atienden a compañeros heridos y reaniman incapacitados dentro de la ventana de recuperación.

## Prioridades y extensión

| Prioridad | Estado de diseño |
|---|---|
| P0 NLP, voz y Unreal | Contrato v1, adaptadores, entrenamiento, servidor y telemetría |
| P1 Juego | Navegación, pelotones, médicos, refuerzos, moral, rival algorítmico y final de partida |
| P2 Pulido | Importación de los modelos externos, animación, locución de personajes, terreno final, multijugador y charla contextual |

Las reglas de navegación actuales usan Recast con recuperación local. Las zonas de coste dinámico y un sistema de supresión completo quedan como ampliaciones. Los dibujos de los efectos de combate son marcadores de prototipo.
