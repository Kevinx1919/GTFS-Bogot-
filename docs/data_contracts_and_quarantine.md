# Cómo construyo mis contratos y para qué uso cuarentena

## De dónde sale un contrato Silver

No recibo un contrato Silver terminado desde la API. Lo construyo cruzando tres referencias:

| Referencia | Qué me dice | Ejemplo de calendarios |
| --- | --- | --- |
| Especificación oficial GTFS | Significado, obligatoriedad, dominios y claves de los campos. | Los siete días de calendar son indicadores 0/1; exception_type distingue añadir y retirar servicio. |
| Archivo publicado y auditoría del encabezado | Qué campos llegaron realmente en cada snapshot. | Calendar publicó diez campos y calendar_dates tres, en las dos versiones revisadas. |
| Decisiones del proyecto | Tipos físicos de Silver, trazabilidad y qué hago ante problemas. | Uso date en Spark, guardo versión/hash y bloqueo la publicación de una entidad cuando hay errores. |

En la [referencia GTFS](https://gtfs.org/documentation/schedule/reference/#calendartxt), la columna Presence indica si un campo es Required, Optional o Conditionally Required. El encabezado del TXT solo enumera sus nombres; no contiene esas explicaciones. La API o catálogo permite localizar y obtener el recurso; la interpretación de estos TXT procede de GTFS.

En calendar, los diez campos son requeridos cuando el archivo está publicado. En calendar_dates, lo son service_id, date y exception_type. Los archivos son condicionales: el estándar permite representar el servicio con las fuentes disponibles según la modalidad. Que un archivo sea opcional o condicional no vuelve opcionales todos sus campos cuando sí existe.

Distingo dos comprobaciones: si falta un campo requerido, reviso la estructura; si el campo existe pero una fila lo deja vacío, reviso el contenido de esa fila. Una columna nueva, incluso si es válida en GTFS, requiere ampliar el contrato que implementé antes de aceptarla automáticamente.

## Qué reglas son decisiones mías

El [contrato de calendarios](contracts/calendars.md) define esas decisiones explícitamente. Guardar IDs como string evita perder ceros iniciales; convertir fechas a date permite comparar fechas reales. Los datos fuente y sus encabezados siguen disponibles para explicar las conversiones.

La advertencia de intervalos mayores de 120 meses es una regla del proyecto para hacer visible un alcance amplio. No es una prohibición GTFS. Tampoco es un error automático que una fecha de servicio pertenezca a otro año que el ZIP: por eso conservo las excepciones de 2023 y aviso de su limitación para analizar 2025.

El umbral, la política de bloquear un snapshot, la auditoría y los nombres de tablas no vienen prescritos por GTFS. Son parte de cómo implemento la calidad y la operación del lakehouse.

## Para qué sirve la cuarentena

La uso como una mesa de revisión: conserva registros que no puedo publicar con las reglas actuales, junto con la evidencia para explicar el motivo. No corrige datos automáticamente ni reemplaza Bronze.

Por ejemplo, si encuentro dos filas con el mismo servicio y fecha, una con añadir servicio y otra con retirarlo, la clave tiene un conflicto. Conservo las dos variantes con SERVICE_KEY_CONFLICT en quarantine_gtfs_calendar_dates. Si la fecha fuente fuera 20260230, conservo ese texto y el motivo DATE_INVALID; no lo transformo silenciosamente en una ausencia válida.

La fila de cuarentena guarda los campos de clave originales, original_row_json, error_codes, versión de reglas, versión/hash fuente, ejecución y timestamp. input_copies conserva cuántas filas de entrada representa un rechazo agrupado. No guardo solo el valor ya convertido: necesito poder ver qué llegó.

## Qué ocurre al ejecutar

- Con mode=validate obtengo los conteos y resultados de validación en memoria. No escribo Silver, cuarentena ni auditoría.
- Con mode=publish registro auditoría y cuarentena. Si hay errores de filas, el intento queda REJECTED y no reemplazo el snapshot en Silver. Las filas aceptadas de ese intento tampoco se publican parcialmente.
- Si había una Silver anterior, queda intacta ante ese rechazo. Si es la primera carga, no creo una Silver parcial.
- Una advertencia temporal no envía por sí sola la fila a cuarentena: el dato puede publicarse conservando el aviso en sus métricas.
- Si falta un encabezado o una dependencia antes de obtener el resultado de validación, el error aparece en el Job; no afirmo que todo fallo produzca filas de cuarentena.

Cada entidad y snapshot se escribe por separado. Si calendar ya se publicó y después fallan sus excepciones, no hay una transacción conjunta que deshaga ambas tablas. El Job conserva el error y la publicación previa debe interpretarse con su estado de auditoría.

Una cuarentena vacía puede ser normal. Una no vacía puede contener intentos anteriores: siempre reviso snapshot y ejecución, no solo el total histórico de la tabla.

## Cómo reviso un rechazo de excepciones

Después de un intento publish que haya creado la tabla puedo consultar:

```sql
select source_feed_version, source_sha256, silver_run_id,
       service_id, date, error_codes, input_copies, original_row_json
from workspace.gtfs_bogota.quarantine_gtfs_calendar_dates
where source_feed_version = '2025-10-28'
  and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952'
order by silver_run_id, service_id, date;
```

Relaciono silver_run_id con audit_gtfs_silver_runs y reviso el motivo. La solución puede ser corregir una transformación, ampliar una regla justificada o recibir una nueva versión de la fuente. No edito el ZIP raw para ocultar el problema ni elimino la evidencia de cuarentena para hacer pasar una ejecución.

Referencias: [calendar.txt](https://gtfs.org/documentation/schedule/reference/#calendartxt), [calendar_dates.txt](https://gtfs.org/documentation/schedule/reference/#calendar_datestxt), [contratos implementados](contracts/calendars.md) y [guía de ejecución](silver_execution.md#despliegue-de-calendarios).
