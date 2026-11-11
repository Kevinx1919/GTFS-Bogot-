# Mi perfil de stops: 2025 y 2026

**Fecha de revisión:** 10 de noviembre de 2026. Consulté Bronze y la auditoría de encabezados mediante Genie, en modo lectura, y recuperé los seis resultados estructurados sin truncamiento. Las consultas verificadas quedan en un único [notebook de lectura](../databricks/notebooks/silver/11_profile_gtfs_stops.ipynb); no duplico un archivo SQL ni creo otro paso del Job.

**Estado:** perfilado completado. El contenedor del notebook está preparado y comprobado estructuralmente; no tiene todavía una ejecución completa documentada en Databricks. Después de revisar este perfil definí e implementé localmente el [contrato stops_v1](contracts/stops.md); su ejecución y publicación en Databricks siguen pendientes. No modifiqué Bronze, Silver ni el Job durante este perfilado.

## Alcance y selección

Tabla: `workspace.gtfs_bogota.bronze_gtfs_stops`. La consulta inicial de conteos descubrió los hashes por fecha; las demás consultas de datos y encabezados fijaron estas parejas exactas:

| Versión | SHA-256 | Filas / IDs distintos |
| --- | --- | ---: |
| 2025-10-28 | `07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952` | 6.530 / 6.530 |
| 2026-09-29 | `08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097` | 8.314 / 8.314 |

Llamo ubicación a una fila de stops: el tipo publicado determina si representa una parada/plataforma, una estación u otra clase. No interpreto 6.530 → 8.314 como crecimiento real de oferta ni como persistencia de las mismas identidades.

## Qué significa cada campo y qué tipo propongo

Los nueve campos de negocio están almacenados como string en Bronze. Los tipos de esta tabla quedaron definidos en el contrato implementado localmente; no son evidencia de una transformación ejecutada en Databricks:

| Campo | Qué representa | Tipo Silver definido | Qué revisaré |
| --- | --- | --- | --- |
| stop_id | Identidad fuente dentro del snapshot. | string | Clave con versión y hash; contenido y unicidad. |
| stop_code | Código visible para viajeros, cuando existe. | string | Opcional; no exigiré que sea único. |
| stop_name | Nombre publicado de la ubicación. | string | Obligatoriedad según tipo; espacios en extremos. |
| stop_lat | Latitud. | double | Conversión, finitud y rango global. |
| stop_lon | Longitud. | double | Conversión, finitud y rango global. |
| location_type | Clase de ubicación. | int | Dominio y coherencia de la jerarquía. |
| parent_station | ID de otra ubicación del mismo snapshot. | string | Existencia, tipo de padre y condiciones de presencia. |
| zone_id | Identidad de zona tarifaria. | string | Opcional; no convertiré el código 0 en una medida numérica. |
| wheelchair_boarding | Información publicada de accesibilidad. | int | Opcional; dominio y semántica según ubicación. |

La procedencia añade source_feed_version, source_sha256 y source_file_path como string, y bronze_loaded_at_utc como timestamp. El esquema histórico tiene 13 columnas en total.

## Archivos publicados y ausencias

La auditoría registra ocho columnas de negocio en 2025 y nueve en 2026. La diferencia es wheelchair_boarding, ausente del archivo de 2025. Sus 6.530 null en la tabla histórica no representan celdas publicadas vacías. Parent_station y zone_id sí estaban publicadas en ambos archivos.

Leo esta evidencia desde `audit_gtfs_source_schema_observations`, no mediante una nueva lectura del ZIP o del TXT. Los conjuntos de nombres registrados no demuestran el orden original de las columnas. En la distribución, [NULL] es una etiqueta de presentación, no una imputación ni un valor escrito en Bronze.

## Tipos de ubicación y valores observados

| Comprobación | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| location_type = 0: parada/plataforma | 6.530 | 8.159 |
| location_type = 1: estación | 0 | 155 |
| Filas con parent_station informado | 0 | 750 |
| Padres distintos referenciados | 0 | 143 |
| wheelchair_boarding publicado | No | Sí: todas las filas tienen 1 |
| zone_id informado | 6.530, todas con código 0 | 4, todas con código 0 |
| zone_id nulo | 0 | 8.310 |

En 2025, no tener padres es compatible con ubicaciones de tipo 0. En 2026 puedo distinguir estaciones y paradas/plataformas que apuntan a ellas. Como ejemplo, una estación puede agrupar varias plataformas sin que cada fila represente una estación diferente.

Las 750 referencias de 2026 apuntan a 143 estaciones válidas del mismo snapshot. El cálculo 155 − 143 = 12 indica que doce estaciones no aparecen como padre en esas referencias; es una observación derivada de estos agregados, no un rechazo automático.

No copio accesibilidad de 2026 hacia 2025 ni convierto su ausencia en falta de accesibilidad. El valor 1 de 2026 es una declaración del feed, no una comprobación física de rampas o recorridos.

## Nulos, contenido y espacios

