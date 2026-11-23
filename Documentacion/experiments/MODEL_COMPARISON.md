# Comparación experimental de los modelos

Se evaluaron las mismas 172 frases reservadas para ambos modelos. El conjunto incluye 159 órdenes, 4 arengas, 4 comentarios y 5 ejemplos fuera del dominio. Las cifras corresponden a familias sintéticas y a una corrida por configuración. La coincidencia exacta compara intención, sujeto, acción, lugar y objetivo.

| Métrica | A · BiGRU | B · Qwen 1.5B Q4_K_M |
|---|---:|---:|
| Coincidencia exacta de la propuesta inicial | 30,8 % | 31,4 % |
| Coincidencia exacta tras validación del servicio de evaluación | 12,2 % | 30,2 % |
| Coincidencia exacta de las 159 órdenes | 8,8 % | 28,9 % |
| F1 macro de intención tras validación | 23,3 % | 37,9 % |
| F1 de entidades normalizadas tras validación | 20,5 % | 84,0 % |
| Propuestas tácticas incorrectas tras validación | 2,3 % | 44,2 % |
| Abstenciones correctas fuera del dominio | 5 de 5 | 2 de 5 |
| Latencia NLP mediana / p95 | 1,12 / 2,59 ms | 2.120 / 3.065 ms |

El umbral 0,70 de A mejora la abstención y reduce la cantidad de órdenes ejecutables. B no reporta confianza. La versión inicial del esquema general produjo 127 respuestas que incumplían reglas entre campos. Se repitió la prueba con una gramática que acota nombres, ubicaciones y combinaciones permitidas. La segunda corrida produjo 0 respuestas estructuralmente inválidas. El cambio se realizó después de diagnosticar la primera corrida y la segunda lectura del conjunto debe tratarse como exploratoria.

El alto número de acciones válidas con significado erróneo de Qwen motivó una comprobación adicional en partida. Para las órdenes y arengas cuya propuesta viene de B, el servicio exige acuerdo con la BiGRU después de aplicar el umbral. Al reproducir esta comprobación sobre las predicciones guardadas se rechazaron 129 propuestas de orden o arenga de B. Pasaron 5 de las 159 órdenes correctas y 0 propuestas tácticas incorrectas en este conjunto. Se documenta el compromiso de cobertura por separado de la comparación individual.

Se exportó la red de A a ONNX con opset 17 y lote fijo de 1. ONNX Runtime CPU se comparó con PyTorch en cuatro entradas. La mayor diferencia absoluta de logits fue 0,00000286. La partida usa el servicio PyTorch.

## Registros

- [Evaluación A por frase](../results/evaluation-A.json)
- [Evaluación B por frase](../results/evaluation-B.json)
- [Evaluación de B con el esquema general anterior](../results/evaluation-B-esquema-global.json)
- [Simulación del acuerdo aplicado en partida](../results/evaluation-B-acuerdo.json)
- [Curvas y matrices de confusión](../results/evaluacion-textual.png)
- [Paridad de ONNX](../results/onnx.json)
