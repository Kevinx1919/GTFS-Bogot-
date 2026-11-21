# Mi contrato Gold: trip_timing_v1

**Estado:** publicado en Workspace para 2026 e importado y comprobado en Power BI.
**Destino:** gold_gtfs_trip_timing.

| Definición | Decisión |
| --- | --- |
| Pregunta | ¿Qué extremos horarios publican los viajes de una ruta y cuáles permiten calcular un intervalo? |
| Una fila | Un trip_id declarado, dentro de versión y SHA-256, aunque no tenga visitas. |
| Ubicaciones | Primera y última visita por stop_sequence. No uso puntos de shapes ni agrego estaciones padre. |
| Ausencias | Conservo horas null y razones de exclusión; no interpolo ni busco otra hora no nula para sustituir el extremo. |
| Claves | source_feed_version + source_sha256 + trip_id; ruta y servicio permanecen en la misma identidad. |
| Límites | Intervalo publicado entre extremos, no duración observada, puntualidad ni continuidad del servicio. |

## Definición horaria cerrada

Ordeno por stop_sequence, que debe ser única dentro del viaje.
Tomo departure_time_seconds de la primera visita y arrival_time_seconds de la última.
No uso MIN(hora) ni MAX(hora) para decidir qué visita es la primera o la última.
Conservo los segundos superiores a 86.400 sin aplicar módulo 24 ni convertirlos en timestamps UTC.
La zona del servicio procede de agency; la metadata de carga permanece en UTC.

Calculo published_span_seconds solo para viajes con al menos dos visitas, ambos extremos presentes,
intervalo no negativo y ausencia de ventanas de frecuencia.
El cero es un intervalo publicado válido entre dos visitas distintas.
Las plantillas conservan sus extremos como diagnóstico, pero no reciben un intervalo comparable al de viajes sin frecuencias.
No expando salidas, incluso si frequencies informa exact_times=1.

La precisión se refiere únicamente al timepoint efectivo de los dos extremos.
Exact_as_published describe los códigos publicados; no demuestra exactitud operacional.
Una precisión aproximada o desconocida no impide una resta descriptiva, pero debe mostrarse junto al indicador.
Una hora intermedia ausente no sustituye ni elimina los extremos del viaje.

## Fuentes y preparación

Uso trips, stop_times y frequencies Silver del mismo ámbito.
Exijo reglas trips_v1, stop_times_v1 y frequencies_v1 y publicaciones vigentes exitosas.
Fijo versiones Delta y verifico filas, ejecución y regla frente a sus auditorías.
No rescato un éxito antiguo después de un intento fallido o ambiguo posterior.
Esta primera versión requiere frequencies publicado, como en el snapshot 2026.
No interpreto una tabla perdida como un archivo opcional legítimamente ausente.

Agrego visitas y ventanas por viaje antes de unirlas con trips mediante left join.
Así preservo viajes sin visitas y evito multiplicación por varias ventanas.
Uso agregados min/max de structs ordenados primero por secuencia, sin ordenar todas las visitas con una ventana global.
No ejecuto UDF ni recojo millones de filas en Python.

## Campos y tipos

| Campos | Tipo | Significado |
| --- | --- | --- |
| source_feed_version, source_sha256 | string | Identidad histórica. |
| trip_id, route_id, service_id | string | IDs originales, sin convertirlos en números. |
| visit_count | long | Visitas publicadas del viaje. |
| first_stop_id, last_stop_id | string nullable | Ubicaciones de las visitas extremas. |
| first_stop_sequence, last_stop_sequence | long nullable | Secuencias extremas originales. |
| first_departure_time_seconds, last_arrival_time_seconds | long nullable | Horas extremas publicadas como segundos de servicio. |
| frequency_window_count | long | Ventanas asociadas al viaje. |
| is_frequency_template | boolean | Existencia de al menos una ventana. |
| endpoint_time_precision | string | unknown, approximate o exact_as_published. |
| timing_status | string | Motivo o elegibilidad, según la precedencia inferior. |
| published_span_seconds | long nullable | Resta de extremos exclusivamente cuando timing_status=eligible. |

