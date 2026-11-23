# Auditoría del proyecto y del dataset

## Recursos encontrados

| Recurso | Hallazgo y uso |
|---|---|
| `WarCommanderDemo/WarCommanderDemo.uproject` | UE 5.8, módulo C++ con variantes First Person, Shooter y Horror. Se conservan sus mapas, Blueprints y clases. |
| `WarCommanderDemo/Content` | Plantillas, maniquíes y materiales de prototipado. Valle Alfa reutiliza `M_FlatCol` y geometría del motor. |
| `Referencias/map_idea.jpg` | La referencia usa extensión `.jpg`. Presenta bases enfrentadas, tres recorridos, posiciones intermedias y cruces laterales. Valle Alfa toma esa topología. |
| `Documentacion/Pautas IA enemiga.docx` | Incluye percepción parcial, caducidad de contactos, exploración y cinco tácticas. Sus latencias son estimaciones de referencia. |
| `AI NLP/Data` | Esquema anterior, DataTables CSV de unidades, comandos, zonas, oleadas y réplicas, structs de importación y JSONL con etiquetas BIO. Se preservan como recursos de origen. |
| `Assets` | Mallas FBX, paquetes para Mixamo, texturas, mapa de altura, capas de terreno, interfaz y VFX. Se mantienen disponibles para el pulido. La arena actual se genera a partir de geometría simple. |
| `Tema NLP Universidad codigo referencial` | Cuadernos de PyTorch, Transformers y NLP con tareas de otros dominios. Se consultó su inventario y se usó el dataset específico del juego. |

Se encontró UE 5.8.4, Visual Studio 2022 y Python 3.14.3. El primer intento de compilación usó una ruta global de caché sin permisos. La compilación automatizada usa un directorio UBA del proyecto. El directorio raíz y el proyecto Unreal carecían de un repositorio Git inicializado.

## Seed y distribución experimental

La semilla contiene 1.510 frases en español, con ejemplos de 11 etiquetas heredadas y 8 tipos de entidades. Hay 220 instrucciones compuestas. Los tamaños originales son 1.053, 226 y 231. Cada partición carece de duplicados textuales exactos. Hay 142 ejemplos con desalineación BIO. El generador cuenta algunos conectores de varias palabras como un token y les asigna varias etiquetas. El informe de entrenamiento guarda los conteos por partición.

Las etiquetas originales mezclan acto lingüístico y acción táctica. El esquema anterior permite listas de acciones y usa identificadores diferentes de los del prototipo. Se introdujo un contrato v1 para una sola propuesta táctica, con cuatro intenciones y once acciones. Una parte de los ejemplos originales se adapta y retokeniza para **entrenamiento**. Las otras frases se conservan en el dataset original.

El generador del corpus v1 reserva familias de expresiones disjuntas para validación y prueba, elimina coincidencias normalizadas y registra la fuente de cada muestra. Las particiones resultantes son 1.434, 117 y 172. El conjunto de entrenamiento incorpora 259 frases adaptadas de la semilla. La prueba es sintética y el balance favorece las órdenes. Su puntuación mide la generalización a las familias reservadas. La prueba con hablantes bolivianos, varias voces y ruido de combate requiere una colección adicional.
