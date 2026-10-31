# Mi runbook de notebooks

## Convención

Uso este runbook para recordar qué hace cada bloque, qué necesita y qué debería revisar al terminar. Documento propósito, entradas, salidas, efectos persistentes y validación; los comentarios del código explican las decisiones que no resultan evidentes. Para mí es como una lista antes de salir de viaje: puedo comprobar qué preparé, qué ejecuté y qué falta sin depender de la memoria.

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

**Estado:** completé la revalidación prevista y guardé las salidas de ambas versiones. Para 2025, 07 terminó en `PASSED`, con cero fallos bloqueantes y cero advertencias. Para 2026, terminó en `WARNING`, con cero fallos bloqueantes y cinco advertencias de esquema en las entidades conocidas. Las ocho entidades de referencia de cada versión mostraron `snapshot_already_loaded = true` en 04. La salida detallada de 2026 confirmó calendarios y relaciones aprobados, y 9.408.893 filas de horarios. En esta revisión guardé el resumen de 2025, sin una nueva consulta detallada del conteo de horarios. Mi siguiente paso es perfilar agencias y rutas; revisaré las advertencias de esquema al definir sus contratos Silver.

Conservo los pasos siguientes por si necesito repetir la comprobación. No hace falta repetir una ejecución correcta solo para volver a obtener la misma salida. Las correcciones locales no actualizan automáticamente los notebooks que utiliza el Job. Si necesito reproducirla, primero sincronizo o importo `feature/silver-referencias` y compruebo a qué notebooks apuntan las tareas. Reviso la configuración antes de usar el Job manual; para esta comprobación puedo ejecutar los notebooks indicados en orden y sin otra carga concurrente del mismo snapshot.

| feed_version | snapshot_sha256 | Orden manual |
| --- | --- | --- |
| `2025-10-28` | `07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952` | 04 completo y después 07 completo, con estos dos parámetros en ambos. |
| `2026-09-29` | `08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097` | 04 completo y después 07 completo, con estos dos parámetros en ambos. |

- **04:** vuelvo a leer los encabezados y compruebo el contrato. En las tablas que ya contienen el hash debe informar `snapshot_already_loaded = true` y omitir la inserción. Si alguna entidad publicada no tiene filas Bronze, detengo el avance a Silver e investigo la carga incompleta; no borro tablas para forzar una recarga.
- **07:** vuelvo a evaluar la evidencia y guardo su `quality_run_id` para consultar únicamente esa corrida de auditoría. Es normal que la auditoría tenga más filas; no implica duplicación de datos Bronze.
- **02:** conservar la corrección para futuras ingestas. No hace falta descargar otra vez estos snapshots ni ejecutar todo el Job para actualizar esta validación. La barrera de rechazo y el reintento Raw se comprobaron localmente con ZIP sintéticos; sigue pendiente su prueba de integración en un entorno de desarrollo.
- **03 y 05:** no cambiaron y no necesitan ejecutarse para esta revisión. En particular, no es necesario releer y volver a cargar los millones de filas de horarios.
- **00:** la corrección de destino no requiere ejecución; es una prueba manual que crea una tabla de prueba y no pertenece al flujo Bronze.

Para consultar una ejecución concreta, reemplazo el marcador por el identificador que imprimió el notebook:

```sql
select check_name, entity_name, severity, status, observed_value, details
from workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_quality
where quality_run_id = '<quality_run_id_de_la_ejecucion>'
order by status, entity_name, check_name;
```

Criterios de revisión: `calendar_definition_present = PASS`; cero `FAIL` con severidad `BLOCKING`; `bronze_provenance_version` con cero discrepancias; y `trips_service_id_exists` evaluado, sin un `NOT_APPLICABLE` inesperado. Reviso cada `WARN`: un cambio de esquema conocido puede mantenerse advertido, pero no se autoriza automáticamente una relación rota para Silver. El número total de checks cambia respecto al Hito 08 porque se añadió el check del grupo de calendarios.

Para comprobar que el volumen histórico de horarios se conserva, uso esta consulta:

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

Con las comprobaciones satisfactorias y las advertencias revisadas puedo empezar el perfilado de agencias y rutas para definir Silver. No hace falta repetir las ingestas ni habilitar una programación automática.

## Preparación de Silver — Hito 10

El [plan consolidado](silver_design.md) describe el contrato y la secuencia de trabajo. Existe databricks/notebooks/silver/ con un README. El notebook 08 de perfilado de agency ya está creado como se documenta a continuación; todavía no lo he ejecutado en Databricks ni he creado tablas Silver con él.

