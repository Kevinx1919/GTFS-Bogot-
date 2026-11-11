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

Ya revisé y publiqué agency para ambos snapshots, y su Job manual terminó con éxito. El perfil real de [routes](../../../docs/routes_profile_2025_2026.md) y su [contrato v1](../../../docs/contracts/routes.md) están documentados. Su implementación Spark reutiliza el notebook 10 y la publicación común; ya ejecuté el Job ampliado en Workspace y comprobé las tablas Silver.

Para las corridas habituales uso solo el notebook 10: bloque 1 de parámetros/imports y bloque 2 de ejecución. Los notebooks 08 y 09 conservan su valor de aprendizaje y diagnóstico; no son requisitos por corrida ni necesito duplicarlos para routes. Configuro dependencias en el entorno antes de ejecutar.


## Stops: lectura de ubicaciones y jerarquía

Continúo con [11_profile_gtfs_stops.ipynb](11_profile_gtfs_stops.ipynb). Conserva seis consultas SQL ejecutadas mediante Genie para los dos snapshots: esquema, conteos, encabezados, distribución, ausencias y controles de identidad/coordenadas/padres. No necesita módulos, instalaciones ni variables Python de otra celda. Cada consulta puede leerse por separado; el bloque de controles es el detalle avanzado.

Es una guía fijada a los valores del proyecto y a los dos hashes comprobados. El SQL fue ejecutado mediante Genie; el archivo nuevo no tiene todavía una ejecución completa documentada como notebook. No necesito repetir las consultas para estudiar el [informe de stops](../../../docs/stops_profile_2025_2026.md). Después de revisar el perfil implementé stops_v1 en el pipeline compartido. No añadí un notebook de validación separado: uso el 10 con entity=stops y mode=validate/publish. La plantilla del Job incorpora una tarea stops serial y ya amplié el Job de Workspace: ejecuté el flujo y comprobé la tabla y sus datos.


El [contrato stops_v1](../../../docs/contracts/stops.md) y la [guía de despliegue](../../../docs/silver_execution.md#despliegue-de-stops_v1) explican las reglas y el despliegue ya comprobado en Databricks, con su alcance de evidencia. Las pruebas de reglas, publicación y preservación son independientes del perfil real guardado en el notebook 11.

## Siguiente bloque del plan

Continúo con calendar y calendar_dates: patrón semanal y excepciones de servicio. Primero perfilaré ambos snapshots y cerraré sus contratos. Después derivaré service_dates antes de pasar a geometrías y viajes. No hay un nuevo notebook o procesador de calendarios implementado todavía; el detalle está en el [plan](../../../docs/silver_design.md#siguiente-bloque-calendar-y-calendar_dates).
