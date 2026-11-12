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

Completé el perfil de calendar y calendar_dates: patrón semanal y excepciones de servicio. El [notebook 12](12_profile_gtfs_calendars.ipynb) conserva siete consultas definitivas de lectura y el [informe](../../../docs/calendars_profile_2025_2026.md) explica el alcance temporal anómalo de 2025. Implementé los contratos en calendars_spark.py; ya validé/publiqué con el notebook 10, ejecuté ambas tareas del Job y consulté las tablas. También publiqué y consulté service_dates para 2026; ahora paso a revisar geometrías antes de viajes. La guía de perfilado no se añade al Job. Los cinco procesadores fuente y service_dates de 2026 ya tienen tablas y datos comprobados en Workspace; la siguiente entidad es shape_points; el detalle está en el [plan](../../../docs/silver_design.md#siguiente-bloque-calendar-y-calendar_dates).


## Service_dates: de reglas a días activos

El [notebook 13](13_preview_gtfs_service_dates.ipynb) conserva las tres consultas de vista previa. El [informe](../../../docs/service_dates_preview.md) registra el resultado de lectura y el [contrato](../../../docs/contracts/service_dates.md) define horizonte, trazabilidad y publicación.

Elegí comenzar por 2026. El procesador y la sexta tarea del Job están implementados y probados localmente. También publiqué la tabla en Databricks y consulté 1.403 pares únicos, siete servicios y fechas de 2026-01-01 a 2026-12-31. El [cierre](../../../docs/silver_execution.md#cierre-de-la-ejecución-de-service_dates) conserva el alcance de la comprobación. Uso el notebook 10 con entity=service_dates y window_start/window_end explícitos. En este incremento pasaron 24 pruebas seleccionadas sin omisiones, incluidas ocho nuevas; la verificación anterior de 105 casos queda como antecedente y no como una nueva ejecución completa de toda la suite.


## Shape_points: perfil antes de implementar

El [notebook 14](14_profile_gtfs_shape_points.ipynb) conserva nueve consultas definitivas de lectura, ejecutadas mediante Genie. El [informe](../../../docs/shape_points_profile_2025_2026.md) registra 909.878 / 926.501 puntos y 676 / 1.045 trazados. Los controles no encontraron errores de claves o conversiones, pero sí coordenadas consecutivas iguales y cuatro trazados sin viajes referenciados en 2025. El [contrato](../../../docs/contracts/shape_points.md) explica por qué se conservan.

Implementé shape_points localmente. Sus pruebas nativas están en ejecución y la publicación sigue pendiente. El notebook de perfilado no se añade al Job. La ejecución de las consultas está comprobada por separado; no afirmo haber ejecutado el cuaderno completo. El [plan](../../../docs/shape_points_plan.md) mantiene el mapeo shapes.txt/Bronze → shape_points Silver y los pasos de pruebas/publicación pendientes.


## Publicación preparada de shape_points

El procesador shape_points_spark.py conserva puntos y valida claves compuestas. El alias usa shapes.txt y bronze_gtfs_shapes. Notebook 10 mantiene sus dos bloques ejecutables. La plantilla añade publish_shape_points después de service_dates. No necesita un horizonte de fechas.

La [guía de despliegue](../../../docs/silver_execution.md#despliegue-de-shape_points_v1) contiene parámetros y resultados esperados. El [contrato](../../../docs/contracts/shape_points.md) define advertencias y bloqueos. La primera ejecución en Workspace sigue pendiente.
