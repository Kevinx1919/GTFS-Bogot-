# Silver: mi recorrido de trabajo

Mi punto de entrada es [08_agency_sql_guiado.ipynb](08_agency_sql_guiado.ipynb). Lo preparé para estudiar una pregunta por bloque, empezando por agency de 2025. No necesito abrir todos los archivos ni ejecutar dos implementaciones para entender el concepto.

## Recorrido

1. Elijo el snapshot y miro qué columnas tiene la tabla.
2. Miro las filas y compruebo si puedo explicar qué representan.
3. Cuento filas e IDs y reviso nulos, vacíos e identificadores repetidos.
4. Consulto el encabezado histórico para distinguir una columna ausente de un valor vacío.
5. Reviso lo encontrado antes de pasar a 2026 y definir el contrato Silver.

El bloque 0 crea widgets; las consultas siguientes son de lectura. Las consultas largas de Genie están al final, como apéndices opcionales y fijadas a 2025. No necesito volver a ejecutarlas: sus resultados ya están documentados. Todavía no he ejecutado la guía nueva con widgets en Databricks.

## Para qué sirve cada archivo

| Archivo | Uso |
| --- | --- |
| [08_agency_sql_guiado.ipynb](08_agency_sql_guiado.ipynb) | Mi punto de entrada y consultas cortas explicadas; apéndices con el SQL completo de Genie. |
| [08_profile_gtfs_reference_entities.ipynb](08_profile_gtfs_reference_entities.ipynb) | Perfilador PySpark más general; alternativa posterior para automatizar las mismas preguntas. |
| [agency_profile_2025.sql](../../sql/silver/agency_profile_2025.sql) | Archivo original de las dos consultas largas ya verificadas; evidencia histórica, conservada sin cambios. |
| [Informe de agency 2025](../../../docs/agency_profile_2025.md) | Resultados comprobados y decisiones propuestas; no contiene las filas raw. |
| [10_publish_gtfs_entity.ipynb](10_publish_gtfs_entity.ipynb) | Entrada única del Job: valida y publica el snapshot con cuarentena, auditoría y verificación. |
| [Publicación y Job manual](../../../docs/silver_execution.md) | Cómo ejecutar el flujo, crear el Job y extenderlo a otras entidades. |
| [09_validate_gtfs_agency.ipynb](09_validate_gtfs_agency.ipynb) | Aplica el contrato y muestra candidatos, rechazos y advertencias en memoria. Requiere los módulos gtfs_silver del repositorio. |
| [Validación de ambos snapshots](../../../docs/agency_validation_2025_2026.md) | Resultados reales del núcleo Python, pruebas y ejecución Spark pendiente. |
| [Contrato v1 de agency](../../../docs/contracts/agency.md) | Tipos, obligatoriedad, errores y protección del histórico antes de transformar. |
| [Plan Silver](../../../docs/silver_design.md) | Orden completo de entidades y criterios para avanzar. |

Ya revisé las salidas del perfilador PySpark de agency para ambos snapshots. Preparé los validadores del contrato v1 y el notebook 09 de lectura. Su núcleo Python ya fue contrastado con ambos snapshots; el notebook 09 también fue ejecutado para ambos snapshots en Databricks. Implementé la publicación y el notebook 10, con 64 pruebas aprobadas localmente, sin omisiones. Falta la publicación y creación del Job en el workspace.

El perfilador y la guía ya quedaron versionados en GitHub. Los validadores y el notebook 09 ya quedaron versionados en GitHub. El notebook 10, la publicación, la configuración del Job y las actualizaciones de esta revisión están pendientes de commit/push. Genie no publica automáticamente mi código.
