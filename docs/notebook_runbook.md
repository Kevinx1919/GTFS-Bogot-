# Runbook de notebooks

## Convención

Los notebooks se comentan por bloque, no línea por línea. Cada bloque documentado indica propósito, entradas, salida, efecto persistente y validación. Los comentarios dentro del código aclaran decisiones no obvias.

## Notebook 02 — `02_raw_static_gtfs_ingestion`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración | Define catálogo, schema, Volume y versiones fuente. | Valores de entorno y URLs oficiales. | Variables de sesión. | Se muestran las versiones configuradas. |
| Descarga | Obtiene el ZIP de la versión solicitada y registra metadata de la corrida. | URL resuelta desde la tabla de control. | ZIP y metadata en memoria. | HTTP 200, tamaño y SHA-256. |
| Validación | Comprueba estructura GTFS mínima. | Bytes del ZIP. | Resultado en memoria. | ZIP, archivos esenciales y calendario válidos. |
| Raw | Conserva evidencia original e idempotente. | ZIP validado, hash y metadata. | ZIP y manifiesto JSON en `raw_gtfs`. | Reintento del mismo `run_id`, ruta por versión/hash y manifest legible. |
| Verificación | Comprueba persistencia. | Rutas Raw creadas. | No escribe. | `path`, `name`, `size`, `modificationTime`. |

Resultado: la versión `2025-10-28` se almacenó con HTTP 200 y hash `07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952`.

## Notebook 03 — `03_bronze_static_gtfs`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Referencia a Raw | Selecciona un snapshot GTFS validado. | Versión y SHA-256 del manifest. | Variables de sesión. | Se lista el directorio del ZIP en Raw. |
| Extracción a staging | Extrae de forma idempotente los `.txt` del ZIP para lectura distribuida. | ZIP Raw. | Archivos y manifiesto de extracción en `staging_gtfs`. | Lista de archivos, tamaño descomprimido y estado de existencia. |
| Lectura de rutas | Lee `routes.txt` conservando sus columnas fuente como texto. | `routes.txt` en Staging. | DataFrame con procedencia técnica. | Esquema visible y 676 rutas en el snapshot actual. |
| Escritura Bronze | Persiste las rutas como tabla Delta administrada. | DataFrame de rutas con hash fuente. | `workspace.gtfs_bogota.bronze_gtfs_routes`. | Conteo del snapshot, `describe detail` e historial Delta. |
| Deriva de esquema | Compara columnas del archivo actual contra la tabla histórica. | `routes.txt` y `bronze_gtfs_routes`. | Reporte de columnas omitidas o nuevas. | Conteo de `route_desc` no nulo por versión. |

## Notebook 04 — `04_bronze_static_gtfs_reference_entities`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración | Selecciona el mismo snapshot validado en Staging. | Versión y SHA-256. | Variables de sesión. | Directorio de Staging visible. |
| Contrato | Declara columnas mínimas y diferencia archivos requeridos de opcionales. | Definiciones del feed. | Contratos en memoria. | Columnas requeridas y ausencia explícita de opcionales. |
| Carga Bronze | Lee y escribe entidades disponibles, incluida metadata de feed si existe. | Archivos `.txt` de Staging. | Tablas `bronze_gtfs_*`. | Conteo, idempotencia, opcionales omitidos y evolución de esquema auditada. |
| Verificación | Inspecciona las paradas persistidas. | `bronze_gtfs_stops`. | No escribe. | Muestra de filas y `describe detail`. |

## Notebook 05 — `05_bronze_static_gtfs_operational_entities`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración y contrato | Identifica el snapshot y las columnas mínimas de las entidades grandes. | `shapes.txt` y `stop_times.txt`. | Variables y contratos en memoria. | Archivos y encabezados válidos. |
| Carga de geometrías | Persiste la geometría planificada de recorridos. | `shapes.txt` en Staging. | `bronze_gtfs_shapes`. | Conteo, idempotencia y evolución explícita de esquema. |
| Carga de horarios | Persiste la secuencia de paradas por viaje. | `stop_times.txt` en Staging. | `bronze_gtfs_stop_times`. | Conteo, muestra ordenada, `describe detail` y evolución explícita de esquema. |

Resultado: para la versión `2025-10-28`, se validaron 909.878 filas en
`bronze_gtfs_shapes` y 5.698.892 filas en `bronze_gtfs_stop_times`.

## Notebook 06 — `06_discover_static_gtfs_catalog`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración | Declara el portal oficial, grupo GTFS, tablas y modo de selección. | Identificador público, modo y fechas opcionales. | Variables de sesión y `catalog_run_id`. | Endpoint, corrida y modo visibles. |
| Consulta | Recorre las páginas del catálogo ArcGIS público. | Respuesta JSON del grupo oficial. | Ítems del catálogo en memoria. | HTTP exitoso, sin error ArcGIS y al menos un ítem. |
| Contrato | Conserva solo ítems con versión GTFS fechada y normaliza metadata. | Ítems descubiertos. | DataFrame con esquema explícito. | Patrón de fecha, ítem único y URL directa identificada. |
| Control y auditoría | Mantiene el estado actual y el historial de observaciones. | Catálogo normalizado. | Tablas Delta de control y auditoría. | `MERGE` por ítem y auditoría append-only. |
| Plan | Selecciona una, varias o la última versión descargable sin Bronze. | Control, `bronze_gtfs_routes` y parámetros. | Plan para `latest_uningested`, `explicit_version` o `backfill_range`. | Solo ZIP directo, sin carga Bronze y con fechas válidas. |

## Notebook 07 — `07_validate_bronze_gtfs_snapshot`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Parámetros | Identifica un único snapshot ya cargado. | Versión GTFS y SHA-256. | Variables de sesión y `quality_run_id`. | Formato de versión y hash; ruta de Staging definida. |
| Contrato | Declara entidades requeridas, opcionales e identificadores críticos. | Contrato GTFS del proyecto. | Reglas en memoria. | No inventa datos si falta un archivo opcional. |
| Utilidades | Define esquemas explícitos y funciones de auditoría. | Metadatos de la corrida. | Filas de calidad acumuladas en memoria. | Esquemas de auditoría sin inferencia. |
| Presencia y procedencia | Comprueba Staging, filas Bronze y versión fuente por entidad. | Snapshot de Staging y tablas Bronze. | Evidencia de completitud y linaje. | Los archivos requeridos y sus tablas deben tener filas. |
| Identificadores y relaciones | Revisa IDs críticos y relaciones GTFS básicas. | `routes`, `stops`, `trips`, `stop_times`, calendarios. | Fallos por IDs vacíos; advertencias por huérfanos fuente. | IDs no nulos; huérfanos registrados, no eliminados. |
| Evolución de esquema | Guarda una observación por archivo y hash; compara contra la versión previa. | Encabezados de Staging e historial de observaciones. | `audit_gtfs_source_schema_observations`. | Campos nuevos o retirados aparecen como advertencia revisable. |
| Resultado | Persiste los checks y decide el estado de la corrida. | Todas las filas de auditoría. | `audit_gtfs_bronze_snapshot_quality` y task values para el Job. | `FAIL` con severidad `BLOCKING` detiene el Workflow después de registrar evidencia. |

Resultado esperado: `PASSED` si las reglas bloqueantes se cumplen, `WARNING` si hay
cambios de esquema o relaciones huérfanas que requieren revisión, y `FAILED` si
falta evidencia obligatoria o un identificador crítico no es válido.
