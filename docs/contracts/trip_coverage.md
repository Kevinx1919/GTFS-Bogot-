# Mi contrato Gold: trip_coverage_v1

**Fecha:** 17 de noviembre de 2026.
**Estado:** validado y publicado en Workspace para 2026-09-29; importado y comprobado en Power BI el 19 de noviembre de 2026.
La salida implementada se llama gold_gtfs_trip_coverage.
No añado esta entidad Gold al registro de procesadores Silver.

## Definición de negocio

| Punto | Definición |
| --- | --- |
| 1. Pregunta | ¿Cuántos viajes declarados tienen visitas publicadas y qué contexto de frecuencias presentan? |
| 2. Una fila | Un trip_id declarado en trips Silver, dentro de una versión y un hash. |
| 3. Ubicaciones | Visitas Silver a paradas/plataformas; no añado estaciones padre ni otras ubicaciones sin visitas. |
| 4. Ausencias | Sin visitas produce un conteo derivado cero; las horas ausentes permanecen ausentes. No interpolo ni invento registros. |
| 5. Claves | source_feed_version + source_sha256 + trip_id. Las relaciones futuras con rutas y servicios conservarán el snapshot. |
| 6. Límites del reporte | Varias visitas no prueban recorrido completo. Ningún grupo representa operación observada; frecuencias y exactitud temporal requieren contexto propio. |

Es como revisar un itinerario antes de analizarlo: algunos viajes tienen una lista de paradas y otros no.
Conservo los itinerarios declarados aunque falte esa lista.

## Fuentes y alcance inicial

Uso silver_gtfs_trips, silver_gtfs_stop_times y silver_gtfs_frequencies del mismo snapshot.
La primera implementación trabajará con 2026-09-29 y el hash validado 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097.
Exigiré publicaciones compatibles con trips_v1, stop_times_v1 y frequencies_v1 para estas fuentes presentes.
Frequencies está publicado en este snapshot; no interpretaré su tabla perdida como ausencia válida de archivo.
La política para otro snapshot sin frequencies consultará la evidencia de archivos publicados.
No necesito service_dates para clasificar las visitas de un viaje declarado.
La fecha activa se añadirá posteriormente cuando la pregunta lo requiera.

## Campos de negocio implementados

| Campo | Tipo | Significado |
| --- | --- | --- |
| source_feed_version, source_sha256 | string | Identidad del snapshot. |
| trip_id | string | Viaje o plantilla declarados; no identifica un bus físico. |
| route_id, service_id | string | Contexto conservado desde trips, sin duplicar filas por calendario. |
| visit_count | long | Visitas publicadas del viaje; puede valer cero. |
| complete_time_pair_count | long | Visitas con llegada y salida presentes como segundos de servicio. |
| visits_without_complete_time_pair | long | visit_count menos complete_time_pair_count. |
| frequency_window_count | long | Ventanas publicadas del viaje, agregadas antes del join. |
| coverage_status | string | sin_visitas, una_visita o varias_visitas. |
| scheduling_context | string | sin_frecuencias, por_frecuencia u horario_exacto_por_frecuencia. |

La publicación añade gold_rule_version y gold_run_id como string, y gold_loaded_at_utc como timestamp UTC.
La tabla contiene catorce columnas.
Audit_gtfs_gold_runs conserva las versiones Delta y las ejecuciones fuente necesarias para reproducir el resultado.
No reutilizaré un silver_run_id como identificador de la ejecución Gold.

## Reglas

Agrupo stop_times por snapshot y trip_id antes del left join con trips.
Agrupo frequencies por la misma clave antes de unir sus ventanas.
Así una visita repetida a la misma parada conserva su multiplicidad válida.
Varias ventanas tampoco multiplican las filas de viajes.

| Condición | Clasificación |
| --- | --- |
| Cero visitas | sin_visitas. |
| Una visita | una_visita. |
| Dos o más visitas | varias_visitas. |
| Sin ventanas publicadas | sin_frecuencias. |
| Ventanas con exact_times_effective=0 | por_frecuencia. |
| Ventanas con exact_times_effective=1 | horario_exacto_por_frecuencia. |

Un contexto contradictorio produce diagnóstico y bloqueo; no elijo una interpretación arbitraria.
La vista previa usa contexto_inconsistente para hacer visible ese caso; no será un valor analítico publicado sin resolver.
Sin frequencies no significa que todas las horas sean exactas: stop_times conserva su propia semántica timepoint.
Una pareja de horas completa demuestra presencia, no exactitud ni cumplimiento operacional.
No asigno una elegibilidad universal: cada indicador posterior definirá sus requisitos.

