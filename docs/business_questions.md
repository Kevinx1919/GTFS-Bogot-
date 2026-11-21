# Mi definición de negocio antes de Gold y Power BI

**Estado:** preguntas candidatas para acordar; no son indicadores aprobados ni promesas del reporte.
**Alcance:** oferta planificada y calidad del GTFS estático de los snapshots existentes.
No incorporo demanda, operación observada ni un feed nuevo durante esta revisión.

## Cómo elegiré cada indicador

Primero definiré quién utiliza el reporte y qué decisión necesita tomar.
Después formularé una pregunta que los datos realmente puedan responder.
Relacionaré cada indicador con una acción o una revisión concreta.
Solo entonces elegiré tablas Gold y visualizaciones.
Una visualización atractiva no demuestra utilidad de negocio.

| Elemento | Qué tengo que acordar |
| --- | --- |
| Persona usuaria | Su responsabilidad: planeación, revisión del feed u otra función concreta. |
| Decisión | Qué puede cambiar, revisar o priorizar con la información. |
| Pregunta | Una pregunta medible dentro del alcance del GTFS estático. |
| Indicador | Definición, unidad, numerador, denominador y grupos incluidos o excluidos. |
| Grano y comparación | Snapshot, ruta, fecha, franja o ubicación; claves completas y comparabilidad comprobada. |
| Acción | Qué hará al detectar un resultado y con qué evidencia debe revisarlo. |
| Límites | Qué no mide el indicador y qué ausencias o advertencias deben acompañarlo. |

## Preguntas candidatas, todavía sin aprobación

| Área | Pregunta candidata | Decisión o revisión que podría apoyar | Condición |
| --- | --- | --- | --- |
| Calidad del feed | ¿Qué rutas concentran viajes declarados sin visitas o con una sola visita? | Priorizar revisión del dato y mostrar exclusiones del análisis. | No atribuir cancelaciones ni causas operativas. |
| Oferta planificada | ¿Cómo se distribuyen los patrones y el servicio publicado por ruta y fecha activa? | Revisar consistencia de programación y comparar escenarios publicados. | Separar patrones, plantillas por frecuencia y salidas estimadas. |
| Datos de ubicaciones | ¿Dónde falta información utilizable de coordenadas o accesibilidad publicada? | Priorizar revisión del catálogo e informar la cobertura del atributo. | Ausencia de información no demuestra falta de accesibilidad. |
| Procedencia | ¿Qué snapshot estoy analizando y qué período declara su publicador? | Elegir una fuente adecuada y explicar sus límites. | Fechas declaradas no sustituyen calendarios ni auditorías de cobertura. |
| Tarifas, fuera del foco inicial | ¿Qué estructura tarifaria publica cada snapshot? | Consultar esa estructura si el reporte incorpora una pregunta tarifaria. | No inferir recaudo, precio efectivamente pagado ni vigencia actual. |

Desarrollé estas preguntas en [historias de negocio y cuatro páginas candidatas](power_bi_user_stories.md).
Incluí gerencia, programación, planeación, accesibilidad, supervisión técnica y responsabilidad del dato.
Las historias son escenarios de portafolio; no representan entrevistas reales ni indicadores aprobados.
Una decisión sobre aumentar flota o reducir esperas necesitaría evidencia adicional de demanda y operación.
No usaré conteos de viajes declarados como buses observados ni precios del feed como ingresos.

## Necesidad de entidades Silver

No exijo que todo archivo Bronze tenga una transformación Silver para considerar útil la primera entrega.
Raw y Bronze ya conservan la evidencia; Silver se amplía con contratos según el uso requerido.
Feed_info aporta metadata; fare_attributes y fare_rules aportan un dominio tarifario distinto del análisis de oferta.
Su [evaluación técnica y utilidad](remaining_silver_assessment.md) conserva lo comprobado y lo que todavía falta.

## Validación del modelo elegido

Cada tabla Gold completará las seis respuestas de negocio del plan Silver.
Comprobaré que el indicador conserva el grano y que sus joins no multiplican filas.
Reconciliaré totales y exclusiones contra las fuentes Silver del mismo snapshot.
Revisaré casos concretos antes de elegir gráficos.
Power BI mostrará fuente, definiciones, períodos y limitaciones junto a los resultados que dependen de ellos.
El prototipo de cobertura local permanecerá sin publicación hasta confirmar su papel en el modelo elegido.
