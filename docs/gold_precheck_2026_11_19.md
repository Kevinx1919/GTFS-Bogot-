# Mi comprobación previa de cobertura Gold

**Fecha de cierre:** 19 de noviembre de 2026.
**Método:** consultas de lectura de Genie sobre las tablas existentes.
No ejecuté Jobs, no ejecuté el notebook 20 y no publiqué Gold.

## Snapshot

- Versión: `2026-09-29`.
- SHA-256: `08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097`.

Consulté el último started_at_utc por entidad con dense_rank.
No filtré por status ni committed antes de elegir el último intento.
Encontré un único registro vigente por entidad y los tres terminaron SUCCEEDED, committed=true.
Las reglas y destinos coinciden con el contrato del publicador.

| Fuente | Filas auditadas | Regla | Ejecución Silver |
| --- | ---: | --- | --- |
| trips | 181060 | trips_v1 | df1c0f0f-3616-4431-b6fc-268e4d678898 |
| stop_times | 9408893 | stop_times_v1 | 035295e1-e7ed-477a-b61a-a56d4e2fc0d7 |
| frequencies | 14 | frequencies_v1 | 4835598e-c0be-492c-a17a-23d461a15447 |

Gold_gtfs_trip_coverage todavía no existe en el schema consultado.

## Reconciliación SQL

Agrupé visitas y ventanas por snapshot y trip_id antes del left join con trips.
Conservé viajes declarados sin visitas.

| Cobertura | Contexto | Viajes declarados | Visitas | Ventanas |
| --- | --- | ---: | ---: | ---: |
| sin_visitas | sin_frecuencias | 739 | 0 | 0 |
| una_visita | sin_frecuencias | 61 | 61 | 0 |
| varias_visitas | por_frecuencia | 14 | 98 | 14 |
| varias_visitas | sin_frecuencias | 180246 | 9408734 | 0 |

Los grupos concilian 181060 viajes declarados, 9408893 visitas y 14 ventanas.
Encontré cero visitas sin pareja completa de llegada y salida.
La presencia de horas no demuestra su exactitud ni operación real.
No atribuí causas a los viajes sin visitas.

## Qué falta ejecutar

La revisión SQL no fija versiones Delta conjuntamente ni ejecuta las comprobaciones de metadatos del procesador Python.
El notebook 20 en modo validate fija sus fuentes y aplica las verificaciones implementadas.
Ese modo no escribe tablas ni auditoría Gold.
No tengo una herramienta de ejecución de Jobs/notebooks autenticada en esta sesión.
Genie permite completar la revisión SQL, pero no sustituye esa ejecución.

Abriré `databricks/notebooks/gold/20_publish_gtfs_trip_coverage` en Workspace y configuraré:

| Campo | Valor |
| --- | --- |
| repo_root | Raíz del repositorio sincronizado en Workspace. |
| catalog | workspace |
| schema | gtfs_bogota |
| feed_version | 2026-09-29 |
| snapshot_sha256 | 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097 |
| mode | validate |

Espero persisted=false, reconciled=true, 181060 candidatos, 739 sin_visitas,
61 una_visita y 180260 varias_visitas.
La publicación y la incorporación a Power BI vendrán después de verificar ese resumen.

Conservo las consultas en el historial local de Genie; omito el enlace privado del workspace

## Validación y publicación posteriores

Ejecuté notebook 20 en validate: gold_run_id a767716a-f2cf-4eeb-ad4d-49c4389a2e2c, persisted=false y reconciled=true.
Después ejecuté publish: gold_run_id 8d48f208-89a1-4c7b-9369-136be92d7a51, persisted=true y reconciled=true.
Conservé source_versions: silver_audit=55, trips=1, stop_times=3 y frequencies=1.

La comprobación posterior de Genie confirmó 181060 filas únicas, 9408893 visitas y catorce ventanas.
Encontré un solo gold_run_id y una sola regla trip_coverage_v1 en la tabla seleccionada.
La auditoría conserva STARTED y CLOSED/SUCCEEDED con gold_committed=true para la publicación.
No repetí la publicación desde Genie.

Importé once columnas a Power BI mediante la misma conexión Databricks existente.
Creé diez medidas y comprobé filtros, reconciliación, denominadores y ausencia de cobertura 2025.
Los detalles están en [BI/medidas/trip_coverage](../BI/medidas/trip_coverage/README.md).
