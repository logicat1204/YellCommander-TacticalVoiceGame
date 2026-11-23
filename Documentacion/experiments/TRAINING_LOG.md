# Entrenamiento de la BiGRU

Se usó Python 3.14.3 con PyTorch 2.10.0 CPU en Windows 11, Intel Core i5-13420H y 16 GB de RAM. El entrenamiento arrancó desde parámetros aleatorios con semilla 421. El generador utiliza las semillas 2026 y 421. El vocabulario se construye solo con el conjunto de entrenamiento. Las muestras derivadas del enunciado se usan como frases de demostración y están en entrenamiento.

El modelo recibe embeddings de 48 dimensiones, compuestos por token y trigramas de caracteres, y usa dos sentidos GRU de 56 unidades cada uno con max pooling en la secuencia válida. Predice intención, acción, presencia de sujeto y etiquetas BIO. Los pesos en la pérdida compuesta son 1,1, 1,4, 0,4 y 1,0. Cada cabeza usa entropía cruzada, ponderación por frecuencia y label smoothing de 0,025. La inferencia calibra los logits de intención y acción en validación mediante temperatura. El umbral operativo se aplica a la menor de las dos puntuaciones disponibles.

Se usó AdamW con learning rate inicial 0,002, weight decay 0,012, clipping de gradiente a 1, lote de 40 y dropout de 0,24. ReduceLROnPlateau reduce el learning rate por factor 0,55 después de tres épocas sin mejora. Se selecciona el mejor checkpoint con una combinación de coincidencia semántica y F1 macro de intención en validación. Early stopping detiene después de nueve épocas sin mejora. Las corridas son de una sola semilla y sirven para comparar configuraciones iniciales.

| Configuración | Mejor época | Coincidencia semántica en prueba con reglas de entidades, antes del umbral |
|---|---:|---:|
| Dropout 0,24 | 6 | 32,0 % |
| Dropout 0 | 7 | 23,8 % |

La diferencia se observó en una corrida por configuración. El informe completo conserva la evolución de pérdida y del learning rate por época. La prueba de despliegue agrega el umbral 0,70 y refleja su efecto en la cobertura del modelo.

- [Curvas y configuración base](../results/scratch.json)
- [Experimento sin dropout](../results/scratch-no-dropout.json)