Son diecisiete campos de negocio y tres de publicación: gold_run_id, gold_rule_version y gold_loaded_at_utc.
No confundo el intervalo de un viaje con la amplitud mínima–máxima de todas las horas de una ruta.

## Categorías excluyentes, en orden

1. no_visits: cero visitas.
2. one_visit: una visita.
3. frequency_template: al menos dos visitas y ventanas de frecuencia.
4. missing_endpoints: sin frecuencia y falta una hora extrema.
5. reversed_endpoints: ambos extremos presentes y resta negativa.
6. eligible: al menos dos visitas, sin frecuencia y resta no negativa.

Conservo is_frequency_template aunque otra categoría tenga precedencia, por ejemplo si faltan visitas.
No corrijo automáticamente los extremos invertidos ni altero Silver.
Las categorías deben conciliar con todos los viajes declarados.

## Validación y publicación

Compruebo claves únicas de trips; viaje/secuencia de stop_times; viaje/inicio de frequencies.
Rechazo IDs, secuencias y horas negativas inválidas.
Las horas opcionales ausentes y timepoint no especificado siguen siendo ausencias.
Compruebo que visitas y ventanas referencien viajes del mismo ámbito.
Reconcilio filas y viajes distintos contra trips; visitas contra stop_times; ventanas contra frequencies.

Validate no escribe tablas ni auditorías.
Publish registra STARTED, sustituye solo versión/hash y comprueba filas, viajes distintos y ejecución destino.
Registra CLOSED/SUCCEEDED o FAILED y conserva gold_committed si el commit ya ocurrió.
Reutilizo el helper Delta existente, bajo un solo escritor operativo.
No hay transacción única entre tabla y auditoría; no modifiqué el coordinador.

## Consumo

Relacionaré el hecho con trips por trip_key; no añadiré un camino paralelo directo a rutas.
Las medidas horarias elegibles filtrarán timing_status y explicarán precisión y exclusiones.
Las ventanas de frecuencia permanecerán en su visual propio.
Este hecho es catálogo por viaje, no una expansión diaria.
Una selección de fecha necesita una medida o derivación explícita con servicios activos, sin relaciones bidireccionales entre hechos.
La [guía de ejecución](../gold_trip_timing_execution.md) conserva el siguiente paso.


## Verificación local

Pasaron diecisiete pruebas en 55,960 segundos con Spark 4.0.1 dentro del Docker offline existente.
El repositorio se montó en solo lectura y los datos sintéticos quedaron fuera de OneDrive.
Los tests cubren secuencias no consecutivas, horas mayores de 24, ausencia de extremos, precisión y plantillas con varias ventanas.
También verifican categorías excluyentes, viajes preservados, claves duplicadas, referencias huérfanas, horas negativas y ámbito histórico.
Las comprobaciones de metadata prueban versiones fijadas, deriva y bloqueo de una publicación fallida previa.
Validate no llamó al escritor ni a la auditoría; la publicación con dobles comprobó el ámbito y el cierre exitoso.
Las transformaciones usan Spark real; el IO Delta se sustituye por dobles.
No ejecuté una integración Delta nativa nueva ni publiqué esta entidad en Workspace.
Comprobé sintaxis Python, dos bloques del notebook sin resultados guardados, diecisiete campos de consumo y enlaces.


## Cierre de publicación y consumo

La ejecución Gold d39bc6b9-9cf2-478c-9830-0f72cd905b2a terminó SUCCEEDED y reconciled=true, según su resumen de publicación.
Importé la tabla mediante la conexión existente del modelo local y comprobé sus filtros y conteos con DAX.
La [evidencia del modelo](../power_bi_gold_import.md) conserva los resultados y decisiones de relación.
