# Mi contrato Gold: route_stop_v1

**Estado:** publicado en Workspace para 2026 e importado y comprobado en Power BI.
**Destino:** gold_gtfs_route_stop.

| Definición | Decisión |
| --- | --- |
| Pregunta | ¿Qué ubicaciones relaciona cada ruta y cuáles comparten varias rutas? |
| Una fila | Una pareja ruta–ubicación dentro de versión y SHA-256. |
| Ubicaciones | Solo paradas/plataformas referenciadas por stop_times, tipo 0 o ausente según Silver. No añado estaciones padre. |
| Ausencias | Conservo las rutas sin visitas en el catálogo y las cuento en el diagnóstico. No invento parejas ni coordenadas. |
| Claves | source_feed_version + source_sha256 + route_id + stop_id. |
| Límites | Red publicada de catálogo; no representa operación, frecuencia, transbordos confirmados ni cobertura poblacional. |

## Fuentes y construcción

Uso routes, trips, stop_times y stops Silver del mismo ámbito fuente.
Exijo sus reglas routes_v1, trips_v1, stop_times_v1 y stops_v1 y últimas publicaciones exitosas.
Fijo versiones Delta de las cuatro fuentes y de su auditoría.
Comparo filas, ejecución y regla con la auditoría antes de unir.
Reutilizo la selección de la última publicación del procesador diario.
Un intento posterior fallido o ambiguo impide usar una publicación anterior.

Agrupo stop_times por viaje y ubicación, conservando la cantidad de visitas.
Uno ese agregado con trips y agrupo por ruta y ubicación.
Una visita repetida no crea otra pareja, pero sí aumenta published_visit_count.
Dos viajes de una ruta que mencionan la misma ubicación producen una sola pareja.
Dos rutas que comparten una ubicación producen dos parejas distintas.

No recojo visitas o parejas masivas en Python ni uso UDF.
Las comprobaciones y agregados se ejecutan en Spark.
Compruebo claves antes de unir y rechazo referencias huérfanas sin descartarlas silenciosamente.
No agrego ubicaciones padre como si fueran visitas adicionales.

## Campos

| Campo | Tipo | Uso |
| --- | --- | --- |
| source_feed_version, source_sha256 | string | Identidad y relaciones históricas. |
| route_id, stop_id | string | IDs originales de la pareja, sin convertirlos a enteros. |
| published_visit_count | long | Visitas publicadas asociadas a esta pareja, incluidas repeticiones válidas. |
| declared_trip_count | long | Viajes declarados distintos que relacionan esta pareja. Incluye plantillas. |

Son seis campos de negocio y tres técnicos: gold_run_id, gold_rule_version y gold_loaded_at_utc.
Las coordenadas, nombres y tipos permanecen en stops para no repetirlos por cada ruta.
No sumo declared_trip_count de varias ubicaciones como si fueran viajes distintos del sistema.
No sumo ubicaciones por ruta para obtener ubicaciones únicas de toda la red.

## Comprobaciones

Las claves de rutas, viajes y ubicaciones deben ser únicas.
La clave de stop_times es viaje y secuencia; una parada puede repetirse con otra secuencia.
Verifico trips→routes, stop_times→trips y stop_times→stops con identidad completa.
La cantidad de parejas debe igualar sus claves distintas.
La suma published_visit_count debe reconciliar con todas las visitas Silver del ámbito.
Cada pareja conserva al menos un viaje y tantas visitas como viajes o más.

El resumen informa rutas del catálogo, rutas con visitas, rutas sin visitas, ubicaciones relacionadas y ubicaciones sin coordenadas.
Una coordenada ausente no se rellena; el mapa tendrá que identificar ese caso.
Una salida global vacía bloquea esta primera versión sin borrar un destino anterior.

## Publicación

Validate no escribe tablas ni auditorías.
Publish registra STARTED, sustituye solo versión/hash, comprueba parejas y ejecución y registra CLOSED.
Uso el escritor Delta por ámbito existente y un único escritor operativo.
La auditoría conserva gold_committed si un error ocurre después del commit.
No existe una transacción única entre destino y auditoría.
No modifiqué el Job principal.

## Consumo del mapa

El puente recibe filtros desde ruta y ubicación mediante claves de fuente completas.
Mantengo ambas relaciones unidireccionales hacia el puente.
El mapa utiliza campos de stops y una medida de existencia de parejas como filtro visual.
Ese filtro permite que la ruta seleccionada reduzca los puntos visibles sin cambiar globalmente la dirección de las relaciones.
La [guía de ejecución](../gold_route_stop_execution.md) explica su incorporación.
No aplico fecha de servicio a esta red de catálogo; una red diaria requeriría conservar servicios o derivar otro grano.


## Verificación local

Pasaron 18 pruebas en 81,013 segundos: diecisiete del puente y una regresión del contrato de horizonte compartido.
Usé Spark 4.0.1 en Docker offline, repositorio en solo lectura y datos sintéticos fuera de OneDrive.
Las lecturas y escrituras Delta se sustituyen por dobles; no ejecuté una integración Delta nativa nueva.
Probé repeticiones válidas, ubicaciones compartidas, claves duplicadas, referencias huérfanas, padre indebido y ausencia de coordenadas.
También comprobé identidad histórica, metadata auditada, fuentes perdidas, propagación de fallos previos y evidencia de commit tras un error.
Validate no llamó al escritor ni a la auditoría.
La publicación con doble comprobó su ámbito y las parejas guardadas.
La fixture huérfana inicial fabricaba secuencias duplicadas; la corregí para aislar la referencia faltante y la selección final pasó completa.
Comprobé sintaxis Python, los dos bloques del notebook sin resultados guardados, enlaces y manifiesto BI.
La ejecución y publicación en Workspace siguen pendientes.


## Cierre de publicación y consumo

La ejecución Gold 41900e02-7a3a-4fd3-8f24-63d0002ab2b9 terminó SUCCEEDED y reconciled=true, según su resumen de publicación.
Importé la tabla mediante la conexión existente del modelo local y comprobé sus filtros y conteos con DAX.
La [evidencia del modelo](../power_bi_gold_import.md) conserva los resultados y decisiones de relación.
