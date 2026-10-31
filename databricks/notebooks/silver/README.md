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
| [Plan Silver](../../../docs/silver_design.md) | Orden completo de entidades y criterios para avanzar. |

Todavía no he creado tablas ni transformaciones Silver. Uso esta carpeta para el código de revisión; las tablas futuras vivirán en Unity Catalog. Prepararé la transformación después de entender y perfilar ambos snapshots.

Guardé los archivos nuevos y la reorganización localmente; me falta hacer commit/push. Genie no copia ni publica automáticamente mi código en GitHub.
