# Bogotá GTFS Mobility Lakehouse

Estoy construyendo un lakehouse de movilidad para Bogotá mientras aprendo Databricks y PySpark. Mi primera entrega cubre GTFS estático, Gold y Power BI. Conservo demanda oficial, GTFS-Realtime y n8n/Ollama como ampliaciones posteriores. Quiero explicar el proyecto desde la ingesta hasta un reporte de oferta planificada y cobertura.

> La velocidad operacional se deriva de posiciones consecutivas de vehículos. No representa ni pretende medir la congestión total de la ciudad.

## Problema de negocio de la primera entrega

Quiero entender la oferta planificada publicada y las limitaciones de los datos que alimentan el reporte.
Las primeras preguntas son:

- ¿Qué rutas y ubicaciones aparecen en cada snapshot?
- ¿Qué servicios tienen fechas activas dentro del horizonte 2026?
- ¿Cuántos viajes declarados tienen visitas publicadas y qué contexto de frecuencias presentan?
- ¿Qué exclusiones y advertencias debo mostrar junto a cada indicador?

Estos datos describen planificación. No demuestran viajes operados, puntualidad, ocupación ni espera experimentada.
La [ruta de cierre](docs/gold_plan.md) define los entregables de Gold, Power BI y la demostración del portafolio.
Las [historias de negocio](docs/power_bi_user_stories.md) relacionan preguntas, decisiones e indicadores candidatos.
El [diseño visual](docs/power_bi_navigation_images.md) propone Inicio y cuatro páginas analíticas.
El boceto HTML utiliza cifras ilustrativas; todavía no consume Gold ni ejecuta DAX.

## Arquitectura de la primera entrega

```text
GTFS estático oficial → Raw inmutable → Bronze Delta → Silver Delta → Gold Delta → Power BI
```

El Job principal ya coordinó descubrimiento, Bronze y Silver en un piloto con el snapshot existente de 2026.
Gold tiene su primer procesador preparado localmente; su publicación y su incorporación al flujo siguen pendientes.

## Arquitectura objetivo ampliada

```text
GTFS estático + validaciones/salidas oficiales + GTFS-Realtime
                |
                v
Databricks Workflows: descubrimiento, plan de ingesta y Jobs por fuente (America/Bogota)
                |
                v
Unity Catalog Volume: archivos raw inmutables + manifiesto
                |
                v
Bronze: snapshots y auditoría de ingesta (Delta)
                |
                v
Silver: feeds decodificados, normalizados y validados (Delta)
                |
                v
Gold: indicadores de oferta planificada, demanda observada y operación disponible (Delta)
       |                                  |
       v                                  v
Power BI / Databricks SQL        n8n + Ollama (solo lectura)
                                 reporte y anomalías aprobadas
```

### Principios de diseño

Para mí, Raw es como guardar el archivo original de una encuesta antes de corregir sus columnas: si una cifra no cuadra, puedo volver a lo que recibí. Esa idea guía las siguientes decisiones.

- **Raw primero.** Cada respuesta se conserva con URL, fecha UTC, `run_id`, hash, tamaño y estado HTTP.
- **Transformaciones deterministas.** La limpieza, las reglas de calidad y los cálculos se implementan en PySpark/SQL, no mediante un LLM.
- **Medallion architecture.** Bronze conserva evidencia; Silver estandariza; Gold expone métricas listas para consumo.
- **Idempotencia y trazabilidad.** Una ejecución puede reintentarse sin duplicar registros y cada métrica se relaciona con su ejecución y versión de feed.
- **IA con rol acotado.** n8n/Ollama interpreta las anomalías ya calculadas para redactar reportes; no escribe tablas, no cambia umbrales y no ejecuta el pipeline.
- **Calidad observable.** Frescura, completitud, coordenadas inválidas, duplicados y saltos imposibles se registran como métricas y registros rechazados.

## Datos fuente