| Componente propuesto | Propósito | Entrada | Salida / efecto previsto | Verificación antes de continuar |
| --- | --- | --- | --- | --- |
| 08 / selección del snapshot y perfilado de agency | Entender identidad, campos y calidad antes de transformar. | Bronze agency de una versión/hash y sus encabezados fuente. | Resúmenes de lectura; sin escritura Silver ni cambios Bronze. | Revisar clave, conteos, nulos, vacíos, espacios, duplicados y completitud por versión. |
| 08 / perfilado posterior de routes | Acordar el contrato de rutas después de revisar agency. | Bronze routes y agencias del mismo snapshot. | Resúmenes de lectura y relaciones; sin escritura Silver. | Revisar nombres, tipos de ruta, colores, duplicados, agencia y ausencia de route_desc. |
| 09 / transformación de referencias | Aplicar los contratos acordados, primero agency y luego routes. | Bronze y reglas explícitas; dependencias validadas. | Tablas Silver, cuarentena y auditoría; pendientes de diseño por bloque antes de implementar. | Pruebas, reconciliación, calidad, trazabilidad y reejecución sin duplicación. |

Los números y nombres son propuestos. Esta tabla describe intención, no resultados ejecutados. Antes de añadir el primer bloque se detallarán sus parámetros y su comprobación concreta; no avanzaré a una transformación mientras tenga su perfilado sin revisar.

## Notebook 08 — silver/08_profile_gtfs_reference_entities

**Mi alternativa PySpark para automatizar.** Comienzo por 08_agency_sql_guiado para entender las preguntas. No necesito ejecutar ambas opciones como dos pasos obligatorios.

**Estado:** preparé el perfilador local de agency, pero todavía no lo he ejecutado en Databricks ni lo he añadido al Job Bronze. Me faltan routes y las transformaciones.

| Bloque | Propósito | Entradas | Salidas | Efectos persistentes | Verificación |
| --- | --- | --- | --- | --- | --- |
| 1 / parámetros | Seleccionar un snapshot y explicar la lectura. | Widgets catalog, schema, staging_volume, feed_version y snapshot_sha256. | Tabla, ruta, parámetros, UTC y versión de Spark visibles. | Ninguno en archivos o tablas; los widgets son configuración de sesión. | Identificadores simples, fecha real en formato ISO y SHA-256 hexadecimal. Cambiar versión y hash juntos. |
| 2 / procedencia y muestra | Confirmar identidad y esquema antes de perfilar. | bronze_gtfs_agency y encabezado de agency.txt del snapshot en Staging. | Conteo, encabezado, printSchema y hasta 20 filas fuente. | Ninguno. | Hash con filas, versión y ruta correctas; columnas técnicas presentes; columnas fuente conservadas como string; encabezado no ambiguo. |
| 3 / perfil por columna | Medir ausencias y variedad y mostrar tipos propuestos. | DataFrame completo del snapshot y encabezado publicado. | DataFrame de métricas por campo, tipo Bronze y propuesta Silver. | Ninguno; todos los resultados quedan en sesión. | Revisar source_column_present antes de interpretar los nulos. Nulos/vacíos/solo espacios/no vacíos son categorías exclusivas para cada columna existente. |
| 4 / duplicados | Separar copias de negocio, conflictos de ID y colisiones potenciales. | Columnas publicadas y agency_id cuando exista. | Grupos idénticos, IDs repetidos, resumen de IDs y posibles colisiones al eliminar espacios. | Ninguno: no aplica trim ni deduplicación. | Tabla vacía = ningún grupo encontrado; business_variants=1 es copia idéntica; >1 es conflicto. Revisar IDs ausentes por separado. |

**Si elijo esta alternativa PySpark:** empezaré por 1 y 2 para 2025 y revisaré conteo, printSchema y muestra antes de interpretar las métricas. Los defaults son workspace, gtfs_bogota, staging_gtfs y el snapshot 2025 ya documentado. El hash de 2026 está al inicio del notebook y en la sección de revalidación de este runbook; al cambiar parámetros se deben reejecutar los bloques desde 1.

**Tipos:** la propuesta de los campos conocidos de agency es string, incluido ID y teléfono. No se fuerza una conversión numérica ni se rellena ningún faltante. Campos desconocidos quedan pendientes. El perfil no valida todavía formatos URL, zona horaria, idioma ni todas las reglas de obligatoriedad, y no incorpora relaciones con routes.

**Pruebas locales:** `py -B -m unittest discover -s tests -v` terminó con 22 pruebas aprobadas y 3 omitidas por requerir un entorno Spark local. Las tres pruebas Spark usan fixtures sintéticos para categorías de ausencia, duplicados conflictivos y campos desconocidos; su ejecución sigue pendiente en un entorno con PySpark/Java. La ejecución real del notebook en Databricks será una comprobación adicional, no un resultado ya obtenido.

## Acceso de consulta mediante Genie — Hito 12

Comprobé la conexión de Databricks Genie en Free Edition con dos consultas de lectura: DESCRIBE de bronze_gtfs_agency y conteo por versión/hash de los snapshots conocidos, ambos con resultado estructurado SUCCEEDED. Recuperé 11 columnas reales y 7 registros por snapshot. Esta vez obtuve los resultados mediante el conector, en lugar de depender de las salidas que había revisado desde la interfaz.

Esta conexión permite continuar el perfilado con SQL revisado y resultados estructurados; no implica que se haya ejecutado el notebook 08 o que el conector pueda ejecutar sus bloques PySpark. En ese punto había comprobado esquema y conteos; la muestra, los nulos y los duplicados llegaron después, en el Hito 13. La lectura directa del encabezado Staging con el notebook sigue pendiente. El notebook permanece como implementación versionada para ejecutar y aprender en Databricks.

