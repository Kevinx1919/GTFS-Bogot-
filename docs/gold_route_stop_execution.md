# Mi ejecución de Gold ruta–ubicación

**Actualización: 20 de noviembre de 2026.**

## Publicación confirmada para 2026

La ejecución 41900e02-7a3a-4fd3-8f24-63d0002ab2b9 terminó SUCCEEDED, persisted=true y reconciled=true.
Conservé 62.715 parejas únicas, 1.045 rutas, 8.159 ubicaciones y 9.408.893 visitas publicadas.
El resumen registró cero filas inválidas y cero ubicaciones relacionadas sin coordenadas.
La tabla ya está importada en Power BI; Red publicada y el mapa de Panorama la utilizan.

## Procedimiento y comprobaciones previas

Los apartados siguientes conservan el procedimiento y las pruebas locales anteriores a esta publicación.

**Estado:** publicado en Databricks para 2026 e importado en el modelo local Power BI.
El [contrato](contracts/route_stop.md) conserva grano, campos y límites.

## Validar y publicar

1. Sincronizo el repositorio completo en Workspace.
2. Abro databricks/notebooks/gold/23_publish_gtfs_route_stop.
3. Uso repo_root igual que en los notebooks 20 y 22.
4. Configuro catalog=workspace, schema=gtfs_bogota, feed_version=2026-09-29.
5. Uso snapshot_sha256=08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097.
6. Conservo mode=validate y ejecuto Run all.
7. Reviso reconciled=true, invalid_rows=0 y candidate_rows=distinct_pairs.
8. Contrasto published_visits con el conteo Silver del ámbito: 9.408.893 si las fuentes 2026 no cambiaron.
9. Reviso routes_without_visits y related_stops_without_coordinates como diagnósticos.
10. Después selecciono publish y repito Run all para publicar.

No fijé una cantidad de parejas reales antes de ejecutar el publicador en Workspace.
Las 8.314 ubicaciones del catálogo no necesariamente aparecen todas en visitas.
No repito el publicador diario para ejecutar este nuevo notebook.

Publish debe terminar SUCCEEDED, persisted=true y con su cierre auditado.
El código comprueba la unicidad de las parejas y la ejecución guardada después del commit.
La publicación en Workspace y la integración Delta nativa nueva siguen pendientes de comprobación.

## Incorporación posterior a Power BI

Importaré las seis columnas de negocio por la conexión existente.
Excluiré gold_run_id, gold_rule_version y gold_loaded_at_utc del consumo normal.
Crearé route_key y stop_key con las expresiones de identidad que ya utiliza el modelo.
Configuré routes→puente con dirección única.
Para stops utilizo una relación virtual por stop_key dentro de la medida, evitando dos caminos activos desde snapshot.

El mapa usará stop_lat y stop_lon de stops, sin resumir, y conservará stop_key como identidad del punto.
Para que la selección de ruta reduzca los puntos, añadiré esta medida y aplicaré valor 1 como filtro visual:

```dax
Ubicación relacionada =
VAR Ubicaciones = VALUES ( silver_gtfs_stops[stop_key] )
VAR Parejas = CALCULATE ( COUNTROWS ( gold_gtfs_route_stop ), TREATAS ( Ubicaciones, gold_gtfs_route_stop[stop_key] ) )
RETURN IF ( Parejas > 0, 1, 0 )
```

La medida se evalúa por ubicación con los filtros de ruta y componente activos.
Crearé también un conteo distinto de stop_key sobre el puente para los indicadores de ubicaciones relacionadas.
No usaré COUNTROWS(stops) como si respondiera automáticamente al filtro de ruta.
No introduciré una relación bidireccional para forzar esa propagación.
La fecha de servicio no filtrará este mapa de catálogo.
Las coordenadas no forman por sí solas el trazado ordenado de una ruta.


Las [consultas posteriores](../databricks/sql/gold/route_stop_checks.sql) permiten contrastar el resumen y revisar una ruta.
El detalle acotado no sustituye los conteos completos del publicador.


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