| Fuente | Uso | Frecuencia |
| --- | --- | --- |
| GTFS estático oficial | Rutas, paradas, viajes, calendario y operación planificada | Ante nueva versión publicada |
| Validaciones mensuales | Demanda histórica por mes, componente y franja disponible | Mensual / histórico |
| Validaciones diarias | Accesos diarios, sujeto a validación de esquema y volumen | Diario |
| Salidas diarias del troncal | Flujos de salida por estación/portal y franja disponible | Diario |
| Salidas mensuales | Resumen histórico de salidas por intervalos disponibles | Mensual / histórico |
| GTFS-Realtime Vehicle Positions | Posiciones y vehículos activos | Cada 5 minutos; actualmente monitorizado por indisponibilidad del proveedor |
| GTFS-Realtime Trip Updates | Cambios y tiempos de viaje cuando estén disponibles | Cada 5 minutos; actualmente monitorizado |
| GTFS-Realtime Service Alerts | Alertas operativas | Cada 5 minutos; actualmente monitorizado |

Dejo las fuentes, contratos y límites analíticos en [docs/source_strategy.md](docs/source_strategy.md).

## Capas de datos

| Capa | Responsabilidad | Ejemplos |
| --- | --- | --- |
| Raw / Volume | Evidencia inmutable del origen | ZIP GTFS y manifiestos; protobuf queda para una ampliación |
| Bronze | Filas fuente y auditoría por snapshot | `bronze_gtfs_*` y auditorías de carga/calidad |
| Silver | Entidades estáticas tipadas y validadas | Diez entidades; `service_dates` derivada solo para 2026 |
| Gold | Datos de negocio preparados para consumo | Cobertura de viajes implementada localmente; publicación pendiente |

## Indicadores previstos para la primera entrega

- Catálogo publicado de rutas, agencias y ubicaciones, conservando la identidad del snapshot.
- Cobertura de viajes declarados: sin visitas, una visita o varias visitas.
- Contexto de frecuencias separado del conteo de patrones de viaje.
- Oferta asociada a fechas activas, con ficha de negocio y denominadores explícitos antes de implementar cada indicador.
- Advertencias de calidad y límites de interpretación visibles en Power BI.

Las métricas de demanda, operación observada y anomalías quedan en el alcance ampliado.
No llamaré anomalía a una variación aislada sin una línea base suficiente.

## Stack

- **Ingesta y transformación:** Python, PySpark, Databricks Jobs.
- **Lakehouse:** Unity Catalog, Volumes, Delta Lake y Databricks SQL.
- **Calidad:** reglas PySpark, tablas de auditoría y pruebas automatizadas.
- **Analítica:** Power BI; Gold prepara datos reutilizables y las medidas DAX responden a filtros.
- **Asistencia al modelado:** MCP oficial de Power BI, con conexión local probada en solo lectura.
- **Asistencia al reporte web:** habilidad Power BI disponible; acceso a la cuenta web todavía sin verificar.
- **Automatización de narrativa:** n8n y Ollama, en modo lectura.
- **Entrega:** GitHub, CI y documentación reproducible.

## Convenciones de tiempo y datos

- Las marcas de ingesta se almacenan en **UTC**.
- Los reportes y programación operativa se presentan en **America/Bogota**.
- Cada tabla Gold tendrá grano explícito. Las futuras métricas operativas podrán usar franjas de **5 minutos**; el GTFS estático se analizará según snapshot o fechas de servicio.
- Las claves, nombres de tablas y nombres de archivos se escriben en `snake_case`.
- Ningún secreto, token, archivo `.env` ni dato personal se sube a Git.

## Roadmap de cierre de la primera entrega

1. Raw, Bronze y diez entidades Silver disponibles para los snapshots existentes.
2. Coordinador manual comprobado con 2026; prueba de feed nuevo aplazada y programación deshabilitada.
3. Primera entidad Gold: cobertura de viajes, con procesador local y publicación en Workspace pendiente.
4. Modelo e indicadores de oferta planificada, con fichas de negocio y relaciones por snapshot.
5. Reporte Power BI y demostración reproducible del proyecto.

La [estrategia de fuentes](docs/source_strategy.md) conserva las ampliaciones de demanda, salidas y GTFS-Realtime.
No son requisitos para cerrar esta primera versión.

## Estado actual

Raw y Bronze conservan 2025-10-28 y 2026-09-29. Las diez entidades Silver habilitadas ya tienen despliegue funcional confirmado.
El Job Silver usa listas dinámicas y el Job principal terminó SUCCEEDED en la prueba manual con 2026.
Ese piloto no prueba la ingesta de una versión nueva, que dejé pendiente para otro momento.

