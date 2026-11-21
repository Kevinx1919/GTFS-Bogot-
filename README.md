# Bogotá GTFS Mobility Lakehouse

Un proyecto de ingeniería de datos para explorar la **oferta de transporte publicada para Bogotá**, desde archivos GTFS hasta un reporte de Power BI.
Lo desarrollé mientras aprendía Databricks, PySpark y modelado analítico.

**Estado: v1 local funcional de portafolio · noviembre de 2026.**
El alcance entregado incluye ingesta, Bronze, diez entidades Silver, cuatro tablas Gold y cuatro paneles de Power BI.
La navegación del informe está comprobada. Conservo documentadas las comprobaciones pendientes y las ampliaciones opcionales.

## Qué puedo responder

| Panel | Pregunta de negocio | Qué permite revisar |
| --- | --- | --- |
| **Panorama de oferta** | ¿Qué cambia entre dos fechas y dónde se concentra? | Rutas con programación, viajes sin frecuencia, plantillas, diferencias y ubicaciones relacionadas. |
| **Programación** | ¿Qué días y horas publica la selección? | Calendario, servicios activos, extremos horarios y ventanas de frecuencia. |
| **Red publicada** | ¿Qué ubicaciones relaciona una ruta y cuáles comparte? | Coordenadas, tipos de ubicación, estaciones padre y relaciones ruta–ubicación. |
| **Revisión de información** | ¿Qué casos necesitan aclaración antes de analizar? | Viajes sin visitas, visitas únicas, plantillas y exclusiones del perfil horario. |

Panorama funciona también como entrada al informe.
Las historias representan escenarios de portafolio; no son entrevistas ni encargos reales de TransMilenio.

**El GTFS estático describe programación publicada.**
No demuestra viajes realizados, pasajeros, ocupación, puntualidad, espera ni cumplimiento contractual.
Para responder esas preguntas necesitaría fuentes observadas y correspondencias verificadas.

## Arquitectura implementada

```text
GTFS estático oficial
        ↓
Raw: ZIP inmutable + manifiesto + SHA-256
        ↓
Staging: TXT extraídos
        ↓
Bronze Delta: filas fuente + procedencia + calidad
        ↓
Silver Delta: entidades tipadas, validadas y relacionadas
        ↓
Gold Delta: hechos con grano y definición de negocio
        ↓
Power BI: modelo + DAX + HTML/SVG + controles nativos
```

Raw y Staging son archivos en Volumes; Bronze, Silver y Gold son tablas Delta.
Las capas comparten el schema del proyecto y se distinguen por responsabilidad y prefijo.
Cada snapshot conserva versión y SHA-256; las relaciones incorporan también el ID de negocio.
Conservo los originales para poder rastrear una cifra hasta su fuente.

El coordinador manual conecta descubrimiento, Bronze y Silver.
Gold y la actualización de Power BI conservan pasos manuales documentados.
No presento ese recorrido como automatización completa de extremo a extremo.

## Datos y resultados disponibles

Raw y Bronze conservan los snapshots **2025-10-28** y **2026-09-29**.
Las diez entidades Silver habilitadas son agency, routes, stops, calendar, calendar_dates, service_dates, shape_points, trips, frequencies y stop_times.
Service_dates cubre explícitamente 2026; las demás entidades mantienen el histórico según sus contratos.
Feed_info y las entidades tarifarias fueron evaluadas y quedaron fuera del alcance inicial del reporte.

Las cuatro Gold están publicadas e importadas para 2026:

| Tabla | Una fila representa | Filas |
| --- | --- | ---: |
| gold_gtfs_trip_coverage | Un viaje declarado del snapshot. | 181.060 |
| gold_gtfs_route_service_day | Una ruta y fecha de servicio. | 305.165 |
| gold_gtfs_route_stop | Una pareja ruta–ubicación. | 62.715 |
| gold_gtfs_trip_timing | Un viaje declarado con clasificación de sus extremos horarios. | 181.060 |

Cobertura conserva 9.408.893 visitas publicadas: 739 viajes no tienen visitas, 61 tienen una y 180.260 tienen varias.
La clasificación horaria identifica 180.246 viajes elegibles y separa catorce plantillas por frecuencia.
Estas cantidades describen la publicación de 2026; no constituyen conteos de vehículos ni pasajeros.
Las [fichas Gold](docs/contracts) conservan pregunta, grano, ubicaciones, ausencias, claves y límites de interpretación.

## Power BI: cálculo, diseño e interacción

Gold prepara relaciones, categorías y agregados reutilizables.
DAX calcula indicadores y comparaciones según los filtros elegidos.
HTML Content presenta esos resultados mediante HTML, CSS y SVG, con identidad roja y amarilla.
Los botones y selectores nativos gestionan navegación y filtros.

- El menú conecta los cuatro paneles y resalta la página actual.
- Panorama incluye tarjetas ilustradas de Troncal, Zonal (SITP), Alimentación, Dual y TransMiCable.
- Esas tarjetas filtran Panorama localmente; los desplegables sincronizan componente y ruta entre páginas.
- Los mapas muestran coordenadas GTFS y relaciones de catálogo; no posiciones de vehículos en tiempo real.

Las vistas previas HTML utilizan resultados DAX precalculados y un conjunto acotado de selecciones.
No consultan Databricks en vivo ni sustituyen el modelo completo.
El JavaScript de esas vistas previas no se ejecuta dentro de HTML Content en Power BI.

