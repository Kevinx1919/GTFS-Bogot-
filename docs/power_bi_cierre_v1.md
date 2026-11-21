# Mi cierre de la primera versión GTFS

**Cierre de alcance — 20 de noviembre de 2026:** doy por entregada la v1 local funcional de portafolio. La revisión integral de filtros/rendimiento y la prueba completa de actualización permanecen documentadas como pendientes de endurecimiento; no las marco como superadas.

**Actualización del cierre — 20 de noviembre de 2026:** navegación nativa confirmada; cuatro paneles y cuatro Gold disponibles. [Estado vigente](project_status.md) y [menú y componentes](power_bi_navigation_images.md).

**Alcance:** GTFS estático, Gold y Power BI para oferta planificada de 2026.
**Estado:** cuatro páginas implementadas; revisión final y procedimiento completo de actualización pendientes.
La revisión confirmó la navegación nativa. La revisión integral de filtros, lectura y rendimiento sigue abierta.

## Las cuatro páginas acordadas

| Página | Pregunta | Estado actual |
| --- | --- | --- |
| Panorama de oferta | ¿Qué cambia entre dos fechas y dónde se concentra? | Diseño revisado; medidas y definiciones PBIP guardadas. |
| Programación | ¿Qué días y horas publica la selección? | Diseño revisado; cálculo y límites documentados. |
| Red publicada | ¿Qué ubicaciones relacionan las rutas y cuáles comparten? | Implementación y vista previa comprobadas; definición de negocio documentada. |
| Revisión de información | ¿Qué casos necesitan aclaración y cómo afectan a los indicadores? | Implementación, conciliación y vista previa comprobadas; revisión de Desktop pendiente. |

Panorama también cumple la función de entrada al informe.
El menú lateral conecta las cuatro páginas.
No necesito añadir una quinta portada para cerrar este alcance.

## Qué hace el cuarto panel

Ayudo a localizar casos concretos mediante cobertura y extremos horarios Gold ya importadas.
Relaciono esos casos con sus rutas y componentes del mismo snapshot.
La [definición de negocio](power_bi_revision_negocio.md) conserva preguntas, cálculos y ejemplos.

| Pregunta | Visual propuesto | Regla de negocio |
| --- | --- | --- |
| ¿Cuántos viajes carecen de visitas publicadas? | Cantidad, porcentaje y denominador. | coverage_status=sin_visitas frente a viajes declarados del contexto. |
| ¿Cuántos viajes tienen solamente una visita? | Cantidad y detalle de rutas. | coverage_status=una_visita; no permite analizar un recorrido entre dos ubicaciones. |
| ¿Qué viajes quedan fuera del perfil horario? | Distribución por motivo. | timing_status conserva categorías excluyentes; separo plantillas, visitas y extremos. |
| ¿Dónde concentro la revisión? | Rutas ordenadas y detalle de viajes. | Muestro cantidad afectada, porcentaje y total de viajes de cada ruta. |
| ¿Qué debo hacer después? | Explicación del motivo y referencia al viaje. | Distingo ausencia publicada, plantilla y falta de extremos antes de investigar la fuente. |

Trabajo con el catálogo 2026, sin presentarlo como casos activos de una fecha elegida.
Componente y ruta limitan las cantidades y sus denominadores.
Si incorporo fechas posteriormente, aplicaré explícitamente los servicios activos, como en Programación.

## Ejemplo que debe explicar el cuarto panel

El catálogo contiene 181.060 viajes declarados.
Cobertura clasifica 739 sin visitas, 61 con una visita y 180.260 con varias visitas.
La clasificación horaria distingue 180.246 elegibles y 814 excluidos.
En esta publicación, los excluidos son 739 sin visitas, 61 con una visita y 14 plantillas.
No encontré extremos ausentes ni invertidos en ese resumen publicado.

Las dos clasificaciones describen los mismos viajes desde preguntas diferentes.
No sumaré sus cantidades afectadas como si fueran grupos independientes.
Varias visitas no certifican un recorrido completo.
Una plantilla no constituye por sí misma un dato inválido.
Ninguna clasificación demuestra cancelaciones ni fallos operativos.

## Qué falta para cerrar

Ya construí y comprobé Revisión de información en el motor y la vista previa.

| Orden | Trabajo pendiente | Evidencia de cierre |
| --- | --- | --- |
| 1 | Completar la revisión integral en Desktop. | Navegación ya confirmada; faltan registrar filtros combinados, selección de detalle y legibilidad de los cuatro paneles. |
| 2 | Verificar rendimiento y lectura del informe completo. | Registro escenarios y tiempos reales; corrijo problemas visibles. |
| 3 | Documentar y comprobar la actualización manual completa. | Puedo seguir Raw/Bronze/Silver, Gold y actualización del modelo sin instrucciones implícitas. |
| 4 | Preparar la entrega del portafolio. | Documentación vigente, diagramas alineados, fuentes versionadas y recorrido de demostración. |

Las cuatro tablas Gold ya están publicadas e importadas para 2026.
No necesito crear nuevas tablas Gold ni importar más Silver para construir el cuarto panel propuesto.
Feed_info y las entidades tarifarias siguen fuera del alcance analítico inicial.

## Qué significa «actualizar el proyecto»

El coordinador versionado conecta la ingesta Bronze con la publicación Silver.
Todavía no incorpora las publicaciones Gold ni la actualización de Power BI.
No lo describiré como automatización completa hasta implementar y comprobar esas etapas.

Para la primera entrega puedo conservar un procedimiento manual reproducible.
Coverage debe publicarse antes del hecho diario que la utiliza.
Ruta–ubicación y extremos horarios conservan sus publicadores y contratos propios.
Después actualizo las tablas importadas y recalculo el modelo de consumo.

Las guías existentes son mi punto de partida; falta comprobar el recorrido de actualización completo.
No necesito repetir ahora la ingesta de un feed nuevo para cerrar las páginas del snapshot disponible.
La prueba con otra versión permanece registrada como trabajo posterior.

## Qué no bloquea este cierre local

- Integrar demanda oficial, GTFS-Realtime, n8n u Ollama.
- Completar tarifas o feed_info en Silver sin una pregunta que los necesite.
- Automatizar Gold y la actualización de Power BI dentro del coordinador.
- Habilitar una programación productiva.
- Publicar en Power BI Service o configurar actualización programada.

Una entrega compartida en Service necesitará comprobar publicación, credenciales y actualización en ese entorno.
No doy esa publicación por hecha desde un archivo local.

## Mi definición de terminado

Daré por cerrada la primera versión cuando las cuatro páginas respondan sus preguntas con resultados verificables.
También dejaré visibles sus limitaciones y un procedimiento reproducible de actualización y demostración.
Versionaré fuentes y definiciones; mantendré credenciales, cachés y datos de ejecución fuera de Git.

[Plan del informe](power_bi_storytelling_plan.md).
[Definición de Red publicada](power_bi_red_negocio.md).
[Fuentes Gold importadas](power_bi_gold_import.md).
[Alcance del coordinador](pipeline_coordinator.md).
[Publicación de cobertura](gold_precheck_2026_11_19.md).
[Publicación diaria](gold_route_service_day_execution.md).
[Publicación ruta–ubicación](gold_route_stop_execution.md).
[Publicación de extremos horarios](gold_trip_timing_execution.md).


El [procedimiento manual de actualización](power_bi_actualizacion_manual.md) ya está documentado; falta comprobar el recorrido completo.
