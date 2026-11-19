# Mi replanteamiento del reporte: de catálogo a preguntas de negocio

**Fecha:** 19 de noviembre de 2026.
**Estado:** plan de negocio propuesto; no representa nuevas tablas publicadas ni páginas terminadas.
**Alcance:** oferta planificada GTFS estática, Gold y Power BI.

## Lo que encontré

Me adelanté a pulir la presentación antes de completar los hechos que necesitaban las preguntas.
General explica el catálogo, la procedencia y la cobertura del dato.
Todavía no explica la programación por fecha ni la relación entre rutas y ubicaciones.
La presencia de gráficos o transiciones no resuelve esa falta de contenido analítico.

Revisé las historias de negocio, el plan Gold, los contratos y el modelo local mediante MCP.
Encontré una sola tabla Gold importada: gold_gtfs_trip_coverage.
Su contrato resuelve cobertura de visitas por viaje declarado.
No resuelve por sí mismo la programación diaria, los extremos horarios ni la red de ubicaciones por ruta.
En el repositorio, las otras piezas siguen pendientes de contrato e implementación.
No interpreto esa comprobación como un inventario actualizado de todo el workspace Databricks.

Conservo la identidad roja y amarilla, la selección por componente, la navegación y las medidas numéricas útiles.
Cambio la jerarquía narrativa y el lugar de la revisión técnica.

## Propósito del reporte

Quiero ayudar a planeación y programación a explorar la oferta planificada publicada.
El reporte permitirá identificar diferencias que requieren revisión y recuperar las rutas implicadas.
Los roles siguen siendo escenarios de portafolio; no representan entrevistas realizadas con TransMilenio.
El GTFS estático no permitirá concluir que faltan buses o que una ruta incumplió su operación.

El recorrido de cada página será:

**Pregunta → hallazgo → comparación → detalle → acción.**

Un indicador debe tener una pregunta y una acción asociada antes de reservarle espacio.
Un texto automático debe describir el contexto seleccionado y conservar sus denominadores.
No atribuiré causas a una diferencia solo porque el gráfico la muestre.

## Cuatro páginas y su historia

| Página | Persona principal | Pregunta central | Qué mostraré | Acción que habilita |
| --- | --- | --- | --- | --- |
| Panorama de oferta | Planeación y gerencia | ¿Cómo se distribuye la programación publicada para la fecha elegida? | Rutas con programación, viajes declarados sin frecuencias y plantillas por frecuencia, comparación de componentes y rutas. | Elegir componente y abrir las rutas que explican la diferencia. |
| Programación | Programación del servicio | ¿Qué cambia entre dos fechas y qué horario publica una ruta? | Comparación de fechas, calendario, rutas presentes o ausentes en cada fecha y ventanas de frecuencia; horas cuando cierre su contrato. | Contrastar una diferencia concreta con la programación de referencia. |
| Red publicada | Planeación e información al público | ¿Qué ubicaciones relaciona cada ruta y cuáles comparte con otras? | Mapa de ubicaciones publicadas, tipos, jerarquía y lista de rutas relacionadas. | Revisar una ruta, una ubicación o su información publicada. |
| Revisión de información | Responsable del dato | ¿Qué casos debo revisar antes de utilizar esta programación? | Viajes sin visitas o con una visita, rutas afectadas, cobertura temporal y casos recuperables. | Priorizar una solicitud de aclaración con claves y evidencia. |

Panorama será también la entrada al reporte.
No añadiré una portada separada que obligue a pasar por otra página sin aportar análisis.
Mantengo Troncal, Zonal (SITP), Alimentación, Dual y TransMiCable como selección analítica documentada.

## Historia de la primera página

1. Empiezo por el componente y la fecha de servicio.
2. Presento un hallazgo con magnitud y referencia: qué grupo concentra la programación o qué cambió entre fechas.
3. Muestro rutas con calendario habilitado para esa fecha.
4. Separo viajes declarados sin frecuencias de plantillas por frecuencia.
5. Comparo componentes o las rutas de la selección con una escala común.
6. Ofrezco el acceso a Programación con las fechas y la ruta seleccionadas.

Un encabezado candidato será: «{Componente} publica {N} rutas para {fecha}; {X} cambian respecto a {fecha comparada}».
Las llaves indican una plantilla, no resultados ya calculados.
Definiré qué significa cambiar: presencia de ruta, cantidad de viajes declarados u otra medida explícita.
No presentaré todas esas diferencias bajo un indicador ambiguo de cambio.
Si las fechas tienen valores iguales, el texto lo dirá sin inventar una tendencia.

