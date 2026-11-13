# Mi perfil de stop_times: 2025 y 2026

**Fecha:** 12 de noviembre de 2026. Consulté únicamente lectura mediante Genie.
Revisé ambos snapshots completos mediante agregados; los ejemplos tienen un límite explícito.
Este perfil no constituye una publicación Silver ni una ejecución completa del notebook.
El [contrato](contracts/stop_times.md) separa reglas, ausencias válidas y advertencias.

| Medida | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| Filas fuente y claves distintas trip_id + secuencia convertida | 5.698.892 | 9.408.893 |
| Viajes con visitas | 107.162 | 180.321 |
| Viajes declarados en trips Silver | 107.162 | 181.060 |
| Viajes declarados sin visitas | 0 | 739 |
| Viajes con una visita | 0 | 61 |
| Mínimo / máximo de visitas por viaje | 2 / 191 | 1 / 215 |
| Secuencia mínima / máxima | 0 / 191 | 1 / 215 |
| Filas con horas ≥24 | 23.079 | 42.065 |
| Mínimo / máximo de segundos publicados | 8.400 / 95.040 | 9.000 / 95.070 |
| Filas timepoint=0 | 5.698.878 | 9.408.795 |
| Filas timepoint=1 | 14 | 98 |
| Filas con stop_headsign informado | Campo ausente | 9.408.893 |
| Filas con shape_dist_traveled informada | Campo ausente | 9.408.893 |
| Viajes con frequencies y visitas | 2 | 14 |
| Primera salida de plantillas: mínimo / máximo, segundos | 16.200 / 19.800 | 21.600 / 21.600 |

S conserva las parejas exactas de versión y SHA-256 del [plan](stop_times_plan.md#qué-comprobé-y-qué-todavía-desconozco).
No detecté claves duplicadas, IDs/horas vacíos ni timepoint fuera de 0/1 en estos agregados.
Todas las horas publicadas cumplieron el formato comprobado.
Las referencias resolvieron contra trips y stops del mismo snapshot.
Todas las visitas revisadas referencian location_type 0. Las 155 estaciones de stops 2026 no representan visitas adicionales.
No detecté distancias descendentes ni repetidas en el control ordenado.
No necesito convertir secuencias que comienzan después de uno: GTFS permite ese inicio.

## Decisiones que tomé

Conservo las 61 visitas aisladas de 2026 con una advertencia.
No permiten describir un recorrido entre dos paradas.
Diez ejemplos acotados muestran stop_id 52281 y secuencia 1.
La muestra no demuestra que los 61 casos compartan parada ni explica su causa.
No los clasifico como cancelaciones, viajes vacíos ni posicionamiento sin evidencia adicional.

Registro 739 viajes sin visitas como cobertura incompleta.
No fabrico filas para cuarentena. Tampoco elimino viajes del histórico de trips.
Gold deberá mostrar esta limitación cuando compare viajes declarados y viajes con visitas.

Conservo las horas superiores a 24 como horas del día de servicio.
No cambio 25:00:00 por 01:00:00 ni sumo días para esconder retrocesos.
Conservo los opcionales ausentes de 2025 como null y registro el encabezado fuente.
No copio stop_headsign a otras visitas ni completo distancias desde coordenadas.

## Evidencia y límites

El [notebook 17](../databricks/notebooks/silver/17_profile_gtfs_stop_times.ipynb) conserva las consultas definitivas verificadas.
No guardo millones de filas ni resultados de ejecución dentro del notebook.
Las consultas devolvieron agregados completos. Los ejemplos limitados son una muestra, no un censo de causas.
Las lecturas de Genie no fijaron versiones Delta; el pipeline de publicación sí las fija.

La primera revisión generó una consulta inválida con ventanas dentro de agregados.
Genie la corrigió. No conservé esa versión fallida en el notebook.
También revisé las comparaciones de horas: uso segundos para evitar el orden lexicográfico.
El control definitivo compara contra el máximo temporal previo, incluso con ausencias intermedias.
No uso x!=x para detectar NaN en Spark; uso isnan y compruebo Infinity.
La validación del procesador sigue siendo la puerta final antes de publicar.

Después del perfil ejecuté stop_times en Databricks y comprobé que la tabla contiene datos.
El cierre funcional no incluye nuevos conteos por iteración ni mediciones de duración.
Los conteos del perfil no sustituyen ese resultado.

[Explorar las consultas en Databricks](https://dbc-caa55511-0fef.cloud.databricks.com/one/chat/threads/d22faadae12641b5a9c2486f4df81d8f?o=7474646722477316&utm_source=genie_chat_mcp).
