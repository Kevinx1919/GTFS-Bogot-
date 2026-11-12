# Mi contrato derivado service_dates_v1

**Fecha:** 11 de noviembre de 2026. **Estado:** implementación y configuración probadas localmente. La vista previa SQL está ejecutada; las 24 pruebas seleccionadas pasaron sin omisiones con Spark 4.0.1 y Delta 4.0.0, incluidas las ocho nuevas y las regresiones de calendarios y del lector compartido. Ya publiqué la derivación en Databricks y consulté sus datos: 1.403 filas, 1.403 claves distintas y siete servicios, entre 2026-01-01 y 2026-12-31. El [cierre de ejecución](../silver_execution.md#cierre-de-la-ejecución-de-service_dates) conserva la evidencia y su alcance.

## Horizonte, fuentes y grano

Acordé empezar solo por 2026: snapshot 2026-09-29, SHA-256 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097, del 2026-01-01 al 2026-12-31. No traslado las excepciones de 2023 a otro año ni calculo todo 2000–2099.

Una fila es un servicio activo en una fecha dentro del snapshot. La clave es source_feed_version + source_sha256 + service_id + service_date. No la uso para decidir si existe un servicio al validar trips: su catálogo de IDs no depende de tener días activos en esta ventana.

Los parámetros window_start y window_end son obligatorios para la derivación. La v1 acepta entre 1 y 366 días inclusivos, como protección operativa explícita, no como regla GTFS ni como recorte silencioso. Cambiar el horizonte ya publicado para el mismo snapshot requiere una migración; una reejecución no puede eliminar días de una ventana distinta por accidente.

## Dependencias y trazabilidad

Leo la auditoría de encabezados para saber qué fuentes fueron publicadas. Exijo sus correspondientes tablas Silver validadas del mismo snapshot, con tipos, claves y marcadores calendar_v1/calendar_dates_v1 correctos. Admite solo patrón, solo excepciones o ambas fuentes según lo publicado; no inventa una fuente ausente ni ignora una declarada pero no publicada en Silver.

Fijo una versión Delta de cada tabla antes de calcular. input_versions_json y la metadata de auditoría guardan tablas y versiones usadas. DerivedSnapshotSpec representa la derivación sin source_path: service_dates no es otro TXT ni otro archivo Raw.

## Esquema de salida

| Campo | Tipo | Significado |
| --- | --- | --- |
| service_id | string | Servicio fuente sin normalizar su identidad. |
| service_date | date | Día activo después de aplicar excepciones. |
| activation_source | string | weekly_pattern o calendar_date_addition. Una adición explícita prevalece como procedencia aunque el patrón ya estuviera activo. |
| weekly_pattern_active | boolean | Si el patrón semanal ya activaba ese día antes de las excepciones. |
| source_feed_version, source_sha256 | string | Identidad del snapshot fuente. |
| analysis_window_start, analysis_window_end | date | Horizonte explícito, repetido para identificar el alcance de cada fila. |
| source_temporal_warning | boolean | Propaga un intervalo mayor de 120 meses o excepciones de año distinto al snapshot. |
| input_versions_json | string JSON | Tablas y versiones Delta de las fuentes realmente usadas. |
| silver_rule_version | string | service_dates_v1. |
| silver_run_id, silver_loaded_at_utc | string / timestamp | Ejecución y carga UTC añadidas por el escritor común. |

Son 13 columnas físicas. No atribuyo a esta tabla source_file_path, bronze_loaded_at_utc ni un encabezado TXT propios. La trazabilidad de archivos originales se consulta a través de las fuentes Silver y Bronze.

## Algoritmo y reconciliación

Expando el patrón solo dentro de la intersección de su intervalo y el horizonte. Uno las adiciones como conjunto y retiro las bajas. Una adición repetida sobre un día ya activo y una baja de un día inactivo no cambian dos veces el resultado.

Registro weekly_service_days, added_new_days y removed_active_days y verifico: activos = patrón + adiciones nuevas - retiradas efectivas. Registro por separado filas de las dos fuentes y reglas dentro/fuera de ventana.

En la auditoría de esta entidad, input_rows es el número de filas derivadas que entra a la validación/publicación, después de aplicar el calendario. No son las siete filas de calendar más las 133 reglas: sus granos son distintos. Las métricas fuente aparecen por separado en el resumen y las versiones permiten reproducirlas.

No consolido silenciosamente duplicados de las fuentes Silver: son un incumplimiento de su contrato y detienen la derivación. Los avisos temporales se propagan sin modificar fechas. Una salida válida pero vacía detiene la publicación en esta v1; no borra una Silver anterior ni se etiqueta como prueba de que el GTFS fuente sea inválido.

## Publicación y límites

Reutilizo notebook 10 y el escritor común. Validate no escribe; publish sustituye solo el snapshot después de comprobar que su horizonte coincide con el ya publicado. Las demás versiones permanecen intactas. No hay una transacción conjunta entre fuentes, destino, cuarentena y auditoría.

La cuarentena derivada puede quedar vacía: los datos de salida son construidos y las fuentes se comprueban antes. Una fuente curada inválida falla antes de obtener candidatos; el error aparece en el Job, sin fabricar registros rechazados de una derivación que no llegó a calcularse.

El [notebook 13](../../databricks/notebooks/silver/13_preview_gtfs_service_dates.ipynb) es exploración, no una tarea del Job. La plantilla añade publish_service_dates después de publish_calendar_dates y un único work item 2026. Las pruebas nativas ya pasaron y la primera publicación en Workspace está comprobada mediante la consulta del cierre.

El [informe](../service_dates_preview.md) conserva la vista previa de 1.403 pares activos en 2026; la consulta posterior de la tabla publicada confirmó ese total. Eso no mide operación, pasajeros, ocupación ni cantidad de viajes. Gold seguirá requiriendo su ficha de negocio y las uniones correctas con viajes/horarios.