## Reconciliación y publicación

La cantidad de filas Gold deberá igualar los viajes declarados del snapshot.
La clave completa deberá permanecer única.
La suma de visit_count deberá reconciliarse contra las visitas fuente del mismo snapshot.
La suma de ventanas deberá reconciliarse contra frequencies cuando el archivo esté publicado.
Los conteos derivados serán no negativos y complete_time_pair_count no superará visit_count.

La publicación fijará versiones Delta de entrada y comprobará la coherencia con sus auditorías.
No confundirá una dependencia ausente con un cero de negocio.
La escritura se limitará al snapshot seleccionado y preservará otros snapshots.
La reejecución no duplicará claves; no cambiará reglas ni datos Silver para conseguir ese resultado.
La validación sin publicación no escribirá tablas analíticas.

## Límites

No calculo duración del recorrido, salidas diarias, viajes operados, ocupación ni puntualidad desde esta clasificación.
Una sola visita con horas completas sigue sin permitir estudiar un recorrido entre dos paradas.
Las plantillas por frecuencia requieren sus ventanas para futuras estimaciones de oferta.
No uniré las visitas directamente a todos los puntos de trazado ni a todas las fechas activas.
La [vista previa](../trip_coverage_profile_2026.md) registra la evidencia disponible antes de implementar.

## Implementación local y entrada de ejecución

El módulo gtfs_gold/trip_coverage.py prepara la clasificación y reconcilia los conteos antes de publicar.
Comprueba la última auditoría vigente de cada fuente; no rescata un éxito antiguo tras un fallo posterior.
Fija las versiones Delta de la auditoría y las tres tablas Silver.
Una agregación técnica independiente reconcilia sus filas y metadatos con las publicaciones auditadas.
Después agrupa visitas y ventanas y valida la unicidad de viajes y los totales derivados.
No recoge millones de filas de negocio en el driver ni usa UDF de Python.
No activa persist/cache obligatorio.

Notebook 20 tiene dos bloques y mode=validate por defecto.
Validate no escribe tablas analíticas ni auditorías Gold.
Publish registra STARTED, reemplaza únicamente el ámbito versión/hash y comprueba su resultado.
Después registra CLOSED / SUCCEEDED; un error registra CLOSED / FAILED cuando el proceso puede cerrarlo.
Una interrupción del proceso puede dejar un STARTED sin cierre.
Si el error ocurre después del commit, la auditoría conserva gold_committed=true y no promete rollback automático.
El historial de otros snapshots permanece fuera del replaceWhere.
Mantengo un solo escritor; no implementé un bloqueo distribuido entre Jobs.

La publicación reutiliza el helper técnico de escritura por ámbito y la inserción inmutable de auditorías existentes.
No usa la auditoría Silver para registrar ejecuciones Gold.
El Job principal todavía no llama al publicador Gold.

## Pruebas ejecutadas

Pasaron 135 pruebas unitarias y dos integraciones seleccionadas de cobertura con Spark/Delta reales.
Las fixtures cubren cero, una y varias visitas, horas intermedias ausentes y múltiples ventanas del mismo viaje.
La publicación repetida conserva claves únicas y mantiene exactamente otro snapshot, incluidas sus columnas técnicas.
La deriva de un run_id fuente y un fallo Silver posterior bloquean Gold.
Validate no crea la tabla Gold ni su auditoría.
Un fallo de preparación durante publish conserva STARTED y CLOSED / FAILED sin tabla analítica nueva.
No ejecuté una publicación real en Workspace durante esta revisión.

## Primera publicación comprobada — 19 de noviembre de 2026

Validé notebook 20 con persisted=false y reconciled=true.
Publiqué con gold_run_id 8d48f208-89a1-4c7b-9369-136be92d7a51 y comprobé CLOSED/SUCCEEDED.
Gold conserva 181060 viajes únicos, 9408893 visitas, catorce ventanas y cero filas inválidas.
Las categorías concilian 739 sin_visitas, 61 una_visita y 180260 varias_visitas.
La importación Power BI utiliza once columnas de negocio; la evidencia completa permanece en Databricks.
El Job principal todavía no llama automáticamente a este publicador.