Comencé Gold por la cobertura de viajes. La consulta Silver verificada conserva 181060 viajes y 9408893 visitas de 2026.
Identifica 739 viajes sin visitas, 61 con una visita y 180260 con varias visitas.
El procesador y notebook 20 son un prototipo local con validate por defecto; todavía no publiqué Gold en Workspace.
Antes de publicar definiré las decisiones del reporte y las métricas que las apoyan. La [evaluación de entidades pendientes](docs/remaining_silver_assessment.md) evita ampliar Silver solo por cantidad de tablas.
El [contrato](docs/contracts/trip_coverage.md), el [perfil](docs/trip_coverage_profile_2026.md) y el [plan Gold](docs/gold_plan.md) conservan las decisiones.

Documenté [Gold, medidas DAX y conexión con Power BI](docs/powerbi_mcp_setup.md).
La licencia del MCP quedó aceptada y probé una conexión local al modelo abierto.
Esa prueba no crea un modelo GTFS ni habilita cambios sobre el informe.
Las métricas candidatas del boceto conservan sus filtros, denominadores y límites como trabajo de definición.

La suite usa fixtures locales y no realiza llamadas reales de red como prueba automatizada.
Las pruebas nativas Spark/Delta requieren su entorno offline, como describen las guías existentes.
No instalé dependencias de pruebas dentro del repositorio.

### Plan de Silver

**Mi punto de entrada es el [notebook SQL guiado de agency](databricks/notebooks/silver/08_agency_sql_guiado.ipynb): una pregunta pequeña por bloque.** El [README de Silver](databricks/notebooks/silver/README.md) explica el recorrido y para qué sirve cada archivo. Las consultas largas ya ejecutadas con Genie están en apéndices opcionales; puedo dejarlas para después de entender las preguntas pequeñas.

