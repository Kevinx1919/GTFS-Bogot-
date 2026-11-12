# Bogotá GTFS Mobility Lakehouse

Estoy construyendo un lakehouse de movilidad para Bogotá mientras aprendo Databricks y PySpark. Empecé con el GTFS estático para entender la oferta planificada de TransMilenio; más adelante quiero relacionarlo con validaciones y salidas oficiales. Incorporaré GTFS-Realtime cuando la fuente esté disponible. Mi objetivo es tener un proyecto de portafolio que pueda explicar desde la ingesta hasta el análisis en Power BI.

> La velocidad operacional se deriva de posiciones consecutivas de vehículos. No representa ni pretende medir la congestión total de la ciudad.

## Problema de negocio

Los equipos de operación necesitan detectar degradaciones del servicio y entender qué rutas, franjas horarias o eventos las explican. La información en tiempo real es efímera y los archivos GTFS estáticos describen la operación planificada, por lo que se requiere conservar ambos y convertirlos en métricas confiables.

Con las fuentes y validaciones necesarias, quiero llegar a responder preguntas como:

- ¿Qué rutas tienen menor cobertura de vehículos frente a su patrón histórico?
- ¿Cómo evoluciona la velocidad operacional por ruta, dirección y franja de cinco minutos?
- ¿Qué alertas de servicio y actualizaciones de viajes coinciden con una degradación operativa?
- ¿Qué tan fresco y completo está el dato que alimenta el tablero?

## Arquitectura objetivo

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
| Raw / Volume | Evidencia inmutable del origen | `.pb`, ZIP GTFS, manifiestos JSON |
| Bronze | Registro de snapshots y auditoría | `bronze_feed_snapshot`, `bronze_ingestion_audit` |
| Silver | Datos decodificados y validados | posiciones, alertas, actualizaciones, rutas, paradas |
| Gold | Métricas de negocio por intervalo | velocidad operacional, cobertura de flota, confiabilidad, frescura |

## Métricas y anomalías iniciales

- Demanda por componente, estación/portal y franja horaria cuando la fuente lo permita.
- Cambios de demanda frente al patrón histórico comparable.
- Cambios de oferta planificada: rutas, paradas, viajes, calendarios y frecuencias entre versiones GTFS.
- Proxy de presión demanda-oferta planificada, únicamente después de validar llaves y granularidad compatibles.
- Feed sin actualización, fallos consecutivos y frescura del último snapshot exitoso.
- Cobertura de vehículos y velocidad operacional solo cuando GTFS-Realtime vuelva a estar disponible.

Antes de llamar anomalía a un resultado, necesito una línea base suficiente. Durante la etapa inicial quiero reunir evidencia y revisar calidad, sin convertir una variación aislada en una conclusión definitiva.

## Stack

- **Ingesta y transformación:** Python, PySpark, Databricks Jobs.
- **Lakehouse:** Unity Catalog, Volumes, Delta Lake y Databricks SQL.
- **Calidad:** reglas PySpark, tablas de auditoría y pruebas automatizadas.
- **Analítica:** Power BI.
- **Automatización de narrativa:** n8n y Ollama, en modo lectura.
- **Entrega:** GitHub, CI y documentación reproducible.

## Convenciones de tiempo y datos

- Las marcas de ingesta se almacenan en **UTC**.
- Los reportes y programación operativa se presentan en **America/Bogota**.
- Cada tabla Gold tendrá grano explícito. Las futuras métricas operativas podrán usar franjas de **5 minutos**; el GTFS estático se analizará según snapshot o fechas de servicio.
- Las claves, nombres de tablas y nombres de archivos se escriben en `snake_case`.
- Ningún secreto, token, archivo `.env` ni dato personal se sube a Git.

## Roadmap

1. Validar fuentes oficiales, contratos y conectividad desde Databricks.
2. Descubrir automáticamente las versiones GTFS y persistir un plan de ingesta reproducible.
3. Implementar captura Raw idempotente del GTFS estático versionado y backfill histórico.
4. Inspeccionar e incorporar validaciones mensuales como primera fuente de demanda.
5. Incorporar salidas y, después, validaciones diarias según su esquema y volumen.
6. Construir Bronze/Silver, modelo dimensional y controles de calidad.
7. Comparar oferta planificada y demanda observada sin inferir ocupación o puntualidad.
8. Reintentar la incorporación de GTFS-Realtime con auditoría y reglas de frescura.
9. Construir métricas Gold, Power BI y detección determinista de anomalías.
10. Conectar n8n/Ollama únicamente a una vista de anomalías aprobadas.
10. Automatizar, observar costos y documentar operación/recuperación.

