# Mi vista previa de cobertura de viajes 2026

**Fecha de revisión:** 17 de noviembre de 2026.
**Estado:** consulta de lectura ejecutada mediante Genie; no publiqué Gold.
Usé el snapshot existente 2026-09-29 y su hash validado 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097.
Conservé el SQL en el [notebook 19](../databricks/notebooks/gold/19_preview_gtfs_trip_coverage.ipynb).
La consulta terminó SUCCEEDED y recuperé sus cuatro filas estructuradas completas, sin truncamiento.

## Resultado

| Cobertura | Contexto | Viajes declarados | Visitas | Ventanas |
| --- | --- | ---: | ---: | ---: |
| sin_visitas | sin_frecuencias | 739 | 0 | 0 |
| una_visita | sin_frecuencias | 61 | 61 | 0 |
| varias_visitas | por_frecuencia | 14 | 98 | 14 |
| varias_visitas | sin_frecuencias | 180246 | 9408734 | 0 |

Los grupos suman 181060 viajes, 9408893 visitas y 14 ventanas.
Las cantidades coinciden con los conteos documentados del snapshot.
Hay 180260 viajes con varias visitas y 180321 con al menos una visita.
La consulta encontró cero visitas sin pareja completa de llegada y salida.
También encontró cero grupos con contexto de frecuencia inconsistente.

Estos resultados no prueban exactitud temporal ni operación real.
Los 61 viajes con una visita tienen horas presentes; eso no crea una segunda parada.
Los 14 viajes por frecuencia representan plantillas con ventanas, no catorce salidas diarias observadas.
Sin frecuencias no equivale automáticamente a horarios exactos.

## Método y límites

Leí únicamente trips, stop_times y frequencies Silver del mismo snapshot.
Agregué visitas y ventanas por la clave completa antes de unir mediante left join.
No consulté la API del proveedor, descargué ZIP ni ejecuté Jobs durante esta revisión.
La consulta sí leyó las columnas necesarias de stop_times; no fue una operación exclusiva de metadata.
No recogí sus millones de visitas en el driver ni guardé resultados en el notebook.

Esta lectura de Genie no fijó versiones Delta de las tres entradas ni representa una transacción conjunta.
La implementación de publicación deberá fijarlas y reconciliar las fuentes.
El notebook conserva la consulta verificada; todavía no documenté una ejecución completa de ese notebook en Workspace.
No repetí perfiles completos de nulos, duplicados y formatos ya cubiertos por los contratos Silver.
La siguiente implementación sigue la [ficha Gold propuesta](contracts/trip_coverage.md).

[Explore in Databricks](https://dbc-caa55511-0fef.cloud.databricks.com/one/chat/threads/868b28b754034326a7489fd8e18ed009?o=7474646722477316&utm_source=genie_chat_mcp).
