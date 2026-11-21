# Mi estado actual del proyecto GTFS

**Cierre de alcance — 20 de noviembre de 2026:** doy por entregada la v1 local funcional de portafolio. La revisión integral de filtros/rendimiento y la prueba completa de actualización permanecen documentadas como pendientes de endurecimiento; no las marco como superadas.

**Actualización:** 20 de noviembre de 2026.
**Entrega:** oferta planificada de 2026 con GTFS estático, Databricks y Power BI.

Ya puedo recorrer los cuatro paneles mediante el menú nativo.
Conservo separados lo publicado, lo comprobado durante el desarrollo y lo pendiente de cierre.

## Del origen al reporte

| Etapa | Qué hace | Estado |
| --- | --- | --- |
| Raw y Staging | Conservo ZIP, manifiesto y TXT originales. | Snapshots 2025-10-28 y 2026-09-29 disponibles. |
| Bronze | Preservo filas fuente, identidad y calidad del snapshot. | Cierres completos; 2026 conserva cinco avisos de evolución de esquema sin bloqueantes. |
| Silver | Tipo, valido y relaciono entidades del mismo snapshot. | Diez entidades habilitadas con despliegue confirmado. Service_dates cubre solo 2026. |
| Gold | Preparo hechos con grano y límites de negocio explícitos. | Cuatro tablas publicadas e importadas para 2026. |
| Power BI | Aplico filtros, medidas DAX y presentación. | Cuatro paneles implementados; navegación nativa confirmada durante la revisión. |

Bronze, Silver y Gold comparten el schema del proyecto y se distinguen por prefijo y responsabilidad.
Los Volumes contienen archivos; las tablas Delta contienen registros consultables.
La identidad conserva versión, SHA-256 e ID; no relaciono IDs históricos sin esa identidad completa.

## Las cuatro Gold disponibles

| Tabla | Qué representa una fila | Filas de 2026 | Uso |
| --- | --- | ---: | --- |
| gold_gtfs_trip_coverage | Un viaje declarado del snapshot. | 181.060 | Visitas publicadas y clasificación de cobertura. |
| gold_gtfs_route_service_day | Una ruta y fecha de servicio. | 305.165 | Comparación de programación diaria entre fechas. |
| gold_gtfs_route_stop | Una pareja ruta–ubicación del snapshot. | 62.715 | Ubicaciones relacionadas y ubicaciones compartidas. |
| gold_gtfs_trip_timing | Un viaje declarado con sus extremos y categoría horaria. | 181.060 | Perfil horario y motivos de exclusión. |

Estos conteos corresponden a las publicaciones confirmadas durante el desarrollo.
Esta actualización documental no volvió a ejecutar Databricks ni actualizó datos del modelo.
Las guías de publicación conservan las ejecuciones y sus conciliaciones.

## Qué cuenta cada panel

| Panel | Pregunta principal | Cómo llego a una revisión concreta |
| --- | --- | --- |
| Panorama de oferta | ¿Qué cambia entre dos fechas y dónde se concentra? | Comparo A y B, elijo componente o ruta y reviso diferencias y ubicaciones relacionadas. |
| Programación | ¿Qué días y horas publica la selección? | Aplico servicios activos y separo viajes sin frecuencia de plantillas y ventanas. |
| Red publicada | ¿Qué ubicaciones relaciona una ruta y cuáles comparte? | Exploro coordenadas, tipos de ubicación, estaciones padre y parejas por ID. |
| Revisión de información | ¿Qué casos necesitan aclaración antes del análisis? | Localizo motivos, rutas y viajes concretos sin confundir exclusión analítica con fallo operativo. |

Panorama es también la entrada al informe; no necesito una quinta portada.
Las historias describen escenarios de portafolio, no entrevistas reales con TransMilenio.
Las definiciones de cada panel conservan preguntas, denominadores, filtros y límites.

## Menú, imágenes y filtros

