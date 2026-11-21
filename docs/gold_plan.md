# Mi plan para cerrar la primera versión del proyecto

**Cierre de alcance — 20 de noviembre de 2026:** doy por entregada la v1 local funcional de portafolio. La revisión integral de filtros/rendimiento y la prueba completa de actualización permanecen documentadas como pendientes de endurecimiento; no las marco como superadas.

> **Estado vigente — 20 de noviembre de 2026:** las cuatro Gold de 2026 están publicadas e importadas y los cuatro paneles están implementados. La navegación nativa funciona; la revisión integral y la actualización completa siguen pendientes. [Estado actual](project_status.md).

## Registro de diseño e implementación

Conservo a continuación las decisiones y comprobaciones de cada etapa. Los pendientes de esas fechas describen su momento; el estado vigente anterior los sustituye.

**Fecha:** 17 de noviembre de 2026.
**Actualización:** 19 de noviembre de 2026.
**Alcance acordado:** GTFS estático, Gold y Power BI.
Demanda oficial, GTFS-Realtime y n8n/Ollama quedan como ampliaciones posteriores.
La prueba del coordinador con una versión GTFS nueva queda pendiente para otro momento.
No habilito programación automática como requisito de este incremento.

## Estado del cierre al 19 de noviembre

Publiqué e importé las cuatro Gold necesarias para las preguntas actuales.
Implementé Panorama, Programación, Red publicada y Revisión de información.
Documenté sus cálculos y limitaciones; queda revisar el informe real y su actualización completa.
La revisión dentro de Desktop y el recorrido completo de actualización siguen pendientes.

El [plan de cierre vigente](power_bi_cierre_v1.md) fija cuatro páginas y sus condiciones de aceptación.
Panorama cumple la función de entrada; no necesito una portada adicional para este alcance.
La [explicación del tercer panel](power_bi_red_negocio.md) conserva sus preguntas y ejemplos.

Los apartados posteriores conservan la secuencia histórica del desarrollo.
Sus referencias a productos pendientes describen el momento de cada incremento, no el estado vigente anterior.

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
La cobertura es el primer bloque Gold publicado para General y Calidad.
Las siguientes piezas conservarán su propia definición de negocio antes de publicarse.


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
Publiqué gold_gtfs_trip_coverage para 2026 y la incorporé al modelo Power BI.
Todavía no añadí el publicador Gold al Job principal.
Las historias ya fijan preguntas y decisiones candidatas.
Completaré ahora las fichas de indicadores antes de ejecutar o publicar Gold en Workspace.

## Selección de columnas antes de importar más tablas

La conexión desde Power BI ya está comprobada mediante la carga de agency.
La [guía de consumo](power_bi_consumption_model.md) concreta qué columnas conservar y cuáles omitir de esa importación.
No elimino evidencia Silver: preparo dimensiones y selecciones con claves por snapshot.
Primero cierro General y Calidad; después amplío Programación y Red según sus necesidades.

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
Hasta esa revisión, cobertura tenía contrato y procesador local. La publicación e importación quedaron comprobadas el 19 de noviembre.

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

## Avance del modelo y precheck — 19 de noviembre de 2026

Corregí el modelo de consumo Power BI con claves por snapshot, dimensiones de snapshot/servicio/fecha y relaciones de negocio unidireccionales.
La [documentación del modelo](../BI/modelado/README.md) registra pruebas con filtros y las medidas de catálogo.
Estas dimensiones calculadas pertenecen a Power BI; no representan nuevas tablas Gold en Databricks.
La fecha analítica filtra service_dates; no convierte los conteos de catálogo en programación diaria.
El puente ruta–ubicación sigue pendiente.

La [comprobación SQL de Gold](gold_precheck_2026_11_19.md) concilió fuentes y confirmó que la tabla Gold todavía no existe.
Las tres últimas auditorías Silver siguen disponibles y compatibles.
En ese precheck faltaba ejecutar notebook 20. Después validé y publiqué; el apartado siguiente conserva el cierre.
No marqué la comprobación SQL de Genie como una ejecución de ese notebook.

## Primer Gold publicado y consumido — 19 de noviembre de 2026

Completé la validación y publicación manual de cobertura para 2026.
La [evidencia de publicación](gold_precheck_2026_11_19.md) registra sus ejecuciones y reconciliación.
Incorporé la tabla al modelo Power BI por trip_key y comprobé diez medidas.
El porcentaje de viajes sin visitas es 739/181060, aproximadamente 0,41 %.
El estado de cobertura distingue 2025 sin Gold y el contexto histórico parcialmente evaluado.