| Campo | Null 2025 | Null 2026 | Distintos con contenido 2025 | Distintos con contenido 2026 | Espacios extremos 2025 / 2026 |
| --- | ---: | ---: | ---: | ---: | ---: |
| stop_id | 0 | 0 | 6530 | 8314 | 0 / 0 |
| stop_code | 4 | 159 | 6512 | 8155 | 0 / 0 |
| stop_name | 0 | 0 | 5273 | 4482 | 27 / 1 |
| stop_lat | 0 | 0 | 6530 | 8314 | 0 / 0 |
| stop_lon | 0 | 0 | 6530 | 8314 | 0 / 0 |
| location_type | 0 | 0 | 1 | 2 | 0 / 0 |
| parent_station | 6530 | 7564 | 0 | 143 | 0 / 0 |
| zone_id | 0 | 8310 | 1 | 1 | 0 / 0 |
| wheelchair_boarding | 6530 | 0 | 0 | 1 | 0 / 0 |

No encontré cadenas vacías ni valores compuestos solo por espacios en los controles de Bronze. Si el lector CSV convirtió un vacío del TXT en null, este perfil no recupera esa distinción del original. Los conteos de nulo, vacío, solo espacios y contenido explican el total de cada campo; distintos y espacios extremos son diagnósticos adicionales.

Encontré 27 nombres con espacios extremos en 2025 y uno en 2026. No los cambié. En stops_v1 acordé quitar espacios Unicode de los bordes del nombre, conservando la recuperación del original desde Bronze; los IDs no se limpian silenciosamente.

Stop_code tiene cuatro null en 2025 y 159 en 2026. Además, en 2025 hay 6.526 códigos con contenido pero 6.512 distintos: existen repeticiones de código, no de stop_id. No deduplicaré por código ni por nombre; tampoco relleno los códigos ausentes con el ID.

## Identidad, coordenadas, jerarquía y procedencia

Todos estos controles dieron **cero en ambos snapshots**:

- IDs sin contenido, grupos de IDs duplicados, copias de negocio adicionales, IDs con atributos conflictivos y colisiones de ID al quitar espacios extremos.
- Nombres o coordenadas requeridos ausentes para los tipos observados.
- Coordenadas informadas que no convierten a double, son NaN o están fuera del rango global; pares (0, 0).
- Códigos de location_type o wheelchair_boarding fuera del formato de dominio comprobado.
- Padres inexistentes, autorreferencias, padres con tipo incorrecto y presencia o ausencia de padre incompatible con el tipo de ubicación.
- Timestamp Bronze nulo, ruta fuente inconsistente con versión/hash/stops.txt y caracteres de control en nombres.

Los campos de negocio para comparar copias excluyen las columnas técnicas. Los IDs ya resultaron únicos antes de interpretar el self-join de jerarquía; en un feed futuro con IDs repetidos tendría que resolver primero esa ambigüedad para evitar multiplicar filas en la agregación.

| Extremo observado | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| Latitud mínima | 4.404903241484833 | 4.38691449475084 |
| Latitud máxima | 4.819356886551515 | 4.819356886375242 |
| Longitud mínima | -74.21512003523206 | -74.21922740950833 |
| Longitud máxima | -74.0058612942782 | -74.00586129427845 |

Convertir y comprobar rangos globales no demuestra que cada punto esté dentro del límite oficial de Bogotá ni valida su posición física exacta. No impongo una caja geográfica arbitraria como motivo de rechazo.

## Reglas de referencia y siguiente decisión

Contrasto la jerarquía con [GTFS stops.txt](https://gtfs.org/documentation/schedule/reference/#stopstxt): el padre de una parada/plataforma es una estación; una estación no lleva padre. Los tipos 2 y 3 exigen una estación padre; el tipo 4 exige una plataforma padre. Nombre y coordenadas son obligatorios para tipos 0, 1 y 2. Las reglas que no aparecen en los datos observados necesitarán casos de prueba sintéticos al implementar el contrato.

Conservo como clave candidata `(source_feed_version, source_sha256, stop_id)`. La relación de padre usará la misma versión y hash. No unifico IDs entre años por parecido de nombres o coordenadas. Stops no depende directamente de routes: las futuras relaciones de viajes y horarios darán ese contexto.

Después de revisar este perfil implementé stops_v1 con tipos, motivos de rechazo y limpieza de los 28 nombres con espacios extremos. El registro local y el pipeline admiten stops, y la plantilla incorpora su tarea; aún debo sincronizar y ejecutar validate/publicación en Databricks. El notebook 10 conserva sus dos bloques. El resultado de este informe sigue siendo el perfil fuente, no la salida de esa futura publicación.

## Evidencia y alcance de la comprobación

Recuperé 13 filas de esquema, dos de conteos por snapshot, dos de encabezados, ocho grupos de distribución, 18 filas de métricas por campo y dos de controles. Cada resultado estructurado terminó en SUCCEEDED y sin truncamiento; la distribución devolvió menos filas que su límite SQL de 50.

La primera consulta de métricas que propuso Genie repetía nueve CTEs y no incluía la bandera Unicode solicitada. La sustituí por una consulta compacta con stack y literales raw `r'(?U)...'`, ejecutada y recuperada antes de documentar los resultados definitivos. Conservo en el notebook la versión corregida; no afirmo una mejora de tiempo sin medirla.

No guardo filas fuente, respuestas completas del conector, credenciales o enlaces privados en Git. El notebook conserva SQL verificable y este informe sus agregados e interpretación. La revisión real de los resultados precede al contrato y a la publicación Silver.