[Panorama](BI/imagenes/panorama/panorama_v2_preview.html) · [Programación](BI/imagenes/programacion/programacion_preview.html) · [Red publicada](BI/imagenes/red_publicada/red_publicada_preview.html) · [Revisión](BI/imagenes/revision_informacion/revision_preview.html).
Para visualizar estos HTML desde GitHub, descargo el proyecto y los abro en un navegador.

## Documentación que puedo explorar

Utilicé [Archify](https://github.com/tt-a1i/archify) para explicar el proyecto con diagramas interactivos HTML.
Conservo fuentes editables, referencias al código y resúmenes de verificación.

| Vista | Qué explica |
| --- | --- |
| [Mapa del lakehouse](docs/flujo_pipeline/mapa_lakehouse/mapa_lakehouse.html) | Archivos, transformaciones, tablas y consumo. |
| [Recorrido Silver](docs/flujo_pipeline/job_silver/recorrido_job.html) | Planificación dinámica y orden del Job. |
| [Una iteración](docs/flujo_pipeline/job_silver/iteracion_snapshot.html) | Validación, publicación, cuarentena y errores. |
| [Modelo Silver](docs/flujo_pipeline/modelo_gtfs/modelo_silver.html) | Columnas y referencias por snapshot. |
| [Alcance GTFS](docs/flujo_pipeline/modelo_gtfs/panorama_gtfs.html) | Entidades implementadas y alcance posterior. |
| [Consumo analítico](docs/flujo_pipeline/consumo_analitico/consumo_analitico.html) | Preguntas, Gold, modelo, medidas y paneles. |

Los diagramas explican el sistema; no ejecutan Jobs ni muestran telemetría.
La [guía de documentación visual](docs/flujo_pipeline/README.md) distingue código referenciado y confirmaciones de desarrollo.

## Cómo revisar o reproducir el proyecto

1. Reviso las [fuentes oficiales y sus límites](docs/source_strategy.md).
2. Preparo Databricks siguiendo el [runbook de notebooks](docs/notebook_runbook.md), las [guías Silver](docs/silver_execution.md) y el [coordinador](docs/pipeline_coordinator.md).
3. Valido y publico Gold según sus guías, conservando el horizonte y la identidad del snapshot.
4. Configuro la conexión local y abro [BI/GFTS_BI.pbip](BI/GFTS_BI.pbip) en Power BI Desktop compatible con PBIP/PBIR.
5. Actualizo las tablas importadas y reviso los cuatro paneles con sus definiciones de negocio.

El [procedimiento manual completo](docs/power_bi_actualizacion_manual.md) ordena esos pasos.
Para una copia nueva, creo expressions.tmdl desde [la plantilla sin datos de entorno](BI/GFTS_BI.SemanticModel/definition/expressions.tmdl.example) y configuro hostname y ruta HTTP de mi SQL Warehouse.
Los valores locales y las credenciales permanecen fuera de Git.
Mi copia local conserva su conexión existente; la plantilla sirve para preparar otros equipos.
No distribuyo cachés, credenciales ni el PBIX anterior como fuente del proyecto.

## Organización del repositorio

```text
databricks/
  notebooks/        Ingesta, perfiles y ejecución por bloques
  gtfs_bronze/      Descubrimiento y controles Bronze
  gtfs_silver/      Contratos, validación, publicación y planificación
  gtfs_gold/        Hechos y publicadores Gold
  jobs/             Plantillas y configuración versionadas
  sql/              Consultas de revisión
BI/
  GFTS_BI.pbip      Proyecto Power BI
  *.Report/        Páginas, visuales y recursos PBIR
  *.SemanticModel/ Modelo, relaciones, expresiones y medidas TMDL
  medidas/         Fuentes DAX y definiciones
  imagenes/        SVG, CSS y vistas previas
  modelado/        Explicación del modelo
  consumo/         Selección de campos y relaciones

docs/               Contratos, fuentes, decisiones y guías
  flujo_pipeline/   Diagramas interactivos Archify
tests/              Fixtures, mocks y pruebas de transformación
```

## Qué comprobé y qué queda fuera del cierre

Las publicaciones de Databricks, sus conteos y las consultas de consumo tienen evidencia en sus guías.
El informe tiene comprobaciones DAX, validación PBIR y navegación confirmada durante la revisión.
Los seis diagramas conservan sus comprobaciones y hashes; tres se actualizaron en la última revisión.
Las pruebas del pipeline utilizan fixtures o dobles; las pruebas Spark/Delta necesitan su entorno documentado.
No interpreto una validación de archivos como prueba de una actualización completa en otro equipo.

Doy por cerrado el alcance funcional de esta **v1 local de portafolio**.
Conservo como pendientes de endurecimiento la revisión integral de filtros/rendimiento y una ejecución registrada del procedimiento completo de actualización.
La publicación en Power BI Service, un feed nuevo y la automatización Gold/Power BI son ampliaciones opcionales.
Demanda, salidas, GTFS-Realtime y n8n/Ollama requieren fuentes disponibles y preguntas adicionales; no son funciones implementadas de esta entrega.
No mantengo un monitor de realtime en ejecución por haber investigado sus endpoints.

[Estado y evidencias](docs/project_status.md) · [Cierre y pendientes](docs/power_bi_cierre_v1.md) · [Preguntas de negocio](docs/power_bi_user_stories.md) · [Modelo BI](BI/modelado/README.md) · [Bitácora](BUILD_IN_PUBLIC.md).