Las cuatro opciones del menú son botones nativos con texto propio.
El HTML del fondo conserva la marca y la nota de contexto, pero no dibuja etiquetas de navegación ni Laboratorio.
El CSS oculta esas etiquetas si queda contenido anterior del visual.
La página actual usa fondo rojo suave y texto rojo oscuro.
Los otros botones cambian de fondo al pasar el cursor.
En Desktop pruebo las acciones con Ctrl + clic; en lectura utilizo un clic.
La confirmación de que la navegación funciona procede de la revisión del informe, además de la validación PBIR.

Panorama incorpora tarjetas ilustradas de Troncal, Zonal (SITP), Alimentación, Dual y TransMiCable.
Las tarjetas usan filtrado cruzado local; no sincronizan su selección con las otras páginas.
El desplegable de componente y el de ruta conservan grupos sincronizados entre los cuatro paneles.
Las fechas A y B comparten sincronización entre Panorama y Programación.
Para explorar las cinco tarjetas dejo el desplegable de componente sin restringir.
Los filtros pueden intersectarse y producir una selección sin datos.
Las ilustraciones identifican componentes; no representan vehículos observados ni tamaño de flota.

## Gold, DAX y HTML tienen funciones distintas

Gold conserva relaciones, categorías y agregados reutilizables.
DAX calcula cantidades, porcentajes y comparaciones en el contexto elegido.
HTML Content presenta esos resultados mediante HTML, CSS y SVG.
Los botones y selectores nativos gestionan navegación y filtros compatibles.
El visual HTML no ejecuta el JavaScript de las vistas previas.
Las vistas previas eligen resultados DAX precalculados y no consultan Databricks en vivo.
El PBIP ofrece el modelo completo; el PBIX anterior no recibe automáticamente estos cambios.

## Límites que mantengo visibles

- Analizo programación publicada; no afirmo operación realizada, puntualidad, demanda, ocupación ni cancelaciones.
- Un viaje declarado no equivale siempre a una salida: separo las plantillas por frecuencia.
- Los mapas utilizan coordenadas GTFS y relaciones de catálogo; no son seguimiento de vehículos.
- El mapa de Panorama muestra ubicaciones vinculadas a rutas activas en A, sin garantizar visitas diarias a cada ubicación.
- Una ubicación compartida no demuestra un transbordo realizable ni demanda.
- Las ausencias y los grupos excluidos conservan significado propio; no los convierto automáticamente en cero.
- Gold cubre 2026; no presento el catálogo 2025 como evaluado por esas tablas.

## Qué falta para cerrar

1. Completar una revisión integral de filtros combinados, selección de detalle, legibilidad y rendimiento en Desktop.
2. Comprobar y registrar el procedimiento manual completo de actualización de datos y modelo.
3. Preparar demostración, fuentes versionadas y revisión final del portafolio.

El coordinador ejecuta Bronze y Silver; no automatiza todavía Gold ni la actualización de Power BI.
El piloto con el snapshot existente 2026 terminó correctamente; la prueba con un feed nuevo sigue aplazada.
No habilité una programación productiva ni publiqué en Power BI Service.
Demanda, salidas, GTFS-Realtime, tarifas y n8n/Ollama quedan como ampliaciones según su pregunta de negocio.
La [revisión de acceso a fuentes](source_access_check_2026_11_19.md) conserva los bloqueos observados, sin afirmar que descargué datos nuevos.

## Dónde continúo

- [Cierre de la primera versión](power_bi_cierre_v1.md).
- [Navegación y componentes](power_bi_navigation_images.md).
- [Modelo de consumo](../BI/modelado/README.md).
- [Importación de Gold](power_bi_gold_import.md).
- [Documentación visual Archify](flujo_pipeline/README.md).
- [Panorama](power_bi_panorama_negocio.md), [Programación](power_bi_programacion_negocio.md), [Red](power_bi_red_negocio.md) y [Revisión](power_bi_revision_negocio.md).


El [procedimiento manual de actualización](power_bi_actualizacion_manual.md) ya está documentado; falta comprobar el recorrido completo.
