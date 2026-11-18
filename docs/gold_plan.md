# Mi plan para cerrar la primera versión del proyecto

**Fecha:** 17 de noviembre de 2026.
**Actualización:** 18 de noviembre de 2026.
**Alcance acordado:** GTFS estático, Gold y Power BI.
Demanda oficial, GTFS-Realtime y n8n/Ollama quedan como ampliaciones posteriores.
La prueba del coordinador con una versión GTFS nueva queda pendiente para otro momento.
No habilito programación automática como requisito de este incremento.

## Punto de partida

Conservé dos snapshots estáticos en Raw y Bronze y publiqué diez entidades Silver.
El coordinador ya terminó SUCCEEDED en una prueba manual con 2026-09-29.
No equiparo ese resultado con la prueba de ingesta de un feed nuevo.
No conservé la salida detallada de tareas, el Job run ID ni las listas de ese último piloto.
Mantengo esa distinción sin repetir una ejecución que ya revisé manualmente.

Trabajaré inicialmente con el snapshot 2026-09-29 y su hash validado.
Service_dates ya tiene el horizonte explícito 2026-01-01 a 2026-12-31.
No expandiré el calendario 2025 ni trasladaré sus excepciones de 2023 a otro año.
Las fuentes históricas permanecerán disponibles sin mezclar sus identidades.

## Orden de cierre

Antes de publicar Gold definiré la persona que usará el reporte y la decisión que quiere tomar.
La [guía de negocio](business_questions.md) evita elegir métricas solo porque puedo calcularlas.
Las [historias de negocio](power_bi_user_stories.md) proponen cuatro páginas y acciones concretas.
Separé General por componente, programación, red publicada y revisión técnica.
Añadí una [propuesta de Inicio, navegación e imágenes](power_bi_navigation_images.md).
Inicio separado más cuatro páginas analíticas representan cinco páginas físicas.
Las correspondencias de componentes y los visuales elegidos requieren una prueba previa.
La propuesta requiere cerrar prioridades y definiciones antes de publicar nuevos indicadores.
Revisaré primero la necesidad de las tres entidades Silver opcionales; no completaré capas por cantidad de tablas.
La cobertura implementada localmente es un candidato reutilizable, no una obligación del modelo final.
Su publicación queda pendiente de esa definición de negocio.


| Orden | Entregable | Condición de cierre |
| --- | --- | --- |
| 1 | Preguntas y decisiones de negocio | Persona usuaria, decisión, indicador, denominador, grano y limitaciones acordados. |
| 2 | Gold necesario para esas preguntas | Cobertura es un candidato local; se publica solo si responde una pregunta elegida. |
| 3 | Modelo e indicadores Gold de oferta planificada | Ficha de negocio por tabla, claves únicas y denominadores visibles; sin duplicar frecuencias ni visitas. |
| 4 | Modelo y reporte Power BI | Relaciones por snapshot y claves completas; páginas acordadas desde las historias de negocio, con limitaciones visibles. |
| 5 | Entrega del portafolio | Ejecución reproducible, pruebas pertinentes, documentación vigente y recorrido de demostración. |

No daré por completado un entregable solo porque existe el nombre de una tabla.
Las comprobaciones de Workspace y Power BI formarán parte de su cierre.
Las tablas analíticas vivirán bajo el prefijo gold_gtfs_ en el schema actual, salvo una decisión posterior explícita.
No necesito reorganizar Bronze y Silver en otros schemas para comenzar Gold.

## Primer entregable: cobertura de viajes

La [ficha de negocio](contracts/trip_coverage.md) concreta las seis preguntas acordadas para Gold.
La fuente es trips, con visitas y frecuencias agregadas antes de unir.
Conservo viajes sin visitas; no fabrico sus paradas ni horarios.
La cobertura no certifica que un viaje recorrió todas sus paradas.
Una plantilla por frecuencia no equivale a una sola salida real.

Preparé el [notebook 19](../databricks/notebooks/gold/19_preview_gtfs_trip_coverage.ipynb) con una consulta de solo lectura.
El [perfil Gold inicial](trip_coverage_profile_2026.md) registra sus resultados y límites.
Implementé localmente el procesador y notebook 20, con validación sin escritura por defecto.
No publiqué una tabla Gold en Workspace ni añadí Gold al Job principal.
Las historias ya fijan preguntas y decisiones candidatas.
Completaré ahora las fichas de indicadores antes de ejecutar o publicar Gold en Workspace.

## Reparto entre Gold y Power BI

Gold prepara reglas, relaciones y agregados reutilizables.
Power BI calcula medidas según los filtros elegidos.
La [guía de conexión y responsabilidades](powerbi_mcp_setup.md) concreta ese reparto y el estado del MCP local.
La reparación del MCP no representa una publicación Gold ni un reporte Power BI terminado.

