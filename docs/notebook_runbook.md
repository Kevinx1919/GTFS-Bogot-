# Runbook de notebooks

## Convención

Los notebooks se comentan por bloque, no línea por línea. Cada bloque documentado indica propósito, entradas, salida, efecto persistente y validación. Los comentarios dentro del código aclaran decisiones no obvias.

## Notebook 02 — `02_raw_static_gtfs_ingestion`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración | Define catálogo, schema, Volume y versiones fuente. | Valores de entorno y URLs oficiales. | Variables de sesión. | Se muestran las versiones configuradas. |
| Descarga | Obtiene el ZIP de la versión solicitada y registra metadata de la corrida. | URL resuelta desde la tabla de control. | ZIP y metadata en memoria. | HTTP 200, tamaño y SHA-256. |
| Validación | Comprueba estructura GTFS mínima. | Bytes del ZIP. | Resultado visible y error si es inválido, antes de persistir. | ZIP, archivos esenciales y al menos un calendario válidos. |
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
| Contrato | Declara columnas mínimas y presencia requerida, opcional o por grupo. | Definiciones del feed. | Contratos en memoria. | Al menos un calendario; columnas semanales si existe calendar.txt; ausencia explícita de opcionales. |
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
| Presencia y procedencia | Comprueba Staging, filas Bronze y versión fuente por entidad. | Snapshot de Staging y tablas Bronze. | Evidencia de completitud y linaje. | Al menos un calendario; filas para los archivos publicados; cero versiones nulas o distintas; cero filas atribuidas a un archivo ausente. |
| Identificadores y relaciones | Revisa IDs críticos y relaciones GTFS básicas. | `routes`, `stops`, `trips`, `stop_times`, calendarios disponibles. | Fallos por IDs vacíos; advertencias por huérfanos fuente. | IDs no nulos; servicios comprobados con uno o ambos calendarios; huérfanos registrados, no eliminados. |
| Evolución de esquema | Guarda una observación por archivo y hash; compara contra la versión previa. | Encabezados de Staging e historial de observaciones. | `audit_gtfs_source_schema_observations`. | Campos nuevos o retirados aparecen como advertencia revisable. |
| Resultado | Persiste los checks y decide el estado de la corrida. | Todas las filas de auditoría. | `audit_gtfs_bronze_snapshot_quality` y task values para el Job. | `FAIL` con severidad `BLOCKING` detiene el Workflow después de registrar evidencia. |

Resultado esperado: `PASSED` si las reglas bloqueantes se cumplen, `WARNING` si hay
cambios de esquema o relaciones huérfanas que requieren revisión, y `FAILED` si
falta evidencia obligatoria o un identificador crítico no es válido.

## Correcciones previas a Silver — Hito 09

| Notebook / bloque | Propósito y entradas | Salida y efecto persistente | Cómo verificar |
| --- | --- | --- | --- |
| 00 / prueba de entorno | Usar el catálogo y schema GTFS actuales. | Tabla de prueba en `workspace.gtfs_bogota`; solo si se ejecuta manualmente. | Comprobar destino antes de ejecutar; no forma parte del Job Bronze. |
| 02 / validación y entrada a Raw | Rechazar el ZIP si faltan archivos esenciales o ambos calendarios. | Error antes de crear directorios, ZIP, manifiesto o task values para datos rechazados. | ZIP mínimo válido; archivo esencial ausente; ambos calendarios ausentes; bytes que no son ZIP. |
| 04 / contrato y prevalidación | Admitir `calendar.txt`, `calendar_dates.txt` o ambos; exigir al menos uno y las siete columnas semanales cuando corresponda. | Solo carga archivos publicados; el rechazo de presencia ocurre antes de cargar entidades. | Probar las tres combinaciones válidas y la ausencia de ambos. |
| 07 / presencia y procedencia | Auditar calendarios, rechazar versión nula o distinta y filas sin archivo fuente para un hash. | Nuevos resultados de auditoría; no cambia datos Bronze. | Revisar `calendar_definition_present` y `bronze_provenance_version`. |
| 07 / relación de servicios | Construir servicios con los calendarios disponibles. | Check de huérfanos incluso si existe un solo calendario; sin borrar registros. | Revisar `trips_service_id_exists` con uno y con ambos calendarios. |