Usé acciones de lectura, pero eso no demuestra que mi cuenta tenga únicamente esos permisos. Mantendré las transformaciones deterministas y versionadas. No crearé dashboards para lanzar consultas ni escribiré datos durante el perfilado. Si más adelante necesito ejecutar notebooks o Jobs de forma remota, evaluaré CLI/API con su autenticación; por ahora puedo consultar con Genie.

## Perfilado SQL verificado de agency 2025 — Hito 13

Con Genie revisé agency sin ejecutar el notebook 08. El [informe de 2025](agency_profile_2025.md) separa presencia de columna, ausencias, variedad y duplicados. Las [dos consultas ejecutadas](../databricks/sql/silver/agency_profile_2025.sql) quedaron guardadas en el proyecto local, pendientes de commit, como evidencia reproducible para ese snapshot y el entorno actual; no son transformaciones ni un pipeline genérico.

Resultados: siete filas, siete IDs distintos y cero duplicados/conflictos; ningún nulo o vacío en los seis campos publicados. agency_fare_url no está en el encabezado histórico y tiene siete null en la tabla Delta. Recuperé los resultados SQL completos y los contrasté con un cálculo independiente de las siete filas: coincidieron.

Leí la observación de encabezados de audit_gtfs_source_schema_observations; no abrí directamente el archivo Staging desde el conector. El notebook 08 sigue pendiente de ejecución PySpark. Para el aprendizaje puede ejecutarse de forma opcional para contrastar esas métricas; no es necesario copiar salidas para volver a demostrar el acceso SQL. Primero terminaré de entender el informe y después repetiré el perfilado de agency para 2026. Las transformaciones, pruebas Spark y contrato definitivo siguen pendientes.

## Punto de entrada — silver/08_agency_sql_guiado

**Propósito:** quiero entender agency con preguntas pequeñas antes de leer las consultas agrupadas de Genie. Ya preparé el notebook; todavía no lo he ejecutado en Databricks. Sus apéndices conservan las consultas históricas ya ejecutadas, sin cambios en el SQL original.

| Bloque | Pregunta / propósito | Entrada | Salida | Efectos persistentes y verificación |
| --- | --- | --- | --- | --- |
| 0 / widgets | ¿Qué snapshot voy a mirar? | Tabla agency, tabla de auditoría, versión y hash, con defaults del entorno actual y 2025. | Configuración visible de sesión. | No escribe archivos/tablas. Widgets SQL con marcadores requieren Runtime 15.2 o superior; comprobar al ejecutar. |
| 1 / esquema | ¿Qué columnas y tipos tiene Bronze? | Nombre de tabla parametrizado con IDENTIFIER. | DESCRIBE. | Solo metadatos; el esquema histórico no demuestra presencia en el archivo de cada versión. |
| 2 / muestra | ¿Qué representa cada fila? | Un snapshot explícito. | Hasta 20 filas con columnas de negocio. | Solo lectura; comparar ID y nombre antes de interpretar atributos compartidos. |
| 3 / conteo | ¿Cuántas filas e IDs distintos hay? | El mismo snapshot. | Dos cantidades. | COUNT DISTINCT omite null; el conteo por sí solo no aprueba una clave. |
| 4 / ausencias | ¿Hay IDs nulos, vacíos o compuestos por espacios? | agency_id del snapshot. | Conteos por categoría. | No rellena ni convierte valores; no reconstruye vacíos que el lector CSV haya convertido a null. |
| 5 / repeticiones | ¿Qué IDs aparecen más de una vez? | agency_id del snapshot. | Grupos repetidos. | Tabla vacía = ningún grupo encontrado; no deduplica. |
| 6 / encabezado | ¿La columna se publicó en el archivo? | Observación de esquema por versión/hash y agency.txt. | Lista de columnas fuente. | No escribe auditoría. Permite explicar agency_fare_url ausente en 2025. |
| Apéndices A y B | ¿Cómo se reunieron estas preguntas en las consultas largas? | SQL histórico exacto del archivo agency_profile_2025.sql. | Métricas por columna y resumen de duplicados si se vuelven a ejecutar. | Lectura opcional; fijados a 2025, independientes de los widgets. Sus resultados previos no demuestran ejecución de la guía nueva. |

**Mi forma de trabajo:** una pregunta, un bloque y una explicación del resultado antes de seguir. No añadiré controles avanzados ni otras entidades mientras no entienda la revisión actual. No es necesario volver a ejecutar el perfilado ya comprobado solo para mover su SQL a un notebook.

El código original de las dos consultas sigue en databricks/sql/silver/agency_profile_2025.sql como evidencia; el notebook guiado es mi entrada principal. Dejé la explicación de la conexión Codex–Genie y sus ventajas en el Hito 12, con la precisión de que esta prueba usó herramientas MCP desde Codex desktop y no Databricks CLI.

Referencias de la sintaxis de la guía: [widgets](https://docs.databricks.com/aws/en/notebooks/widgets) y [IDENTIFIER](https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-names-identifier-clause).
