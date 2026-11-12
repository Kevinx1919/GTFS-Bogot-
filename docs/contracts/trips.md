# Mi contrato Silver trips_v1

**Fecha:** 11 de noviembre de 2026. **Estado:** implementación y despliegue funcional completados. Las 37 pruebas seleccionadas pasaron sin omisiones. El despliegue funcional quedó confirmado el 12 de noviembre de 2026. Conservo el [cierre de ejecución](../silver_execution.md#cierre-de-la-ejecución-de-trips). El [informe](../trips_profile_2025_2026.md) conserva los resultados medidos.

## Grano e identidad

Una fila identifica un viaje del GTFS dentro de versión/hash. La clave validada es source_feed_version + source_sha256 + trip_id. No es una identidad de bus físico. Un viaje referenciado por frequencies puede actuar como plantilla.

La fuente es trips.txt y bronze_gtfs_trips. La salida implementada es silver_gtfs_trips. El procesador fija la versión Delta de Bronze y de cada dependencia Silver. Registra esas versiones en la auditoría. Valida procedencia y encabezado antes de transformar.

## Campos de negocio del primer incremento

| Campo | Tipo Silver | Regla |
| --- | --- | --- |
| trip_id | string | Obligatorio. Clave única dentro del snapshot. Conservo ceros iniciales y contenido. |
| route_id | string | Obligatorio. Debe resolver en routes Silver del mismo snapshot. |
| service_id | string | Obligatorio. Debe resolver en los calendarios publicados del mismo snapshot. |
| shape_id | string nullable | Valido su referencia cuando tiene contenido. La obligatoriedad depende del comportamiento continuo. |
| trip_headsign | string nullable | Opcional. Conservo texto informado y convierto ausencias admitidas a null. |

La [referencia GTFS](https://gtfs.org/documentation/schedule/reference/#tripstxt) establece la semántica. La v1 implementada admite estos cinco campos. Un campo nuevo exigirá revisar el contrato. No crearé direction_id, block_id ni atributos de accesibilidad mediante inferencias.

Trip_headsign no existe en 2025. Existe sin contenido no blanco en 2026, según la comparación Staging/Bronze. Conservo esa diferencia en source_columns. Su ausencia válida no rechazará filas ni generará cientos de miles de advertencias repetidas.

No reemplazaré el texto ausente con nombres de rutas. Conservaré texto no blanco sin normalizar su contenido. Revisaré caracteres de control. Los identificadores no admitirán espacios extremos ni cambios de identidad.

## Dependencias y cardinalidad

Routes Silver debe pertenecer al mismo snapshot y a routes_v1. Los servicios proceden de calendar y calendar_dates según los archivos publicados. Exijo sus contratos v1. No exigiré días activos dentro de service_dates para reconocer un service_id.

Uso un catálogo único de shape_id desde shape_points_v1 Silver. No uniré viajes directamente con cada punto. Los joins deberán conservar el conteo de viajes.

Los encabezados actuales no publican comportamiento continuo en routes o stop_times. Compruebo ese alcance mediante audit_gtfs_source_schema_observations. Exijo observaciones de routes, stop_times y al menos un calendario. Si aparecen columnas continuous_pickup o continuous_drop_off, bloqueo la preparación. No interpreto sus valores en esta v1. Reviso el contrato antes de admitir ese alcance nuevo. La falta de metadata o sus variantes ambiguas también bloquean la preparación.

Frequencies no es una dependencia para publicar trips. Su revisión actual solo describe relaciones. La futura tabla frequencies validará sus referencias contra trips Silver. No añadiré un indicador de frecuencia inferido desde Bronze a esta v1.

## Rechazos, copias y ausencias

Consolido solo copias de negocio idénticas. Una clave con atributos diferentes conservará sus variantes en cuarentena. Los conflictos bloquearán el snapshot completo. No deduplicaré por ruta, servicio o trazado.

Una clave obligatoria vacía, procedencia incoherente o referencia requerida sin resolver generará rechazo. Conservaré la fila original y el motivo. Una ausencia opcional válida permanecerá null. Los errores no se convertirán silenciosamente en ausencias.

Conservo las columnas técnicas, source_columns, la versión de reglas y los campos del escritor. La salida contiene 13 columnas físicas. La reejecución deberá mantener claves y valores de negocio. Los demás snapshots permanecerán intactos.

## Verificación antes de publicar

Preparé fixtures para ausencias, copias, conflictos y referencias. Las pruebas cubren dependencias del mismo snapshot y campos opcionales. Aceptaron un servicio sin depender del horizonte. Los joins no multiplicaron viajes por puntos o excepciones.

La integración Delta comprobó lectura sin escritura, publicación, reintento, cuarentena e histórico. Reutilicé el entorno existente. Las 37 pruebas seleccionadas pasaron sin omisiones.

## Límites de análisis

Trip_id no identifica un vehículo observado. El conteo de filas no demuestra viajes operados. Las frecuencias y fechas activas deberán intervenir según la pregunta Gold. Stop_times aportará paradas y horas cuando complete su contrato.

No corregiré las fechas de 2023 de los calendarios 2025 desde trips. La existencia de un servicio no resuelve su alcance temporal. Gold conservará esa limitación.


## Resolución de fuentes y errores

Leo encabezados auditados del mismo par versión/hash. Si calendar.txt está publicado, exijo calendar Silver del mismo snapshot. Aplico la misma condición a calendar_dates.txt. Si shapes.txt está publicado, exijo shape_points Silver. Si no está publicado, un shape_id no vacío queda como referencia no resuelta. Una ausencia opcional válida puede permanecer null.

Compruebo tipos de claves, versión de reglas, unicidad y contenido de los catálogos. Calendar_dates valida su clave service_id + date. Shape_points valida shape_id + shape_pt_sequence. Después extraigo IDs distintos para los joins. No vuelvo a validar toda la geometría ni el calendario completo desde trips.

Una sola acción recupera entre dos y cuatro resúmenes pequeños de dependencias. No trae registros de viajes al driver. La selección de archivos usa como máximo cinco observaciones de metadata. No constituye una transacción conjunta entre tablas.

TRIP_ID_CONFLICT conserva las variantes de una misma clave. ROUTE_ID_NOT_FOUND, SERVICE_ID_NOT_FOUND y SHAPE_ID_NOT_FOUND identifican referencias no resueltas. Los IDs vacíos, espacios extremos y caracteres de control tienen códigos propios. El texto opcional no blanco conserva sus espacios. No normalizo títulos ni IDs.

Los errores de filas llegan a cuarentena y bloquean el snapshot completo. Los errores de encabezado, alcance o dependencia ocurren antes de preparar candidatos. En esos casos el Job conserva el error; no fabrico filas de cuarentena ni una publicación parcial.

El resumen puede mostrar warning_rows=0 con trip_headsign ausente. Esa ausencia es válida. Las limitaciones temporales de los calendarios permanecen documentadas. Cero advertencias de trips no prueba operación real ni fechas activas correctas.