## Estado actual

Ya conservé los snapshots GTFS estáticos `2025-10-28` y `2026-09-29` en Raw y los cargué en tablas Delta Bronze. El Job manual `gtfs_bogota_bronze_manual` ejecutó con éxito Raw, Staging, cargas Bronze y validación de calidad. La comparación de esquemas identificó cinco cambios entre versiones sin fallos bloqueantes; una reejecución conservó el conteo esperado de 9.408.893 filas de `stop_times` para 2026.

El notebook de descubrimiento de versiones funciona, pero todavía tengo que conectarlo al Job. También me falta manejar «sin novedades», probar recuperación y dejar la observabilidad y configuración versionada listas antes de programarlo automáticamente. Agency ya está publicada en Silver y su Job manual terminó con éxito para ambos snapshots. Routes también quedó publicada después de sincronizar la corrección del lector y ejecutar el Job ampliado; comprobé la existencia de las tablas Silver. Stops también quedó publicada: ejecuté su Job y comprobé los datos con una consulta breve. El detalle y las limitaciones de este primer hito están en [Build in Public](BUILD_IN_PUBLIC.md#hito-08--primer-flujo-raw-a-bronze-ejecutado-con-éxito).

### Revisión del contrato antes de Silver

Las correcciones locales de Raw/Bronze admiten las combinaciones válidas de calendarios, detienen Raw ante estructura incompleta y amplían la auditoría de procedencia. Las 16 pruebas locales pasan. Al repetir la validación de ambos snapshots obtuve estos resultados: 2025 terminó en `PASSED`, sin fallos ni advertencias; 2026 en `WARNING`, sin fallos bloqueantes y con cinco advertencias de evolución de esquema conocida. En 04, las ocho entidades de referencia de cada versión omitieron nuevas inserciones al reconocer el hash existente. Ese hito permitió perfilar agencias y rutas y definir sus contratos Silver, ya implementados y publicados. Después implementé y ejecuté stops; también publiqué calendar/calendar_dates y ahora preparo service_dates. El detalle está en el [Hito 09](BUILD_IN_PUBLIC.md#hito-09--revisar-el-contrato-de-bronze-antes-de-diseñar-silver) y el [procedimiento de revalidación](docs/notebook_runbook.md#revalidación-en-databricks-de-los-snapshots-existentes).

Para las pruebas de agency, instalo antes `databricks/requirements-silver.txt` en un entorno virtual. La suite no realiza llamadas de red: `python -B -m unittest discover -s tests -v`. Las pruebas nativas Spark requieren además PySpark y Java.

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

El [siguiente bloque del plan](docs/silver_design.md#siguiente-bloque-calendar-y-calendar_dates) es calendar y calendar_dates: ya perfilé el patrón semanal y las excepciones e implementé sus procesadores localmente. Ya ejecuté sus tareas y comprobé las tablas y sus datos en Databricks. Service_dates ya está publicada y consultada para 2026; la siguiente entidad del plan es shape_points.

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

El [contrato shape_points_v1](docs/contracts/shape_points.md) distingue reglas, advertencias y limitaciones; el [plan](docs/shape_points_plan.md) conserva el estado de cada etapa. La implementación posterior habilita el procesador y amplía la plantilla del Job. Su publicación en Workspace sigue pendiente.


Implementé shape_points_v1 con Spark nativo. Conserva puntos repetidos y genera advertencias. Los errores obligatorios bloquean el snapshot completo. Reutiliza notebook 10 y el escritor existente. La plantilla incorpora una séptima tarea para ambos snapshots. La [guía](docs/silver_execution.md#despliegue-de-shape_points_v1) distingue implementación local y publicación pendiente.


La implementación de shape_points pasó 36 pruebas seleccionadas sin omisiones. Incluyen trece nuevas y tres integraciones Delta en total. La primera publicación en Databricks sigue pendiente.
