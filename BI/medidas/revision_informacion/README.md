# Mis medidas de Revisión de información

Guardé veinte medidas en gold_gtfs_trip_timing.
Once medidas calculan cantidades, disponibilidad o filtros de detalle.
Nueve medidas generan HTML; Tabla previa HTML se utiliza solamente en el prototipo.
Organizo las carpetas de campos como Revisión\Métricas y Revisión\Presentación HTML.

[metricas.dax](metricas.dax) conserva los cálculos.
[presentacion_html.dax](presentacion_html.dax) conserva el formato.
Las definiciones TMDL del PBIP constituyen la implementación del modelo.

## Medidas numéricas

| Medida | Definición |
| --- | --- |
| Fuente disponible | Ambas Gold importadas tienen filas para una identidad única de snapshot. No sustituye su auditoría. |
| Evaluados | Viajes del componente y ruta, retirando los filtros de motivo y detalle del hecho. |
| Sin visitas | timing_status=no_visits del contexto completo. Contrasto el resultado contra cobertura Gold. |
| Una visita | timing_status=one_visit del contexto completo. |
| Plantillas | timing_status=frequency_template, respetando la precedencia de categorías de Gold. |
| Elegibles | timing_status=eligible del contexto completo. |
| Excluidos | Viajes del contexto con timing_status distinto de eligible. No equivale a datos inválidos. |
| Casos del motivo | Excluidos que coinciden con el motivo seleccionado. |
| Porcentaje excluido | Excluidos entre Evaluados; ausencia de denominador permanece BLANK. |
| Mostrar caso | Devuelve uno para una fila de viaje excluido; filtra la tabla nativa. |
| Visitas del caso | Cantidad de visitas del viaje seleccionado. |

## Filtros y rendimiento

Mantengo los caminos físicos desde snapshot, agency, routes y trips.
Para el denominador retiro solo columnas del hecho usadas por motivo y detalle.
No retiro los filtros de las dimensiones ni materializo todos los trip_key para reaplicarlos.
Esta elección evita una transferencia innecesaria de claves dentro de las consultas.
No añado relaciones bidireccionales entre los dos hechos Gold.

El motivo limita Casos del motivo, el ranking y la tabla.
Los indicadores superiores y la clasificación conservan sus denominadores de componente/ruta.
La selección nativa de una fila aplica DataFilter solo a Acción HTML.
Todas las otras interacciones desde esa tabla utilizan NoFilter.

## Columnas de presentación

report_review_reason traduce timing_status a etiquetas legibles.
report_route_label consulta código e ID de routes mediante versión, hash y route_id.
No sustituyen las claves originales ni modifican la clasificación Gold.
Las columnas se recalculan con el modelo de consumo.

[Explicación de negocio](../../../docs/power_bi_revision_negocio.md).
[Resultados y revisión](../../imagenes/revision_informacion/README.md).
