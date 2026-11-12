# Mi vista previa de service_dates

**Fecha:** 11 de noviembre de 2026. Después de comprobar las tablas de calendarios y subir su cierre en 2a8002f, consulté las fuentes Silver mediante Genie. Recuperé sin truncamiento los resultados de tres consultas: 29 filas de esquema, cuatro de conteos y dos de escenarios. El SQL queda en el [notebook 13](../databricks/notebooks/silver/13_preview_gtfs_service_dates.ipynb), sin escrituras ni outputs versionados.

**Decisión:** comenzaré por el snapshot 2026-09-29 y el horizonte 2026-01-01 a 2026-12-31. Las fuentes de 2025 siguen publicadas e intactas. La comparación de 2025 es diagnóstica y no forma parte de la primera tarea derivada del Job.

## Qué significa una fila

Service_dates convierte patrón semanal y excepciones en días activos explícitos. Su clave será versión + hash + servicio + fecha. Un servicio puede agrupar viajes: contar sus días activos no equivale a contar viajes, flota o pasajeros.

Como ejemplo sintético, una fila servicio A / 2026-01-05 significa que ese conjunto de fechas declara servicio ese día. Para saber cuántos viajes se planificaron habrá que relacionarlo después con trips y horarios.

## Fuentes Silver realmente consultadas

| Entidad | Snapshot | Filas | Claves distintas | Versión de reglas incorrecta |
| --- | --- | ---: | ---: | ---: |
| calendar | 2025-10-28 | 7 | 7 | 0 |
| calendar_dates | 2025-10-28 | 140 | 140 | 0 |
| calendar | 2026-09-29 | 7 | 7 | 0 |
| calendar_dates | 2026-09-29 | 133 | 133 | 0 |

Consulté los mismos hashes documentados en el [perfil de calendarios](calendars_profile_2025_2026.md). Las fechas de 2025 siguen siendo 2000–2099 para el patrón y 2023 para las excepciones. Los 29 campos físicos corresponden a 18 + 11 de las fuentes; no a la derivación.

## Escenarios calculados, no tablas publicadas

| Escenario | Días servicio-fecha del patrón | Reglas dentro del horizonte | Adiciones / retiradas declaradas | Pares activos finales |
| --- | ---: | ---: | --- | ---: |
| Año 2025, snapshot 2025 | 1.670 | 0 | 0 / 0 | 1.670 |
| Año 2026, snapshot 2026 | 1.460 | 133 | 19 / 114 | 1.403 |

Los dos resultados contienen siete servicios y fechas entre el 1 de enero y el 31 de diciembre de su escenario. Para 2026 espero 1.403 candidatos en la primera ejecución si las fuentes y reglas no cambian; todavía no afirmo haber publicado esa tabla.

No calculo 1.460 + 19 - 114 como si cada regla cambiara exactamente una fila. Una adición en un día ya activo mantiene una representación; una retirada en un día ya inactivo no elimina otra fila. La consulta aplica operaciones de conjunto sobre servicio + fecha y produce 1.403.

No comparo 1.670 frente a 1.403 como reducción de oferta. Además del alcance festivo incompleto de 2025, los servicios y sus codificaciones cambiaron; esos conteos no representan cantidades de viajes comparables.

## Recorrido y límites

1. Selecciono una sola pareja versión/hash en las fuentes Silver.
2. Recorto el intervalo semanal al horizonte explícito, sin cambiar el intervalo publicado.
3. Expando días y conservo los que marca el patrón.
4. Uno fechas con excepción 1 sin duplicarlas.
5. Retiro fechas con excepción 2.
6. Conservo trazabilidad y verifico clave/conteos antes de publicar.

La primera implementación registra versiones Delta fijadas y el horizonte. Este SQL es una exploración de lectura sobre las tablas consultadas; no publica ni sustituye las pruebas del módulo PySpark. No expandí stop_times ni empecé Gold.

La especificación fuente está en [GTFS](https://gtfs.org/documentation/schedule/reference/#calendar_datestxt). El horizonte, el esquema derivado y las protecciones de publicación pertenecen al [contrato del proyecto](contracts/service_dates.md).


## Comprobación posterior de la tabla publicada

El 11 de noviembre publiqué service_dates de 2026 y consulté la tabla Silver: 1.403 filas, 1.403 claves distintas, siete servicios, primera fecha 2026-01-01 y última fecha 2026-12-31. También inspeccioné sus datos. El resultado coincide con la vista previa anterior; el [cierre de ejecución](silver_execution.md#cierre-de-la-ejecución-de-service_dates) registra el ámbito y la evidencia disponible. El escenario 2025 permanece como diagnóstico, sin publicación derivada.