El dato técnico de versión y hash irá en Fuente y alcance, un tooltip o una ficha de detalle.
Conservaré la identidad completa en las relaciones y auditorías.
La fecha de servicio será el contexto principal de Programación.
La versión de los datos no se confundirá con la fecha de servicio.
La primera entrega diaria seguirá limitada a 2026.

## Historias que ya puedo demostrar

Comprobé estos resultados en el modelo local para el catálogo 2026:

- Zonal reúne 725 de 1.045 rutas: aproximadamente 69,4 %.
- Zonal reúne 106.023 de 181.060 viajes declarados: aproximadamente 58,6 %.
- Los 739 viajes sin visitas y los 61 con una visita pertenecen a Zonal.
- TC30, 15-3 y 8-10 concentran 252 de los 739 casos sin visitas: aproximadamente 34,1 %.

La distribución del catálogo puede apoyar el panorama.
La concentración de casos pertenece principalmente a Revisión de información.
Esos resultados no son oferta diaria, pasajeros, flota ni operación observada.
Todavía no cuento con una conclusión validada sobre cambios entre fechas.

## Gold que necesito y su orden

Los nombres siguientes son propuestas físicas, no tablas ya implementadas.
No necesito una tabla por gráfico ni una tabla por página.

| Orden | Pieza | Una fila representa | Preguntas que habilita | Estado |
| --- | --- | --- | --- | --- |
| Existente | gold_gtfs_trip_coverage | Un viaje declarado dentro de una versión y hash. | Cobertura de visitas y casos que requieren revisión. | Publicada para 2026 e importada. |
| 1 | gold_gtfs_route_service_day | Una ruta y una fecha de servicio dentro de una versión y hash. | Rutas con programación, comparación diaria, viajes declarados y plantillas activas. | Contrato e implementación pendientes. |
| 2 | gold_gtfs_route_stop | Una pareja distinta ruta–ubicación dentro de una versión y hash. | Ubicaciones relacionadas, rutas que comparten ubicaciones y exploración del catálogo de red. | Contrato e implementación pendientes. |
| 3 | gold_gtfs_trip_timing | Un viaje declarado dentro de una versión y hash, con extremos horarios y elegibilidad explícita. | Primeras y últimas horas publicadas y casos excluidos del análisis horario. | Definición horaria y contrato pendientes. |

Publicaré y comprobaré cada pieza en Databricks antes de incorporarla a Power BI.
No importaré millones de stop_times solo para construir estos agregados dentro del reporte.
Conservaré catálogos pequeños como dimensiones cuando sean suficientes.
No duplicaré stops o frequencies en otra tabla solo para cambiarles el prefijo a Gold.

