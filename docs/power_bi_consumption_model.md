# Mi selección de columnas para el consumo en Power BI

> **Estado vigente — 20 de noviembre de 2026:** las cuatro Gold de 2026 están publicadas e importadas y los cuatro paneles están implementados. La navegación nativa funciona; la revisión integral y la actualización completa siguen pendientes. [Estado actual](project_status.md).

## Registro de diseño e implementación

Conservo a continuación las decisiones y comprobaciones de cada etapa. Los pendientes de esas fechas describen su momento; el estado vigente anterior los sustituye.

**Fecha:** 18 de noviembre de 2026.
**Estado:** definición inicial de consumo; no publiqué nuevas tablas o vistas ni modifiqué el archivo Power BI.

## Qué sigue después de comprobar la conexión

Ya puedo consultar Databricks desde Power BI.
Ahora defino qué representa cada tabla importada y qué columnas necesita el reporte.
No elimino columnas de Silver para reducir el tamaño de Power BI.
Preparo una selección explícita en las tablas o vistas de consumo.
La evidencia técnica completa permanece en Databricks.

Empiezo por agency porque fue la tabla utilizada para comprobar la conexión.
Tiene pocas filas; el mayor ahorro llegará al evitar detalles masivos que el reporte no necesita.
No importo todas las visitas o puntos de trazado para calcular un conteo agregado.

## Criterio para conservar una columna

