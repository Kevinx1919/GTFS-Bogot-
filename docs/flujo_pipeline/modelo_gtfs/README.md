# Mi modelo GTFS

Tengo dos vistas para explicar lo que ya construí y lo que irá creciendo:

| Vista | Qué muestra |
| --- | --- |
| [Modelo Silver actual](modelo_silver.html) | Todas las columnas, tipos y claves del contrato de agency y routes. |
| [Panorama GTFS](panorama_gtfs.html) | Las entidades agrupadas por responsabilidad, con lo pendiente en Silver identificado. |

## Cómo leo el modelo actual

Una fila de agency representa una agencia o marca dentro de un snapshot. Una fila de routes representa una ruta dentro de ese mismo snapshot. Mantengo estas claves compuestas:

- Agency: `(source_feed_version, source_sha256, agency_id)`.
- Routes: `(source_feed_version, source_sha256, route_id)`.
- Relación de routes hacia agency: `(source_feed_version, source_sha256, agency_id)`.

Cada ruta aceptada apunta a una agency de su snapshot. Una agency puede tener cero o muchas rutas. No uso el nombre ni la URL como identificador y no uno años distintos por `agency_id` aislado. Es como comparar dos ediciones de un catálogo: que ambas tengan el código 2 no prueba que describan el mismo elemento. Es un ejemplo para entender la regla, no una nueva homologación de datos.

Las marcas PK y FK representan claves y referencias comprobadas por el pipeline; no afirman que haya restricciones PRIMARY KEY o FOREIGN KEY declaradas en Delta. Las tres columnas FK forman una sola referencia compuesta.

Incluí las 16 columnas físicas de agency y las 18 de routes. Los IDs siguen como `string`; `route_type` y `route_sort_order` son `int`. También muestro timestamps, `source_columns`, versión de reglas y datos de ejecución. Un `silver_run_id` identifica una corrida y no reemplaza la identidad del snapshot.

## Cómo leo el panorama

Las ramas agrupan responsabilidades: referencias implementadas, ubicaciones y trazados, servicios, viajes y horarios, tarifas y metadata. **Sus líneas no son joins ni claves foráneas**, y tampoco prescriben el orden exacto del Job.

El panorama incluye las fuentes previstas para las demás entidades y la propuesta derivada `service_dates`. `shape_points` es el nombre propuesto para los puntos de `shapes.txt`. Las tablas y reglas aún pendientes se basan en el [plan Silver](../../silver_design.md); no presento sus tipos o claves como implementados.

No exijo que exista un archivo opcional ni fabrico sus filas. Tener un TXT o una tabla Bronze no equivale a haber desarrollado su transformación Silver.

## Cómo mantendré estas vistas

Al incorporar una entidad revisaré su perfil, cerraré el contrato, implementaré sus tipos y comprobaré su ejecución. Después la moveré al grupo implementado y ampliaré el ERD con todas sus columnas y relaciones. Si el modelo crece demasiado, separaré vistas por dominio para poder leerlo sin perder detalle.

Las fuentes editables son [modelo_silver.erd.json](modelo_silver.erd.json) y [panorama_gtfs.tree.json](panorama_gtfs.tree.json). Los enlaces de evidencia fijan el código del commit `598bc0de6b65b25ffa2ef13b628ab0966fd41dcd`. Consulto los [contratos de agency](../../contracts/agency.md) y [routes](../../contracts/routes.md) cuando necesito las reglas completas.

## Comprobación

Ambos HTML pasaron las comprobaciones automáticas, incluidas las de navegador. Revisé sus capturas en claro y oscuro a 1440×900 y 2048×1320; en el panorama largo puedo desplazarme para recorrer los grupos. El [resumen público](verificacion.json) registra hashes y alcance. Es una revisión de documentación basada en código; no una nueva ejecución de los Jobs o consulta en vivo de las tablas.

Genero fuera de OneDrive y copio los HTML comprobados sin cambiar sus bytes. Conservo los recibos y capturas detalladas fuera de Git.