La separación entre hechos con grano estable, dimensiones para filtrar y medidas para resumir sigue la [guía de Microsoft](https://learn.microsoft.com/en-us/power-bi/guidance/star-schema).

## Definiciones que cerraré para cada pieza

### Programación por ruta y fecha

1. **Pregunta:** qué programación declara una ruta para una fecha y qué cambia respecto a otra.
2. **Fila:** versión + hash + route_id + service_date.
3. **Ubicaciones:** no cuento ubicaciones en este hecho.
4. **Ausencias:** una ruta sin calendario habilitado no aparece como programada; una dependencia ausente produce diagnóstico, no cero.
5. **Claves:** ruta con identidad de fuente y fecha analítica; service_id se utiliza al preparar el hecho.
6. **Límites:** viajes declarados y plantillas no equivalen a salidas reales ni a buses.

Separaré cantidad de viajes declarados, viajes sin frecuencias y plantillas por frecuencia.
Podré conservar conteos de cobertura como contexto, sin convertirlos en una calificación del servicio.
Primero agregaré por ruta y servicio; después aplicaré los días activos y consolidaré por ruta y fecha.
No multiplicaré todas las visitas por las 365 fechas.

Para comparar fechas, mostraré rutas presentes en ambas, solo en A y solo en B.
No llamaré aperturas o cierres físicos a esas diferencias de programación.
No etiquetaré un día como festivo usando únicamente su día semanal o una excepción GTFS.

### Relación ruta–ubicación

1. **Pregunta:** qué ubicaciones aparecen en los viajes declarados de una ruta y cuáles comparten varias rutas.
2. **Fila:** versión + hash + route_id + stop_id, sin repetirla por viajes o visitas.
3. **Ubicaciones:** ubicaciones referenciadas por visitas publicadas; distinguiré plataformas y estaciones padre.
4. **Ausencias:** no inventaré coordenadas ni ubicaciones para rutas sin visitas.
5. **Claves:** route_key y stop_key del mismo ámbito fuente.
6. **Límites:** una ubicación compartida no certifica un transbordo físico; el mapa no mide cobertura poblacional.

La primera versión representa el catálogo de red, sin filtro de fecha de servicio.
No afirmaré que todas las ubicaciones de una ruta se visitan en la fecha elegida en otra página.
Una red por fecha necesitaría conservar también el servicio o una derivación diaria específica.
No sumaré los conteos de ubicaciones por ruta para obtener ubicaciones únicas del sistema.

### Extremos horarios por viaje

1. **Pregunta:** qué horas publican los viajes elegibles de una ruta.
2. **Fila:** versión + hash + trip_id.
3. **Ubicaciones:** primera y última visita según secuencia; separaré sus IDs de los puntos del trazado.
4. **Ausencias:** conservo horas faltantes y una razón de exclusión; no interpolo.
5. **Claves:** trip_key y ruta de su misma fuente.
6. **Límites:** extremos horarios no prueban continuidad, duración observada ni puntualidad.

Cerraré si uso salida de la primera visita y llegada de la última antes de implementar.
Conservaré los segundos superiores a 24 horas y la precisión publicada.
Interpretaré las ventanas de frecuencia separadas de las salidas individuales.
No presentaré el rango mínimo–máximo como duración promedio del recorrido.

## Modelo de consumo previsto

Mantengo dimensiones de ruta, componente, fecha y ubicación según la pregunta.
El hecho diario se relacionará con ruta y fecha.
El puente de red se relacionará con ruta y ubicación.
La cobertura y los extremos conservarán el grano por viaje.
No uniré hechos entre sí por relaciones bidireccionales para conseguir que un filtro parezca funcionar.
Tampoco sumaré conteos diarios de rutas para presentar rutas distintas de un período.

Databricks preparará relaciones, clasificaciones y agregados reproducibles.
DAX calculará selecciones, diferencias, participaciones y textos de hallazgos.
HTML presentará esos resultados y las interacciones permitidas.
Las transiciones reforzarán una selección o un cambio de contexto, sin convertirse en evidencia de negocio.

## Criterios de aceptación

- Cada gráfico responde una pregunta y permite una revisión concreta.
- El encabezado describe el contexto seleccionado, no repite solamente una tarjeta.
- Las fechas comparadas se identifican claramente y usan la misma versión de datos.
- Las rutas con calendario habilitado concilian con sus servicios activos.
- Las plantillas por frecuencia permanecen separadas de los viajes sin frecuencias.
- Las ubicaciones únicas no se multiplican por visitas, viajes o rutas compartidas.
- Los porcentajes muestran un denominador compatible con la selección.
- La ausencia de una fuente no aparece como cero de negocio.
- La evidencia técnica está disponible sin dominar la lectura de gerencia.
- La narrativa indica qué falta comprobar; no inventa causas ni decisiones operativas.

## Próximo incremento

Empiezo por cerrar el contrato de programación por ruta y fecha.
Después preparo una muestra validada para dos fechas y tres rutas de perfiles distintos.
Solo tras comprobar esa muestra implemento y publico el hecho completo.
Lo incorporo a Power BI, compruebo filtros y redacto los hallazgos de Panorama y Programación.
Después continúo con Red publicada y extremos horarios.
La revisión técnica reutiliza trip_coverage, sin repetir su anillo como protagonista en todas las páginas.

Este replanteamiento cambia el orden del plan anterior.
Las páginas HTML actuales quedan como prototipo visual aprovechable, no como reporte de negocio terminado.


## Preparación del siguiente incremento

Implementé localmente route_service_day y su notebook 22, con contrato y modo validate sin escrituras.
La publicación en Workspace y la incorporación al modelo Power BI siguen pendientes.
La [guía de ejecución](gold_route_service_day_execution.md) conserva la muestra de negocio consultada con Genie.
El manifiesto BI/consumo/sources_plan.json identifica columnas y relaciones del próximo hecho.
El mapa usará coordenadas reales del catálogo, con tipos de ubicación separados.
El puente ruta–ubicación sigue pendiente antes de filtrar ese mapa por componente o ruta.
El boceto anterior deja de ser la base de diseño; no sustituye las preguntas ni condiciona la nueva composición.