## Indicadores y modelo dimensional posteriores

Definiré primero qué pregunta responde cada indicador y qué representa cada fila.
Separaré el catálogo publicado, los patrones de viaje y la oferta asociada a fechas activas.
No llamaré viajes operados al conteo de trip_id.
Los patrones por frecuencia tendrán tratamiento explícito; no contaré sus plantillas como salidas exactas.
No expandiré todas las visitas por todas las fechas para crear un agregado por ruta y fecha.

Las dimensiones de rutas, agencias y ubicaciones conservarán el snapshot en sus relaciones.
Las ubicaciones distinguirán paradas/plataformas de estaciones padre.
La ausencia de accesibilidad permanecerá desconocida cuando la fuente no publique el atributo.
El reporte mostrará exclusiones y cobertura junto al indicador correspondiente.
Los catálogos de 2025 y 2026 podrán consultarse, sin presentar cambios de IDs como crecimiento físico demostrado.

Completaré las seis respuestas de negocio antes de implementar cada nueva tabla Gold.
No fijé todavía las columnas finales de todos los hechos y dimensiones.
No presentaré una lista de propuestas como un modelo ya implementado.

## Qué queda fuera de esta primera versión

- Nuevas integraciones de demanda, salidas y GTFS-Realtime.
- Narrativas y alertas mediante n8n/Ollama.
- Tarifas y feed_info en Silver, salvo que una pregunta del reporte requiera incorporarlas.
- Prueba de ingesta automática de una versión GTFS nueva y programación productiva.
- Comparación histórica de viajes operados, ocupación, puntualidad y espera experimentada.

Conservo esos pendientes; no los marco como realizados ni elimino su documentación de ampliaciones.
Esta decisión acota la primera entrega y permite cerrarla con una demostración completa de GTFS estático.

## Ejecución futura de notebook 20, cuando confirme su utilidad de negocio

Primero sincronizo el repositorio completo después del commit y push del incremento.
Abro databricks/notebooks/gold/20_publish_gtfs_trip_coverage.
Configuro repo_root con la raíz del repositorio en Workspace y conservo catálogo/schema actuales.
Uso feed_version=2026-09-29 y su SHA-256 validado.
Mantengo mode=validate y ejecuto Run all.
Espero 181060 candidatos, 739 sin_visitas, 61 una_visita y 180260 varias_visitas, si las fuentes no cambiaron.
El resumen debe reconciliar 9408893 visitas y 14 ventanas, con persisted=false.
Después de revisar el significado y el resultado podré seleccionar publish y repetir Run all.
La comprobación de publicación forma parte del cierre Gold; no la doy por realizada desde las pruebas locales.

## Comprobación local del primer procesador

Pasaron 135 pruebas unitarias y dos integraciones seleccionadas con Spark/Delta reales.
Las integraciones preservan viajes sin visitas y evitan multiplicación por dos ventanas del mismo viaje.
Incluyen horas ausentes, publicación, reejecución y conservación exacta de otro snapshot.
También comprueban deriva de metadata y un intento Silver posterior fallido.
Usé la imagen offline existente, sin red, con el repositorio en solo lectura y temporales fuera de OneDrive.
La prueba local no publicó datos en Databricks ni sustituyó la comprobación de Workspace.

## Estado del diseño de consumo — 18 de noviembre de 2026

Propuse Inicio, General por componente, Programación, Red y Calidad.
El prototipo HTML permite revisar navegación e imágenes con fixtures explícitamente ilustrativos.
La [guía visual](power_bi_navigation_images.md) conserva lo probado y lo pendiente.
Las preguntas están documentadas; todavía no todos los indicadores tienen una ficha Gold/DAX cerrada.
La cobertura sí tiene contrato detallado y procesador local; su publicación sigue pendiente.

La conexión MCP de Power BI quedó probada en solo lectura tras aceptar su licencia.
La habilidad de navegador es otra vía; todavía no comprobé la cuenta web.
Mantendré esa separación al documentar capacidades y resultados.

## Verificación antes de versionar — 18 de noviembre de 2026

Pasaron 135 pruebas unitarias con el entorno offline existente.
Excluí 96 casos nativos de esta selección; no los cuento como aprobados.
El Python de Windows carece de validadores y PySpark requeridos para ejecutar toda la suite.
La integración completa requiere además su configuración Spark/Delta y resolución local de hostname.
Conservo la evidencia previa de las dos integraciones Gold; esta revisión no la sustituye.
Validé sintaxis Python, notebooks sin resultados persistidos y enlaces de documentación.
No instalé paquetes dentro del repositorio ni ejecuté Jobs de Databricks.