El [informe de agency 2025](docs/agency_profile_2025.md) registra siete IDs distintos, sin duplicados ni ausencias en los seis campos publicados; agency_fare_url no fue publicada en ese snapshot. La [bitácora](BUILD_IN_PUBLIC.md#hito-12--primera-consulta-directa-a-databricks-mediante-genie) explica la conexión MCP Codex–Genie y sus ventajas. El [plan detallado](docs/silver_design.md) mantiene el orden completo de entidades.

Ya revisé las salidas del perfilador PySpark de agency para 2025 y 2026. El [contrato v1 de agency](docs/contracts/agency.md) define tipos, obligatoriedad y errores, conservando la identidad por versión, hash e ID. Implementé los validadores y el [notebook 09 de lectura](databricks/notebooks/silver/09_validate_gtfs_agency.ipynb). El [informe de ambos snapshots](docs/agency_validation_2025_2026.md) registra siete candidatos y cero rechazos por versión al ejecutar el núcleo Python; el notebook 09 también fue ejecutado y revisado para ambos snapshots en Databricks. Preparé el [notebook 10 y el Job manual](docs/silver_execution.md) para validar y publicar en una ejecución por snapshot. Agency ya fue publicada para ambos snapshots y el Job manual tuvo dos ejecuciones exitosas. Publiqué routes con Spark y el mismo notebook 10. La guía SQL con widgets de agency conserva su ejecución completa como pendiente; ese estado no impide las publicaciones ya comprobadas con el pipeline.

Verificación local revisada al 11 de noviembre de 2026: **105 casos únicos aprobados sin omisiones**, con Spark 4.0.1 y Delta 4.0.0 en Linux. Incluyen agency, routes, stops y calendarios, preservación de snapshots, rechazos, cuarentena y reejecución. Repetí los once casos Delta tras corregir el montaje temporal del contenedor; la [guía de pruebas](docs/silver_execution.md#verificación-local-de-calendarios) conserva los resultados de ambos pases. Agency, routes, stops y ambos calendarios ya se ejecutaron en el workspace. Comprobé físicamente las dos tablas nuevas y consulté sus datos; el cierre documenta esa evidencia sin inventar nuevos conteos. Las pruebas usan fixtures y tablas temporales, sin consultas a la API ni escrituras en Databricks.


### Routes: segundo contrato Silver y ejecución compartida

Perfilé routes con consultas de lectura y confirmé 676 filas de 2025 y 1.045 de 2026, sin IDs repetidos ni referencias huérfanas en los controles consultados. Definí [routes_v1](docs/contracts/routes.md): route_type pasa a int y los IDs, nombres y colores conservan string. Distingo el nombre largo nulo válido de 2025 de route_desc ausente en el encabezado 2026.

El [notebook 10](databricks/notebooks/silver/10_publish_gtfs_entity.ipynb) ahora tiene dos bloques y reutiliza el mismo escritor para agency y routes. Eliminé instalaciones, reinicios y conteos históricos repetidos por iteración. El Job ampliado agency → routes ya se ejecutó en Workspace después de corregir el doble entrecomillado de identificadores. La [guía de ejecución](docs/silver_execution.md) explica los cambios, los límites de rendimiento y los pasos de despliegue.


### Documentación visual

Preparé [flujo_pipeline](docs/flujo_pipeline/README.md) para explicar el mapa del lakehouse, el recorrido del Job Silver y el modelo GTFS que crecerá con las entidades. Instalé Archify como herramienta local de Codex y comprobé su diagnóstico. El [recorrido del Job Silver](docs/flujo_pipeline/job_silver/README.md) ya tiene vistas interactivas del orden del Job y de una iteración, comprobadas en navegador y revisadas visualmente. También puedo explorar el [mapa del lakehouse](docs/flujo_pipeline/mapa_lakehouse/mapa_lakehouse.html), el [modelo Silver actual](docs/flujo_pipeline/modelo_gtfs/modelo_silver.html) y el [panorama de crecimiento GTFS](docs/flujo_pipeline/modelo_gtfs/panorama_gtfs.html), con sus fuentes y revisión visual. Distingo archivos de tablas, claves validadas y etapas pendientes. Esta documentación no modifica el pipeline ni los datos.


### Stops: perfil, contrato e implementación Silver

El 10 de noviembre de 2026 revisé stops de ambos snapshots mediante Genie en lectura. Encontré 6.530 ubicaciones de tipo parada/plataforma en 2025; en 2026, 8.159 de ese tipo y 155 estaciones. Las 750 referencias a padres de 2026 resuelven dentro del mismo snapshot y los controles ejecutados no encontraron IDs duplicados ni coordenadas inválidas. Hay códigos opcionales ausentes y 27 / 1 nombres con espacios extremos, que ya contemplé al cerrar el contrato.

Conservo las seis consultas verificadas en [11_profile_gtfs_stops.ipynb](databricks/notebooks/silver/11_profile_gtfs_stops.ipynb) y los agregados e interpretación en [mi perfil de stops](docs/stops_profile_2025_2026.md). El notebook es una guía de lectura preparada, no un requisito adicional del Job; todavía no tiene una ejecución completa documentada como notebook. Stops ya tiene contrato implementado y ejecutado en Databricks; comprobé la tabla Silver y sus datos.

El [contrato stops_v1](docs/contracts/stops.md) ya convierte coordenadas a double y los dominios numéricos a int; conserva los identificadores como string. Limpio solo los espacios extremos del nombre y compruebo padres del mismo snapshot sin multiplicar hijos. Reutilizo el notebook 10 y el escritor común, con una tercera tarea ya incorporada al Job de Workspace. Los [pasos y el cierre de despliegue](docs/silver_execution.md#despliegue-de-stops_v1) distinguen el perfil inicial, las pruebas locales y la ejecución real comprobada.

Cada futura tabla Gold completará seis respuestas de negocio: pregunta, grano, ubicaciones, ausencias, claves y limitaciones que debe mostrar Power BI. Dejé la [ficha obligatoria en el plan](docs/silver_design.md#definición-de-negocio-obligatoria-para-cada-futura-tabla-gold).

El [siguiente bloque del plan](docs/silver_design.md#siguiente-bloque-calendar-y-calendar_dates) es calendar y calendar_dates: ya perfilé el patrón semanal y las excepciones e implementé sus procesadores localmente. Ya ejecuté sus tareas y comprobé las tablas y sus datos en Databricks. Service_dates ya está publicada y consultada para 2026; shape_points y trips ya funcionan. Frequencies ya está publicada. La siguiente entidad del plan es stop_times.

### Calendarios: perfil inicial y alcance temporal

Completé el [perfil conjunto de calendar y calendar_dates](docs/calendars_profile_2025_2026.md) con siete consultas definitivas conservadas en el [notebook 12](databricks/notebooks/silver/12_profile_gtfs_calendars.ipynb). Hay siete patrones por versión y 140 / 133 excepciones, sin errores en los controles de completitud, claves, formatos y procedencia ejecutados.

El snapshot 2025 contiene intervalos de 2000 a 2099 y excepciones de 2023. Conservo las fechas originales y dejo el hallazgo visible. Los [contratos calendar_v1/calendar_dates_v1](docs/contracts/calendars.md) ya están implementados y publicados en Databricks, con las dos tareas añadidas al Job y sus datos consultados; para service_dates elegí comenzar solo por el año 2026; las anomalías temporales de 2025 quedan documentadas.

La [guía de despliegue de calendarios](docs/silver_execution.md#despliegue-de-calendarios) conserva parámetros, resultados esperados y el orden de publicación. El escritor admite claves compuestas sin modificar los esquemas existentes de agency/routes/stops. Docker se usa solo para pruebas locales; las dependencias de producción no cambiaron.

El [cierre de calendarios](docs/silver_execution.md#cierre-de-la-ejecución-de-calendarios) registra su ejecución y disponibilidad. Ahora paso del patrón y las excepciones a fechas de servicio activas; el primer horizonte de service_dates será del 1 de enero al 31 de diciembre de 2026.


### Service_dates: del patrón semanal a días activos

Elegí comenzar solo con 2026. El [contrato derivado](docs/contracts/service_dates.md) convierte patrones y excepciones Silver en pares servicio-fecha. Como ejemplo, si el patrón activa los lunes pero una excepción retira un lunes festivo, ese día no aparece como activo; una adición puede activar otro día sin duplicarlo.

La [vista previa consultada con Genie](docs/service_dates_preview.md) produce 1.403 pares activos para siete servicios. Eso todavía no cuenta viajes ni pasajeros. El [notebook 13](databricks/notebooks/silver/13_preview_gtfs_service_dates.ipynb) conserva las tres consultas de lectura. El módulo PySpark y la sexta tarea de la plantilla reutilizan el notebook 10; las fuentes se fijan por versión Delta y el horizonte queda explícito. La [guía de ejecución](docs/silver_execution.md#primera-derivación-service_dates-de-2026) distingue pruebas locales y la publicación ya comprobada en Workspace.


La verificación de service_dates terminó con 24 pruebas seleccionadas aprobadas sin omisiones, incluidas ocho nuevas y tres integraciones Delta en total. La derivación ya está publicada en Databricks: comprobé 1.403 filas y claves distintas, siete servicios y fechas de 2026-01-01 a 2026-12-31. Las cinco entidades fuente anteriores también están publicadas. Continúo con shape_points, los puntos ordenados de cada trazado.


### Shape_points: entender el trazado antes de publicarlo

Completé el [perfil de shapes de ambos snapshots](docs/shape_points_profile_2025_2026.md): 909.878 / 926.501 puntos para 676 / 1.045 trazados. Conservé nueve consultas definitivas en el [notebook 14](databricks/notebooks/silver/14_profile_gtfs_shape_points.ipynb). Las claves y conversiones revisadas no presentan errores; sí hay puntos consecutivos de igual coordenada y cuatro trazados sin referencias desde trips en 2025, que no elimino como si fueran filas duplicadas.

El [contrato shape_points_v1](docs/contracts/shape_points.md) distingue reglas, advertencias y limitaciones; el [plan](docs/shape_points_plan.md) conserva el estado de cada etapa. La implementación posterior habilita el procesador y amplía la plantilla del Job. El despliegue funcional de shape_points en Workspace ya está comprobado.


Implementé shape_points_v1 con Spark nativo. Conserva puntos repetidos y genera advertencias. Los errores obligatorios bloquean el snapshot completo. Reutiliza notebook 10 y el escritor existente. La plantilla incorpora una séptima tarea para ambos snapshots. La [guía](docs/silver_execution.md#despliegue-de-shape_points_v1) distingue pruebas locales y despliegue funcional comprobado.


La implementación de shape_points pasó 36 pruebas seleccionadas sin omisiones. Incluyen trece nuevas y tres integraciones Delta en total. El flujo de shape_points ya funciona en Databricks. El [cierre](docs/silver_execution.md#cierre-de-la-ejecución-de-shape_points) registra la evidencia disponible.


Trips, frequencies y stop_times ya tienen despliegue funcional. La [selección de snapshots](docs/silver_design.md#automatización-pendiente-selección-de-snapshots-silver) usa listas dinámicas y tiene piloto NO_WORK comprobado. Conservo la variante manual para pruebas controladas. La ingesta de un feed nuevo sigue pendiente de prueba integral.


### Trips: perfil, implementación y despliegue funcional

Completé el [perfil de trips](docs/trips_profile_2025_2026.md). Hay 107.162 / 181.060 claves únicas y las referencias resuelven. El [notebook 15](databricks/notebooks/silver/15_profile_gtfs_trips.ipynb) conserva diez consultas verificadas. El [contrato](docs/contracts/trips.md) mantiene IDs y texto como string.

La fuente 2025 no publica trip_headsign. La fuente 2026 lo publica sin contenido no blanco, según la comparación Staging/Bronze. No fabricaré destinos ni interpretaré cada fila como un bus físico. Trips ya funciona en Databricks mediante el Job compartido.


Implementé trips_v1 con referencias a rutas, servicios y trazados del mismo snapshot. La plantilla incorpora una octava tarea y mantiene las siete anteriores. Notebook 10 conserva sus dos bloques ejecutables. Las 37 pruebas seleccionadas pasaron sin omisiones. La [guía](docs/silver_execution.md#despliegue-de-trips_v1) conserva parámetros y resultados esperados.


La implementación de trips pasó 37 pruebas seleccionadas sin omisiones. Incluyen catorce nuevas y dos integraciones Delta en total. El [cierre de trips](docs/silver_execution.md#cierre-de-la-ejecución-de-trips) registra el despliegue funcional confirmado. Continúo con frequencies.

### Frequencies: ventanas de servicio antes de stop_times

Completé el [perfil de frequencies](docs/frequencies_profile_2025_2026.md): 2 / 14 ventanas, todas relacionadas con trips Silver.
El [notebook 16](databricks/notebooks/silver/16_profile_gtfs_frequencies.ipynb) conserva nueve consultas correctas de lectura.
Los controles ejecutados no encontraron errores. Todas las ventanas corresponden a C_1, de cable aéreo.

Preparé la [contrato implementado](docs/contracts/frequencies.md), con horas fuente, segundos de servicio e intervalos tipados.
Exact_times no está publicado. Propongo conservar su ausencia y derivar explícitamente la interpretación predeterminada del estándar.
Implementé el procesador y añadí su tarea a la plantilla. El despliegue funcional de frequencies ya está confirmado. Reutilicé notebook 10 y el escritor común. Las ocho tareas anteriores conservan su configuración.

La [guía de despliegue](docs/silver_execution.md#despliegue-de-frequencies_v1) contiene los parámetros de la novena tarea.

La implementación de frequencies pasó 42 pruebas seleccionadas sin omisiones, incluidas trece nuevas y dos integraciones Delta en total.
Frequencies ya está publicada en Workspace. El siguiente incremento es stop_times, orden 8 del plan.


### Stop_times: despliegue funcional confirmado

Completé el [perfil](docs/stop_times_profile_2025_2026.md) y el [contrato stop_times_v1](docs/contracts/stop_times.md).
Una fila representa una visita planificada de un viaje a una parada.
El [notebook 17](databricks/notebooks/silver/17_profile_gtfs_stop_times.ipynb) conserva siete consultas verificadas de lectura.
El procesador Spark tipa campos, comprueba horas y referencias, y reutiliza notebook 10.
La plantilla añade publish_stop_times como décima tarea; las nueve anteriores conservan su configuración.

Conservo 61 visitas aisladas con advertencia y registro 739 viajes sin visitas en 2026.
Stop_times ya se ejecutó en Databricks y comprobé sus datos. Completo diez entidades Silver con despliegue funcional.
El [despliegue](docs/silver_execution.md#despliegue-de-stop_times_v1) separa validate, publish y comprobación final.

## Recorrido de documentación actualizado

Empiezo por las [preguntas de negocio](docs/power_bi_user_stories.md), el [diseño del reporte](docs/power_bi_navigation_images.md) y el [plan de cierre](docs/gold_plan.md).
La [documentación Archify](docs/flujo_pipeline/README.md) reúne seis vistas con estados explícitos.
El [flujo analítico](docs/flujo_pipeline/consumo_analitico/consumo_analitico.html) distingue Gold, medidas DAX, reporte y herramientas de asistencia.
Los contratos explican reglas y grano; los diagramas permiten recorrer sus relaciones.
