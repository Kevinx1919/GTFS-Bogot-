# Mis contratos Silver calendar_v1 y calendar_dates_v1

**Fecha:** 10 de noviembre de 2026. **Estado:** calendar_v1 y calendar_dates_v1 ejecutados y publicados en Databricks. Amplié el Job con ambas tareas, comprobé físicamente las dos tablas Silver y consulté sus datos. El [cierre de ejecución](../silver_execution.md#cierre-de-la-ejecución-de-calendarios) registra el alcance de esta comprobación. El [perfil real](../calendars_profile_2025_2026.md) conserva las fechas originales; el [despliegue](../silver_execution.md#despliegue-de-calendarios) registra pruebas y pasos pendientes.

La [explicación de contratos y cuarentena](../data_contracts_and_quarantine.md) distingue los requisitos oficiales, lo que publicó cada archivo y las decisiones propias del proyecto.

## Grano y tipos

Todas las claves incluyen source_feed_version y source_sha256. No uso el número de servicio como identidad entre años ni como agency_id.

| Entidad | Campo | Tipo Silver | Regla |
| --- | --- | --- | --- |
| calendar | service_id | string | Requerido; conserva ceros y forma original; sin espacios extremos ni controles Unicode. |
| calendar | monday, tuesday, wednesday, thursday, friday, saturday, sunday | int | Requeridos; dominio 0/1. |
| calendar | start_date, end_date | date | Requeridas; ocho dígitos YYYYMMDD, fecha válida con año 0001–9999 e inicio no posterior al final. Intervalo inclusivo. |
| calendar_dates | service_id | string | Requerido; servicio dentro del snapshot. |
| calendar_dates | date | date | Requerida; formato y validez de fecha iguales a calendar. |
| calendar_dates | exception_type | int | Requerido; 1 añade y 2 retira servicio. |

Calendar usa service_id como clave dentro del snapshot; calendar_dates usa service_id + date. La preparación, las ventanas, el escritor y la cuarentena reconocen todas las columnas de clave, sin un ID concatenado. Un servicio puede tener muchas fechas sin ser un duplicado.

Los enteros admiten ceros iniciales, como los otros contratos; rechazo signos, decimales, desbordamientos y espacios. Las fechas usan try_cast sobre una representación ISO construida a partir del texto fuente, con comprobación separada de formato: un fallo nunca se acepta como null. El encabezado exige todos los campos conocidos y bloquea extensiones o nombres repetidos. Un archivo publicado pero sin filas requiere revisión; esta versión no publica una entidad vacía.

## Duplicados, procedencia y errores

Comparo valores fuente antes de convertir tipos. Consolido copias válidas idénticas conservando su multiplicidad y el timestamp Bronze más antiguo. Dos variantes de una misma clave se rechazan aunque sus valores coincidan después del cast. Si una fecha contiene a la vez añadir y retirar, no elijo una fila al azar.

No deduplico distintos servicios por compartir patrón semanal. Rechazo requeridos vacíos, controles Unicode, IDs con espacios extremos, fechas imposibles, intervalos invertidos, códigos inválidos y procedencia incoherente. Selecciono por hash y compruebo versión, ruta y timestamp de las filas. La sesión usa UTC y las columnas fuente deben seguir como string en Bronze.

Una fila rechazada bloquea la publicación de su entidad/snapshot; la cuarentena conserva campos de clave originales, JSON fuente y motivos. Una dependencia inválida falla antes de producir un resultado de validación y su error queda en el Job, como en routes.

## Archivos condicionales y dependencia semanal

Calendar se procesa sin exigir calendar_dates. Calendar_dates admite dos modalidades:

- Si calendar.txt está publicado en Staging, leo una versión Delta fijada de silver_gtfs_calendar del mismo snapshot. Exijo calendar_v1, claves únicas y fechas válidas; cada service_id de excepciones debe resolver en esa dependencia.
- Si calendar.txt no está publicado, proceso las fechas sin exigir Silver calendar. Si Bronze contiene filas de calendar para ese hash pero falta el archivo en Staging, detengo la ejecución: una pérdida de archivo no se interpreta como ausencia legítima.

No creo filas para un archivo ausente. La plantilla incluye ambas entidades porque los dos snapshots actuales publican ambos TXT; si una futura versión omite uno, su planificación debe omitir la entidad ausente y ajustar el orden aplicable. La plantilla fija no descubre nuevas versiones ni resuelve por sí sola esa planificación.

## Advertencias temporales explícitas

| Código | Cuándo se registra | Consecuencia |
| --- | --- | --- |
| CALENDAR_INTERVAL_OVER_TEN_YEARS | El final supera start_date más 120 meses. | Advertencia de alcance; umbral del proyecto, no prohibición GTFS. No recorto fechas. |
| CALENDAR_WITHOUT_WEEKLY_SERVICE | Los siete indicadores son cero. | Advertencia; las excepciones pueden declarar días activos. |
| EXCEPTION_YEAR_DIFFERS_FROM_SNAPSHOT | El año de date difiere del año de publicación. | Advertencia de contexto, no error de formato. |
| EXCEPTION_OUTSIDE_CALENDAR_INTERVAL | La excepción está fuera del intervalo semanal de su servicio. | Advertencia; una adición puede extender el patrón. |
| REMOVAL_WITHOUT_WEEKLY_CALENDAR | Solo hay calendar_dates y una fila retira servicio. | Advertencia de posible regla sin efecto sobre una base vacía. |

Conservo el intervalo 2000–2099 y las excepciones de 2023 del snapshot 2025. No traslado festivos a 2025 ni afirmo que su calendario esté completo para ese año. Estos avisos no bloquean por sí solos Silver; Gold deberá explicar cobertura y límites.

El resumen añade interval_over_ten_years_rows y no_weekly_service_rows para calendar; different_snapshot_year_rows, calendar_mode y, cuando hay patrón, outside_calendar_interval_rows para calendar_dates. Los contadores adicionales se calculan sobre candidatos únicos válidos. warning_rows cuenta filas fuente con algún aviso, no suma motivos. La auditoría conserva su esquema anterior y warning_rows; no añado columnas a tablas compartidas.

## Publicación y siguiente derivación

Reutilizo notebook 10, escritor, auditoría e idempotencia por versión/hash. Calendar tiene 18 columnas físicas y calendar_dates 11, contando procedencia, presencia de columnas, regla y ejecución. Sus cuarentenas usan el ID y, para excepciones, la fecha fuente como string, de modo que una fecha inválida siga siendo legible.

La plantilla serializa agency → routes → stops → calendar → calendar_dates. El orden de calendar después de stops es operativo; la dependencia de excepciones sobre calendar es condicional al archivo publicado. Cada entidad se escribe por separado: no hay una transacción conjunta entre ambas ni con auditoría/cuarentena. El Job detenido y una sola ejecución escritora evitan carreras; un fallo posterior al commit mantiene silver_committed para revisión.

Service_dates vendrá después con un horizonte acordado y una fila por snapshot, servicio y fecha activa. Este incremento no construye esa tabla, no expande horarios y no modifica las seis definiciones de negocio exigidas a Gold.

Referencia de semántica: [GTFS calendar.txt](https://gtfs.org/documentation/schedule/reference/#calendartxt) y [calendar_dates.txt](https://gtfs.org/documentation/schedule/reference/#calendar_datestxt). Los umbrales y la política de publicación pertenecen al proyecto.
