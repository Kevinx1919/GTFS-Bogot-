# Mi contrato Gold: route_service_day_v1

**Estado:** publicado en Databricks para el horizonte 2026; pendiente de incorporación a Power BI.
**Destino:** gold_gtfs_route_service_day.
**Pregunta:** ¿qué programación declara cada ruta para una fecha y qué cambia entre dos fechas?

## Las seis definiciones de negocio

| Punto | Definición |
| --- | --- |
| Una fila | Una ruta y una fecha activa dentro de versión y SHA-256. |
| Ubicaciones | No cuento ubicaciones en este hecho; el puente de red será otro grano. |
| Ausencias | No invento filas para rutas sin días activos. Una fuente ausente o no vigente bloquea la preparación. |
| Claves | source_feed_version + source_sha256 + route_id + service_date. |
| Alcance | Todo el horizonte publicado de service_dates, sin recortarlo silenciosamente. |
| Límites | Conteos de viajes declarados y plantillas, no buses, salidas operadas ni pasajeros. |

Conservo los viajes declarados sin visitas cuando su servicio tiene una fecha activa.
Sus conteos permiten explicar exclusiones posteriores sin borrar registros del catálogo.
Las plantillas por frecuencia se cuentan separadas de los viajes sin frecuencias.
Una plantilla con tres ventanas sigue siendo una plantilla, con tres ventanas.

## Fuentes y eficiencia

Reutilizo gold_gtfs_trip_coverage con regla trip_coverage_v1 y silver_gtfs_service_dates con regla service_dates_v1.
No vuelvo a agregar los 9,4 millones de stop_times para preparar la oferta diaria.
Primero agrupo cobertura por ruta y servicio.
Después uno ese agregado con los días activos y consolido por ruta y fecha.
No expando cada visita a todas las fechas.

Fijo versiones Delta de las dos tablas y de sus auditorías.
Exijo el último intento Gold con STARTED y CLOSED/SUCCEEDED, committed=true y una sola ejecución.
No rescato una publicación antigua después de un intento posterior fallido o abandonado.
Compruebo que la cobertura coincide con su ejecución y regla auditadas.
Contrasto su linaje con las últimas publicaciones Silver de trips, stop_times y frequencies, sin releer sus tablas grandes.
Exijo también la publicación Silver vigente de service_dates y reconcilio sus filas y metadata.

## Campos de negocio

| Campo | Tipo | Interpretación |
| --- | --- | --- |
| source_feed_version, source_sha256 | string | Identidad de la fuente; queda oculta en el consumo normal, disponible para relaciones. |
| route_id | string | Ruta original, sin convertir IDs a números. |
| service_date | date | Fecha habilitada por service_dates. |
| declared_trip_count | long | Viajes declarados asociados a los servicios activos de la ruta. |
| trips_without_frequency_count | long | Viajes declarados sin ventanas de frecuencia publicadas. |
| frequency_template_count | long | Viajes que actúan como plantillas con una o más ventanas. |
| frequency_window_count | long | Ventanas asociadas a esas plantillas activas. |
| trips_without_visits_count | long | Viajes activos declarados con cero visitas publicadas. |
| trips_with_one_visit_count | long | Viajes activos declarados con una visita. |
| trips_with_multiple_visits_count | long | Viajes activos declarados con dos o más visitas. |
| active_service_count | long | Servicios distintos utilizados por la ruta ese día. |
| source_temporal_warning | boolean | Propaga una advertencia temporal de los servicios activos. |
| analysis_window_start, analysis_window_end | date | Horizonte completo de la fuente derivada. |

Son quince campos de negocio y tres de publicación: gold_run_id, gold_rule_version y gold_loaded_at_utc.
Las cargas se registran en UTC.
El publicador usa audit_gtfs_gold_runs y entity=route_service_day.

## Horizonte y ceros

Los parámetros window_start y window_end deben coincidir con el horizonte de cada fila service_dates.
La ventana admite entre uno y 366 días inclusivos.
Un horizonte distinto requiere una migración explícita si ya existe ese destino para la misma fuente.
No interpreto la versión del feed como una fecha de servicio.
La primera ejecución real utilizará 2026-01-01 a 2026-12-31.

Si un servicio no tiene días activos en el horizonte, registro inactive_trip_count sin etiquetarlo como error.
Una salida global vacía detiene esta primera versión y conserva el destino anterior.
En Power BI, una dimensión de fechas completa podrá mostrar cero programación en un día conocido sin filas.
Una fuente no publicada o una fecha fuera del horizonte debe seguir siendo ausencia, no cero.

## Conciliación

Compruebo unicidad de trip_id en la cobertura y de service_id + service_date en fechas activas.
Rechazo claves, categorías o cantidades de ventanas inválidas.
La salida conserva una sola fila por ruta y fecha.
La suma diaria de viajes declarados concilia con viajes por servicio multiplicados por sus días activos.
Cada fila cumple dos particiones:

- declarados = sin frecuencias + plantillas por frecuencia.
- declarados = sin visitas + una visita + varias visitas.

La suma sobre varias fechas representa viajes-día declarados; no viajes distintos del catálogo.
Tampoco sumo rutas por día para obtener rutas distintas de un período.

## Publicación

Validate prepara y reconcilia sin escribir tablas ni auditorías Gold.
Publish registra STARTED, reemplaza únicamente versión/hash, comprueba filas, clave y ejecución, y registra CLOSED.
Uso el helper Delta existente, que conserva otros ámbitos y exige esquema compatible.
Mantengo un solo escritor, sin bloqueo distribuido entre Jobs.
La auditoría indica si el commit ocurrió antes de un error posterior.
No hay transacción única entre destino y auditoría.
No incorporé automáticamente este nuevo publicador al coordinador.

## Uso en Power BI

Relacionaré el hecho con la dimensión de ruta mediante una clave que conserve versión y hash.
Relacionaré service_date con dim_gtfs_fecha.
No conectaré el hecho directamente con service_dates ni con cobertura mediante relaciones entre hechos.
Las medidas calcularán diferencias entre fechas y participación dentro de la selección.
Este hecho habilita Panorama y Programación; no modifica el catálogo de ubicaciones.


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


## Primera publicación diaria en Workspace

Ejecuté el publicador y obtuve SUCCEEDED, persisted=true y reconciled=true.
La ejecución Gold es 3b65045e-5afb-431b-93d0-1b40315b485d y la regla route_service_day_v1.
Publiqué 305.165 filas y 305.165 claves distintas de ruta y fecha.
Encontré 1.045 rutas con programación dentro del horizonte 2026 completo.
El total acumulado es 25.418.801 viajes-día declarados; no son viajes distintos ni viajes operados.
El resumen informó cero filas inválidas y cero viajes del catálogo sin días activos.

Fijé versiones Delta silver_audit=55, gold_audit=3, trip_coverage=0 y service_dates=0.
Conservé las ejecuciones fuente de cobertura 8d48f208-89a1-4c7b-9369-136be92d7a51 y fechas 8aed94d4-eaae-4faf-b776-7810447bd99e.

El aviso WindowExpression procede de las ventanas que buscan la última ejecución en auditorías ya filtradas por fuente y entidad.
No corresponde al agregado distribuido de rutas y fechas.
La publicación terminó correctamente; el aviso no requiere repetirla por sí solo.
La incorporación de esta tabla a Power BI sigue pendiente.
