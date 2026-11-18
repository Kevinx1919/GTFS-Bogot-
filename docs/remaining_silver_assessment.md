# Mi evaluación de las tres entidades Silver pendientes

**Fecha:** 17 de noviembre de 2026.
**Estado:** revisión exploratoria de lectura; no implementé ni publiqué estas entidades Silver.
**Objetivo:** decidir si aportan a un Power BI útil sobre oferta planificada y calidad del GTFS estático.
Consulté únicamente los snapshots existentes con sus parejas exactas de versión y hash.

## Conclusión para el alcance actual

Ninguna de las tres entidades es una dependencia imprescindible de las métricas de oferta y cobertura planteadas.
Feed_info puede enriquecer una ficha de procedencia; no bloquea la medición de rutas, visitas o fechas activas.
Las dos entidades tarifarias responden a un dominio distinto que requiere una pregunta explícita del reporte.
No transformaré tablas solamente para igualar la cantidad de entidades Bronze y Silver.
Raw y Bronze conservan la evidencia original sin obligar a usarla en cada modelo analítico.

Revisé mi recomendación anterior de completar las tres automáticamente antes de pasar a negocio.
La necesidad debe decidirse por la pregunta, no por una secuencia administrativa de carpetas o tablas.
Esta es una recomendación de alcance; no marco como implementados sus contratos Silver.

| Entidad | Evidencia disponible | Utilidad para el reporte propuesto | Recomendación |
| --- | --- | --- | --- |
| feed_info | Una fila en 2026; no figura en 2025, coherente con la auditoría Bronze previa. | Publicador, idioma, versión textual y período declarado. | Opcional para procedencia; incorporar si esa ficha necesita sus atributos. |
| fare_attributes | Siete clases tarifarias en 2025 y una en 2026. | Estructura tarifaria publicada; no mide oferta de servicio ni demanda. | Aplazar mientras no exista una pregunta tarifaria. |
| fare_rules | 676 reglas en 2025; archivo ausente en 2026 según evidencia disponible. | Aplicación por ruta y zona dentro del snapshot publicado. | Incorporar junto a tarifas solo si el análisis lo requiere. |

## Qué comprobé

Ejecuté cuatro consultas iniciales y dos de seguimiento mediante Genie.
Recuperé los seis resultados estructurados completos, sin truncamiento.
El [notebook 21](../databricks/notebooks/silver/21_review_gtfs_metadata_fares.ipynb) conserva el SQL completo ejecutado.
No ejecuté ese notebook entero en Workspace ni añadí sus controles al Job.

### Feed_info

Encontré una fila para 2026, con Transmilenio S.A., idioma es y feed_version textual 1.
Los campos requeridos revisados no tienen nulos ni cadenas sin contenido tras trim.
Las fechas publicadas convierten a 2026-01-01 y 2026-12-31; no están invertidas.
No detecté copias idénticas en esa fila.

La versión textual 1 no sustituye source_feed_version=2026-09-29 de mi catálogo.
La fecha final declarada no es la hora de descarga ni una prueba de frescura.
Tampoco certifica por sí sola el calendario efectivo que calculé con calendar y calendar_dates.
No completé validación exhaustiva de URL, correo, idioma ni toda la coherencia temporal del estándar.

### Fare_attributes

| Control | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| Filas | 7 | 1 |
| fare_id distintos | 7 | 1 |
| Claves repetidas | 0 | 0 |
| Ausencias en fare_id, price, currency_type o payment_method | 0 | 0 |
| Precios no numéricos o negativos en el control ejecutado | 0 | 0 |
| Referencias agency_id no resueltas | 0 | 0 |

La moneda publicada es COP.
El rango de precios del snapshot 2025 es 0–2950; la fila con cero referencia la agencia Alimentadora.
No infiero gratuidad, subsidio ni motivo del cero sin una definición de negocio adicional.
En 2026 la única fila publica 3550 y referencia agency_id=7, TransMiCable.
No extiendo ese importe a toda la red ni lo presento como tarifa vigente.
No comparo automáticamente agencias de años distintos por el ID aislado.

Transfers aparece null en Bronze para las ocho filas.
El estándar permite transfers vacío con significado de cantidad ilimitada, sujeto al contexto tarifario y su duración.
No lo convierto automáticamente en cero ni lo clasifico como error por estar vacío.
Las duraciones publicadas son 6600 segundos en 2025 y 7500 en 2026.
El código payment_method publicado es 0; su dominio válido no demuestra cómo se paga realmente en operación.
No validé estos atributos contra regulación, recaudo ni comportamiento observado.

### Fare_rules

Las 676 filas de 2025 tienen contenido distinto en los campos de regla revisados.
No encontré fare_id vacío; cinco clases tarifarias aparecen en las reglas.
Sus referencias resuelven contra fare_attributes Bronze del mismo snapshot.
Los 676 route_id distintos resuelven contra routes Silver del mismo snapshot.
Todas las reglas tienen origin_id; su única zona de origen distinta resuelve contra stops.zone_id Silver.
No hubo referencias de zona no resueltas en los campos presentes.

Destination_id y contains_id están publicados pero no tienen valores no blancos en estas filas.
No confundo cero valores informados con una columna ausente del encabezado.
La ausencia del archivo en 2026 es válida para un archivo opcional.
No copio las reglas de 2025 ni supongo que la ausencia significa que no existen tarifas.
Antes de cualquier análisis tarifario tendré que interpretar las reglas del estándar y el alcance de agencia del snapshot.

## Alcance y límites de la revisión

La ausencia en observaciones de esquema se interpreta junto a las auditorías Bronze ya documentadas.
Por sí sola no certifica universalmente que un archivo nunca existió.
Las consultas iniciales comprueban conteos, campos seleccionados, conversiones y relaciones; no toda la especificación GTFS.
Los SQL de fechas y duplicados sirven como evidencia de estos valores existentes; no son validadores genéricos de producción.
No interpreté una consulta satisfactoria como aprobación de un contrato Silver todavía inexistente.
No descargué feeds, ejecuté Jobs ni escribí tablas Bronze, Silver o Gold.

## Próximo paso de negocio

Primero definiré persona usuaria y decisión, después pregunta e indicador.
Elegiré fuentes y tablas Gold solamente cuando esa relación esté clara.
La [guía de negocio](business_questions.md) conserva ejemplos de preguntas para revisar, sin darlas por aprobadas.
El prototipo Gold de cobertura sigue local y sin publicación.
No añadí tablas de tarifas o metadata al registro Silver ni al coordinador.

## Referencias

- [feed_info en la referencia GTFS](https://gtfs.org/documentation/schedule/reference/#feed_infotxt).
- [Atributos tarifarios GTFS](https://gtfs.org/documentation/schedule/reference/#fare_attributestxt).
- [Reglas tarifarias GTFS](https://gtfs.org/documentation/schedule/reference/#fare_rulestxt).
- [Explore in Databricks](https://dbc-caa55511-0fef.cloud.databricks.com/one/chat/threads/80583edacdb143d6b621dbcd00baeb7b?o=7474646722477316&utm_source=genie_chat_mcp).