Las pruebas locales se ejecutan desde la raíz con `py -B -m unittest discover -s tests -v`. Usan el código real de los bloques afectados y datos pequeños; los dobles de Spark no sustituyen la comprobación real en Databricks. Las transformaciones de tipos y la deduplicación pertenecen a Silver.

### Revalidación en Databricks de los snapshots existentes

**Estado:** pendiente de ejecutar en el Workspace. Las correcciones locales no actualizan automáticamente los notebooks que utiliza el Job. Primero sincroniza o importa la versión de `feature/silver-referencias` y confirma que las tareas apunten a esos notebooks. Usa el Job manual únicamente después de verificar su configuración; para esta comprobación basta ejecutar los notebooks indicados manualmente, de forma secuencial y sin otra carga concurrente del mismo snapshot.

| feed_version | snapshot_sha256 | Orden manual |
| --- | --- | --- |
| `2025-10-28` | `07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952` | 04 completo y después 07 completo, con estos dos parámetros en ambos. |
| `2026-09-29` | `08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097` | 04 completo y después 07 completo, con estos dos parámetros en ambos. |

- **04:** vuelve a leer los encabezados y comprueba el contrato. En las tablas que ya contienen el hash debe informar `snapshot_already_loaded = true` y omitir la inserción. Si alguna entidad publicada no tiene filas Bronze, detén el avance a Silver e investiga la carga incompleta; no borres tablas para forzar una recarga.
- **07:** vuelve a evaluar la evidencia y añade una corrida a la auditoría. Copia su `quality_run_id` para consultar únicamente ese resultado. Es normal que la auditoría tenga más filas; no implica duplicación de datos Bronze.
- **02:** conservar la corrección para futuras ingestas. No hace falta descargar otra vez estos snapshots ni ejecutar todo el Job para actualizar esta validación. La barrera de rechazo y el reintento Raw se comprobaron localmente con ZIP sintéticos; sigue pendiente su prueba de integración en un entorno de desarrollo.
- **03 y 05:** no cambiaron y no necesitan ejecutarse para esta revisión. En particular, no es necesario releer y volver a cargar los millones de filas de horarios.
- **00:** la corrección de destino no requiere ejecución; es una prueba manual que crea una tabla de prueba y no pertenece al flujo Bronze.

Consulta los checks de cada ejecución por separado, reemplazando el marcador por el identificador impreso:

```sql
select check_name, entity_name, severity, status, observed_value, details
from workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_quality
where quality_run_id = '<quality_run_id_de_la_ejecucion>'
order by status, entity_name, check_name;
```

Criterios de revisión: `calendar_definition_present = PASS`; cero `FAIL` con severidad `BLOCKING`; `bronze_provenance_version` con cero discrepancias; y `trips_service_id_exists` evaluado, sin un `NOT_APPLICABLE` inesperado. Revisa cada `WARN`: un cambio de esquema conocido puede mantenerse advertido, pero no se autoriza automáticamente una relación rota para Silver. El número total de checks cambia respecto al Hito 08 porque se añadió el check del grupo de calendarios.

Comprueba que el volumen histórico de horarios se conserva:

```sql
select source_feed_version, source_sha256, count(*) as stop_time_rows
from workspace.gtfs_bogota.bronze_gtfs_stop_times
where (source_feed_version = '2025-10-28'
       and source_sha256 = '07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952')
   or (source_feed_version = '2026-09-29'
       and source_sha256 = '08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097')
group by source_feed_version, source_sha256
order by source_feed_version;
```

Referencias históricas documentadas: 5.698.892 filas para 2025 y 9.408.893 para 2026. Son puntos de comparación, no resultados de una nueva consulta realizada durante este cambio. Una discrepancia debe investigarse antes de continuar.

Con estas comprobaciones satisfactorias y las advertencias revisadas podremos empezar el perfilado de agencias y rutas para acordar Silver. No hace falta repetir las ingestas ni habilitar una programación automática.
