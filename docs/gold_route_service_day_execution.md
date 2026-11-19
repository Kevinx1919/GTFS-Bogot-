# Mi ejecución de programación Gold por ruta y fecha

**Estado:** implementación local; falta ejecutar validate y publish en Workspace.
Las comprobaciones de Genie son lectura y no representan una publicación de esta tabla.

## Qué preparo

El nuevo publicador convierte cobertura de viajes y días activos en una fila por ruta y fecha.
La [ficha de negocio](contracts/route_service_day.md) explica sus campos y conciliaciones.
No necesito exportar archivos CSV de Databricks a Power BI.
La conexión ya configurada leerá el destino cuando se publique.

## Ejecución en Databricks

1. Sincronizo el repositorio completo con estos archivos nuevos.
2. Abro `databricks/notebooks/gold/22_publish_gtfs_route_service_day`.
3. Configuro los campos siguientes y ejecuto Run all.

| Campo | Valor inicial |
| --- | --- |
| repo_root | La raíz del repositorio en Workspace, igual que en notebook 20. |
| catalog | workspace |
| schema | gtfs_bogota |
| feed_version | 2026-09-29 |
| snapshot_sha256 | 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097 |
| window_start | 2026-01-01 |
| window_end | 2026-12-31 |
| mode | validate |

Espero status=VALIDATED, persisted=false, reconciled=true y candidate_rows=distinct_keys.
El resultado incluye rutas distintas del horizonte, viajes-día y viajes sin días activos.
No fijé un total candidato real sin ejecutar el procesador completo en Workspace.
No se crean tablas ni auditorías en validate.

4. Reviso el resumen y las referencias fijadas.
5. Selecciono mode=publish y repito Run all para publicar el destino.
6. Compruebo status=SUCCEEDED, persisted=true y la auditoría CLOSED con gold_committed=true.
7. Ejecuto las [consultas de comprobación](../databricks/sql/gold/route_service_day_checks.sql).

La publicación puede bloquearse si hay un intento Gold posterior sin cierre o si su linaje Silver quedó desactualizado.
En ese caso reviso el mensaje y las auditorías; no desactivo las comprobaciones para conseguir un resultado.

## Muestra de negocio ya consultada

Genie ejecutó consultas de lectura sobre las fuentes existentes para estas tres fechas.
La agregación utilizó todas las rutas y servicios, sin el LIMIT del detalle auxiliar de rutas.

| Fecha de servicio | Rutas distintas | Viajes declarados sin frecuencias | Plantillas por frecuencia |
| --- | ---: | ---: | ---: |
| 2026-11-19, jueves | 863 | 80.201 | 6 |
| 2026-11-21, sábado | 775 | 60.618 | 6 |
| 2026-11-22, domingo | 789 | 40.227 | 2 |

Son valores esperados para contrastar las mismas fuentes después de publicar, si no cambiaron.
No representan viajes operados.
El domingo tiene más rutas declaradas que el sábado en esta muestra, aunque menos viajes sin frecuencias.
Esa diferencia justifica explorar rutas y calendarios antes de atribuir una causa.

La consulta de duplicados service_id + service_date no encontró filas.
Otra consulta no encontró servicios de cobertura sin actividad entre el 19 y el 22 de noviembre.
Ese control usó ese intervalo corto; no lo describo como una auditoría completa de calendarios.
La consulta auxiliar por ruta y servicio se limitó a 500 filas y no sustenta totales de toda la red.

## Preparación del mapa

La fuente Silver 2026 contiene 8.314 ubicaciones con pares de coordenadas presentes.
Separé 8.159 de tipo 0 y 155 de tipo 1.
No presento todas esas ubicaciones como paradas equivalentes.
La presencia de coordenadas no certifica exactitud física ni pertenencia a un polígono.

La [preparación BI](../BI/consumo/README.md) conserva campos del mapa y dependencias pendientes.
El puente ruta–ubicación será el siguiente incremento para filtrar el mapa por componente o ruta.
Los puntos de shapes no se convertirán en paradas.

[Explore in Databricks](https://dbc-caa55511-0fef.cloud.databricks.com/one/chat/threads/716373306e1942e4a06cb1591f56a911?o=7474646722477316&utm_source=genie_chat_mcp)

## Después de la publicación

Importaré gold_gtfs_route_service_day por la conexión existente y con el manifiesto de columnas de BI/consumo.
Conservaré las claves técnicas para relacionar datos, ocultas en la presentación normal.
Comprobaré filtros de ruta, componente y fecha antes de crear medidas narrativas.
La siguiente implementación visual partirá de las preguntas de negocio y de un diseño nuevo.
El boceto anterior deja de ser la base y permanece solo como artefacto histórico.


## Pruebas locales de este incremento

Pasaron 17 pruebas en 65,718 segundos con Python 3.10, Spark 4.0.1 y el entorno Docker offline existente.
El repositorio estuvo montado en solo lectura y los datos sintéticos quedaron fuera de OneDrive.
La primera selección usó una copia incompleta de PySpark en la caché y falló al importar su DataFrame.
Cambié la prioridad de importación al PySpark completo de la imagen, sin descargar ni reinstalar archivos.
Corregí además una fixture que convertía varios servicios en uno y fabricaba duplicados antes del caso vacío.
La selección final terminó sin fallos ni omisiones.

Las pruebas cubren varias ventanas por plantilla, varios servicios de una ruta, días inactivos, claves duplicadas,
horizontes incompatibles, fuentes perdidas, linaje desactualizado e intentos sin cierre.
También comprueban validate sin escrituras, el ámbito del escritor y fallos anteriores y posteriores al commit.
Las transformaciones y conciliaciones usan Spark real.
Las lecturas Delta y el escritor están sustituidos por dobles en los tests nuevos.
No ejecuté una integración Delta nativa nueva ni una publicación en Workspace; la comprobación allí sigue pendiente.
La persistencia por ámbito reutiliza el helper ya existente.

Validé sintaxis Python, los dos bloques del notebook sin resultados guardados, sus quince campos de consumo y enlaces documentales.
