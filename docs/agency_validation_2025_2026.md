# Mi validación de agency — 2025 y 2026

**Fecha:** 6 de noviembre de 2026.
**Alcance:** ejecuté localmente el núcleo Python versionado de agency_v1 sobre los datos completos recuperados mediante Genie. No ejecuté el notebook 09 ni el adaptador Spark en Databricks. No escribí tablas.

## Evidencia de entrada

Seleccioné estos pares de versión y hash:

| Versión | SHA-256 |
| --- | --- |
| 2025-10-28 | 07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952 |
| 2026-09-29 | 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097 |

Recuperé 14 filas y dos observaciones de encabezado, con estado SUCCEEDED y sin truncamiento. El conteo de ventana indicó siete filas por snapshot y comprobé que había recuperado las siete antes de validar. Los encabezados proceden de la auditoría Bronze; esta comprobación no reabrió Staging.

El [SQL ejecutado](../databricks/sql/silver/agency_validation_inputs_2025_2026.sql) conserva la selección y los encabezados. Para transportarla sin depender de la zona de la sesión SQL, recuperé la marca Bronze como microsegundos Unix y la reconstruí en UTC. Los datos fuente se usaron temporalmente fuera de Git.

## Resultado del mismo núcleo que utiliza el notebook

| Snapshot | Entrada | Candidatos | Rechazados | Copias consolidadas | Advertencias | Reconciliado |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2025-10-28 | 7 | 7 | 0 | 0 | 0 | Sí |
| 2026-09-29 | 7 | 7 | 0 | 0 | 0 | Sí |

Usé langcodes 3.5.1, tzdata 2026.6 y reglas agency_v1. Los controles estructurales de URL, zona reconocida, coherencia de zona e idioma no encontraron rechazos. No cambié IDs, nombres, teléfonos ni URLs.

`ready_for_publication=true` significa que el núcleo no encontró errores bloqueantes en estas entradas. No significa que haya creado Silver ni probado sus transacciones, el lector Spark o la importación de módulos en Workspace. Tampoco demuestra continuidad de agencias entre años.

## Comprobación local y límites

La suite completa terminó con 51 pruebas: 45 aprobadas y 6 omitidas por falta de PySpark local. Java sí está disponible. Las omitidas son tres fixtures anteriores de perfilado y tres pruebas del nuevo adaptador Spark. Las pruebas nuevas del núcleo usan datos sintéticos, no estas filas reales ni llamadas de red.

El código está en `databricks/gtfs_silver/` y la ejecución guiada en [09_validate_gtfs_agency.ipynb](../databricks/notebooks/silver/09_validate_gtfs_agency.ipynb). Necesito el repositorio completo en Workspace, con sus módulos y dependencias, para ejecutar el notebook.

Mi siguiente comprobación será ejecutar sus bloques con 2025 y 2026. Después prepararé la escritura restringida al snapshot, cuarentena, auditoría y pruebas de reejecución. Ninguna web fue consultada para comprobar disponibilidad de las URLs de las agencias; el teléfono y el correo no tienen validación integral de formato o existencia.
