# Mi plan actual del reporte GTFS

**Actualización del cierre — 20 de noviembre de 2026:** navegación nativa confirmada; cuatro paneles y cuatro Gold disponibles. [Estado vigente](project_status.md) y [menú y componentes](power_bi_navigation_images.md).

**Alcance:** GTFS estático, Gold y Power BI para oferta planificada de 2026.
**Estado:** cuatro páginas implementadas y documentadas; revisión final dentro de Desktop pendiente.
La navegación nativa ya está confirmada; conservo pendiente la revisión integral de filtros, lectura y rendimiento.

## Qué quiero conseguir

Quiero pasar de una diferencia general a una ruta, un horario o una evidencia concreta.
Los roles representan escenarios de portafolio; no entrevistas realizadas con TransMilenio.
El recorrido es pregunta, hallazgo, comparación, detalle y siguiente revisión.

| Página | Persona | Pregunta central | Estado |
| --- | --- | --- | --- |
| Panorama de oferta | Planeación y gerencia | ¿Qué cambia entre dos fechas y dónde se concentra? | Diseño aprobado; medidas y PBIP guardados. |
| Programación | Revisión de programación | ¿Qué días y horas publica la selección? | Diseño aprobado; definición de negocio documentada; revisión en Desktop pendiente. |
| Red publicada | Planeación e información al público | ¿Qué ubicaciones relaciona una ruta y cuáles comparte? | Vista previa revisada; definición de negocio documentada; revisión en Desktop pendiente. |
| Revisión de información | Responsable del dato | ¿Qué casos necesitan aclaración antes del análisis? | Implementación y vista previa comprobadas; revisión en Desktop pendiente. |

## Fuentes disponibles

Las cuatro tablas Gold ya están publicadas para 2026 e importadas al modelo.

| Tabla | Una fila representa | Uso |
| --- | --- | --- |
| gold_gtfs_trip_coverage | Un viaje del snapshot. | Cobertura de visitas y casos para revisar. |
| gold_gtfs_route_service_day | Una ruta y fecha de servicio. | Programación diaria y comparación entre fechas. |
| gold_gtfs_route_stop | Una pareja ruta–ubicación del snapshot. | Red del catálogo, sin garantizar visitas diarias. |
| gold_gtfs_trip_timing | Un viaje del snapshot, con elegibilidad y extremos. | Horarios publicados mediante una selección explícita de servicios activos. |

Conservo las claves por versión, hash e ID.
No añado relaciones bidireccionales entre hechos para simular filtros diarios.
Las cuatro tablas Gold importadas permiten construir estas páginas sin otra exportación.

## Primer panel documentado

La [definición de negocio del Panorama](power_bi_panorama_negocio.md) relaciona cada visual con su pregunta y sus límites.
El [panel actual](../BI/imagenes/panorama/panorama_v2_preview.html) combina perfiles, comparación y coordenadas reales.
Su mapa selecciona ubicaciones del catálogo relacionadas con rutas de A.
No calcula visitas diarias por ubicación.

## Incremento actual y siguiente paso

Documenté [Programación](power_bi_programacion_negocio.md) y su selección explícita de servicios activos.
Implementé [Red publicada](power_bi_red_plan.md) con catálogo, coordenadas, referencias padre y comparación de IDs compartidos.
Las definiciones y comprobaciones quedan junto a cada página.

Implementé **Revisión de información** con motivos, denominadores, rutas y detalle de viajes.
La [definición del cuarto panel](power_bi_revision_negocio.md) explica cómo limita cada caso al análisis.
Conservo la distinción entre motivos del dato y fallos operativos.

## Criterios comunes

- Cada gráfico responde una pregunta con una definición comprobable.
- Cada porcentaje conserva su denominador y su referencia.
- Los viajes, las plantillas y los viajes-día permanecen separados.
- Una fuente o fecha ausente no aparece como cero.
- Las ubicaciones únicas no se multiplican por visitas o rutas compartidas.
- Los horarios mayores de 24 conservan su significado de servicio.
- No deduzco pasajeros, ocupación, flota, puntualidad, continuidad ni cancelaciones.
- Mantengo la procedencia técnica disponible sin convertirla en el mensaje principal.
- Documento qué funciona en el motor, qué guardé en PBIP y qué falta revisar en Desktop.

Demanda oficial, GTFS-Realtime y n8n/Ollama permanecen como extensiones posteriores.


## Entrega de Programación

Documenté [qué muestra y qué responde Inicio](power_bi_panorama_negocio.md).
Construí [Programación](../BI/imagenes/programacion/programacion_preview.html) sobre las tablas importadas.
Documenté [qué responde Programación y cómo lo calculo](power_bi_programacion_negocio.md).
Implementé [Red publicada](power_bi_red_plan.md) con coordenadas, referencias padre y relaciones por ID.
La cuarta página ya está implementada; el siguiente paso es revisar el informe completo en Desktop.

## Documentación del tercer panel y cierre acordado

La [definición de negocio de Red publicada](power_bi_red_negocio.md) explica cada visual, su cálculo y sus límites.
El [plan de cierre de la primera versión](power_bi_cierre_v1.md) concreta la cuarta página y la aceptación final.
Construí Revisión de información con cobertura y elegibilidad horaria ya importadas.
Después revisaré el informe en Desktop y comprobaré su procedimiento de actualización.
La automatización adicional y las nuevas fuentes permanecen como ampliaciones.

## Cuarto panel implementado

Construí [Revisión de información](../BI/imagenes/revision_informacion/revision_preview.html).
Documenté [qué responde y cómo lo calculo](power_bi_revision_negocio.md).
Comprobé setenta contextos y las categorías contra cobertura Gold.
La tabla nativa permite consultar un viaje sin cambiar los totales del contexto.
El [cierre vigente](power_bi_cierre_v1.md) conserva la revisión de Desktop y la actualización reproducible como pendientes.