El siguiente incremento utiliza estas medidas para la página General/Calidad.
Después continuaré con los contratos y piezas de Programación y Red.
El hecho de programación por ruta/fecha, el puente ruta–ubicación y las correspondencias de componentes siguen pendientes.
No marqué todas las métricas Gold como completas por publicar la primera tabla.

## Consumo inicial en General — 19 de noviembre de 2026

Preparé la primera página General con el catálogo Silver y la cobertura Gold publicada para 2026.
Presenté rutas, viajes declarados, viajes sin visitas y viajes con una visita.
Añadí comparación de agencias, composición de cobertura y tres rutas para revisar.
Usé las medidas numéricas existentes como fuente de siete medidas de presentación HTML.
No amplié el contrato Gold ni publiqué tablas adicionales durante esta tarea.

El menú lateral permite navegar; los controles superiores filtran snapshot, agencia y ruta.
Para 2025 señalé la ausencia de evaluación Gold sin fabricar ceros.
Conservé la advertencia de que visitas publicadas no certifican operación ni recorrido completo.
Programación y Red publicada todavía requieren completar sus productos Gold antes de implementar sus páginas.
Las [fuentes de General](../BI/imagenes/general/README.md) incluyen la vista previa y el alcance de las pruebas.

## Replanteamiento narrativo y prioridad de Gold — 19 de noviembre de 2026

Revisé el reporte y encontré que el diseño mostraba catálogo y cobertura del dato, sin desarrollar la historia de programación y red.
El [nuevo plan de storytelling](power_bi_storytelling_plan.md) pasa a ser la referencia para el siguiente incremento.
Mantengo cuatro páginas: Panorama de oferta, Programación, Red publicada y Revisión de información.
La versión y el hash se conservan como procedencia secundaria; las preguntas de negocio dirigen la página.
Priorizaré el contrato y el hecho Gold de programación por ruta y fecha antes de seguir puliendo tarjetas HTML.
Después completaré el puente ruta–ubicación y la definición de extremos horarios.
Las piezas nuevas todavía no están publicadas y las páginas actuales permanecen como prototipo visual.


## Preparación del siguiente incremento

Implementé localmente route_service_day y su notebook 22, con contrato y modo validate sin escrituras.
La publicación en Workspace y la incorporación al modelo Power BI siguen pendientes.
La [guía de ejecución](gold_route_service_day_execution.md) conserva la muestra de negocio consultada con Genie.
El manifiesto BI/consumo/sources_plan.json identifica columnas y relaciones del próximo hecho.
El mapa usará coordenadas reales del catálogo, con tipos de ubicación separados.
El puente ruta–ubicación sigue pendiente antes de filtrar ese mapa por componente o ruta.
El boceto anterior deja de ser la base de diseño; no sustituye las preguntas ni condiciona la nueva composición.

La cobertura Gold 2026 ya está publicada y consumida. El nuevo procesador diario sigue pendiente de validar y publicar en Workspace.
El [plan narrativo](power_bi_storytelling_plan.md) define las preguntas que guían este incremento.


## Cierre de publicación diaria

Publiqué route_service_day_v1 para 2026 con 305.165 claves únicas y 1.045 rutas en el horizonte.
La ejecución 3b65045e-5afb-431b-93d0-1b40315b485d terminó SUCCEEDED y reconciled=true.
El resumen conserva 25.418.801 viajes-día declarados y cero filas inválidas.
La incorporación a Power BI y las nuevas medidas diarias siguen pendientes.
La [guía de ejecución](gold_route_service_day_execution.md) conserva la evidencia y sus límites.


## Incremento ruta–ubicación

Implementé localmente route_stop_v1 y notebook 23, con contrato, conciliación y publicación por ámbito.
La validación y publicación en Workspace siguen pendientes.
La [guía](gold_route_stop_execution.md) explica el paso siguiente y el filtro del mapa.
No avancé a extremos horarios ni marqué el mapa Power BI como implementado.


## Incremento de extremos horarios

Cerré el contrato e implementé localmente trip_timing_v1 y notebook 24.
La [guía](gold_trip_timing_execution.md) conserva los campos, categorías y límites de consumo.
Ruta–ubicación y extremos horarios siguen pendientes de validar y publicar en Workspace.
No marqué estas tablas como importadas en Power BI ni amplié el Job principal.