Conservo una columna si participa en una relación, un filtro, un indicador, una descripción necesaria o una regla del modelo.
Omito de la importación principal las columnas que no cumplen esos usos.
Conservar una columna oculta puede ayudar a ordenar el reporte, pero no evita su almacenamiento en Importar.
La [guía de reducción de Microsoft](https://learn.microsoft.com/en-us/power-bi/guidance/import-modeling-data-reduction) recomienda seleccionar columnas y filas según el uso.

## Agency: selección provisional para la prueba actual

| Columna Silver | Decisión en la prueba | Motivo |
| --- | --- | --- |
| agency_id | Conservar. | Identifica la agencia dentro del snapshot. |
| agency_name | Conservar. | Etiqueta de filtros y detalle. |
| source_feed_version | Conservar temporalmente. | Identifica la versión analizada. |
| source_sha256 | Conservar temporalmente. | Completa la identidad del snapshot. |
| agency_url | Omitir por ahora. | Las preguntas iniciales no requieren abrir la web de la agencia. |
| agency_timezone | Omitir de esta tabla importada. | Mantengo su contexto validado en Databricks; no es un filtro del catálogo actual. |
| agency_lang | Omitir por ahora. | No interviene en las preguntas elegidas. |
| agency_phone | Omitir por ahora. | El reporte inicial no es un directorio de contacto. |
| agency_fare_url | Omitir por ahora. | El dominio tarifario queda fuera de esta primera entrega. |
| agency_email | Omitir por ahora. | El reporte inicial no utiliza correo de contacto. |
| source_file_path | Omitir de la importación principal. | Procedencia técnica conservada en Databricks. |
| bronze_loaded_at_utc | Omitir de esta dimensión. | Lo consultaré como contexto de ejecución cuando el indicador lo necesite. |
| source_columns | Omitir de la importación principal. | Metadata de encabezados; no es un atributo de segmentación. |
| silver_rule_version | Omitir de esta dimensión. | Regla de ejecución disponible en la auditoría. |
| silver_run_id | Omitir de esta dimensión. | Referencia técnica de publicación disponible en Databricks. |
| silver_loaded_at_utc | Omitir de esta dimensión. | La fecha de carga no es una fecha de servicio. |

La prueba puede conservar cuatro columnas: agencia, nombre, versión y hash.
Esta selección no define todavía relaciones entre tablas en Power BI.
Si elimino las columnas mediante Power Query, cambia la consulta importada, no la tabla Silver del origen.

No relaciono agency y routes únicamente por agency_id.
Los IDs cambiaron de significado entre snapshots y pueden repetirse entre versiones.
No borro versión y hash antes de disponer de claves analíticas que preserven esa identidad.
La URL tampoco sustituye una clave.

## Diseño objetivo de la dimensión de agencias

Propongo una fila por agencia dentro del snapshot.
El modelo de consumo necesita una clave única para relacionar esa fila con rutas del mismo snapshot.

| Campo de consumo propuesto | Función |
| --- | --- |
| agency_key | Clave analítica única de la agencia dentro del snapshot; oculta para quien lee el reporte. |
| snapshot_key | Referencia al catálogo de snapshots; oculta para quien lee el reporte. |
| agency_id | ID fuente para inspección y correspondencias; no reemplaza agency_key. |
| agency_name | Nombre publicado que utilizaré como etiqueta. |

Los campos terminados en _key son propuestas de consumo; no existen por haber importado Silver.
Antes de construirlos fijaré una generación determinista y compartida entre dimensiones y hechos.
Comprobaré unicidad, correspondencia por snapshot y estabilidad al reejecutar.
No generaré índices independientes en cada tabla ni eliminaré ceros iniciales de IDs fuente.
Las [relaciones del modelo](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema) necesitan claves únicas y compatibles.

El catálogo de snapshots conservará versión, SHA-256 y el contexto de publicación necesario.
Las auditorías completas permanecerán en Databricks.
El reporte podrá mostrar procedencia sin repetir todos sus campos en cada tabla importada.
Una vista de consumo seleccionará columnas; una tabla Gold materializada preparará resultados cuando corresponda.
No considero ambas opciones equivalentes en coste de cálculo durante cada consulta.

## Primer bloque de consumo: General y Calidad

| Pieza propuesta | Una fila representa | Columnas o categorías que necesita | Estado |
| --- | --- | --- | --- |
| Dimensión de snapshots | Un snapshot identificado por versión y hash. | Clave única, versión, hash y contexto documentado. | Contrato por completar. |
| Dimensión de agencias | Una agencia dentro del snapshot. | agency_key, snapshot_key, agency_id y agency_name. | Selección inicial definida arriba. |
| Dimensión de rutas | Una ruta dentro del snapshot. | Claves de ruta y agencia, ID fuente, nombres y tipo utilizado. | Contrato de consumo por completar. |
| Cobertura de viajes | Un viaje declarado dentro del snapshot. | Claves de relación, trip_id, conteos de visitas, clasificación y contexto de frecuencia. | Gold publicado para 2026; once columnas de negocio importadas y medidas comprobadas. |

Trip_coverage conserva sus reglas y datos técnicos en Databricks.
La futura selección para Power BI no tiene que importar sus catorce columnas físicas completas.
Mantendré los campos necesarios para las métricas seleccionadas y el detalle de revisión.
No quitaré trip_id si la página Calidad necesita recuperar un viaje concreto.
No agrego todas las filas en una tarjeta y después intento reconstruir ese detalle.

El nombre de agencia GTFS no identifica automáticamente un operador ni un componente oficial.
Las tarjetas por componente necesitan una correspondencia revisada por snapshot.
No convierto las agrupaciones ilustrativas del HTML en reglas de negocio implícitas.

## Cómo ampliaré el modelo sin cargar todo Silver

Programación incorporará datos por ruta y fecha desde servicios activos y sus viajes declarados.
Red incorporará relaciones distintas entre rutas y ubicaciones, con jerarquías y geometría según la visualización elegida.
No multiplicaré viajes al unirlos directamente con todas las visitas o puntos del trazado.
No sumaré conteos de ubicaciones entre rutas si comparten ubicaciones.
Para fechas, comienzo con el horizonte 2026 ya derivado.
El catálogo completo y las ubicaciones con programación en una fecha tendrán etiquetas distintas.

## Orden de implementación

1. Cierro las columnas y claves del primer bloque General/Calidad.
2. Completo las fichas de los indicadores, incluidos filtros, denominador y ausencias.
3. Implemento las dimensiones o proyecciones necesarias y las verificaciones de claves.
4. Valido el publicador de cobertura existente en Databricks y reviso su reconciliación.
5. Publico el Gold aprobado y las selecciones de consumo versionadas.
6. Conecto Power BI a esas selecciones con columnas explícitas.
7. Creo relaciones y medidas DAX y contrasto un caso real con Databricks.
8. Amplío Programación y Red según sus preguntas, sin una importación indiscriminada.

No necesito borrar ni volver a cargar Bronze o Silver para definir este modelo.
La conexión ya comprobada puede mantenerse mientras preparo la selección final.

## Referencias del proyecto

- [Preguntas e historias de negocio](power_bi_user_stories.md).
- [Plan Gold y entrega inicial](gold_plan.md).
- [Contrato Gold de cobertura](contracts/trip_coverage.md).
- [Reparto Gold y DAX](powerbi_mcp_setup.md).

## Implementación inicial en Power BI — 19 de noviembre de 2026

Implementé claves calculadas compartidas por snapshot en las ocho tablas importadas.
Añadí dim_gtfs_snapshot, dim_gtfs_service y dim_gtfs_fecha al modelo local.
Las relaciones ya filtran rutas, viajes y ventanas desde snapshot y agencia.
La fecha explícita filtra service_dates; las métricas diarias necesitarán el hecho Gold correspondiente.
La definición y las comprobaciones están en [BI/modelado](../BI/modelado/README.md).
No trasladé esta lógica a Silver ni publiqué nuevas tablas de Databricks.
