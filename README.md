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
- La granularidad de las métricas Gold es de **5 minutos**.
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

El notebook de descubrimiento de versiones funciona, pero todavía tengo que conectarlo al Job. También me falta manejar «sin novedades», probar recuperación y dejar la observabilidad y configuración versionada listas antes de programarlo automáticamente. Silver todavía no está implementada. El detalle y las limitaciones de este primer hito están en [Build in Public](BUILD_IN_PUBLIC.md#hito-08--primer-flujo-raw-a-bronze-ejecutado-con-éxito).

### Revisión del contrato antes de Silver

Las correcciones locales de Raw/Bronze admiten las combinaciones válidas de calendarios, detienen Raw ante estructura incompleta y amplían la auditoría de procedencia. Las 16 pruebas locales pasan. Al repetir la validación de ambos snapshots obtuve estos resultados: 2025 terminó en `PASSED`, sin fallos ni advertencias; 2026 en `WARNING`, sin fallos bloqueantes y con cinco advertencias de evolución de esquema conocida. En 04, las ocho entidades de referencia de cada versión omitieron nuevas inserciones al reconocer el hash existente. Mi siguiente paso es perfilar agencias y rutas para definir su contrato Silver. El detalle está en el [Hito 09](BUILD_IN_PUBLIC.md#hito-09--revisar-el-contrato-de-bronze-antes-de-diseñar-silver) y el [procedimiento de revalidación](docs/notebook_runbook.md#revalidación-en-databricks-de-los-snapshots-existentes).

Pruebas locales sin red ni Spark instalado: `py -B -m unittest discover -s tests -v`.

### Plan de Silver

**Mi punto de entrada es el [notebook SQL guiado de agency](databricks/notebooks/silver/08_agency_sql_guiado.ipynb): una pregunta pequeña por bloque.** El [README de Silver](databricks/notebooks/silver/README.md) explica el recorrido y para qué sirve cada archivo. Las consultas largas ya ejecutadas con Genie están en apéndices opcionales; puedo dejarlas para después de entender las preguntas pequeñas.

El [informe de agency 2025](docs/agency_profile_2025.md) registra siete IDs distintos, sin duplicados ni ausencias en los seis campos publicados; agency_fare_url no fue publicada en ese snapshot. La [bitácora](BUILD_IN_PUBLIC.md#hito-12--primera-consulta-directa-a-databricks-mediante-genie) explica la conexión MCP Codex–Genie y sus ventajas. El [plan detallado](docs/silver_design.md) mantiene el orden completo de entidades.

Sigo revisando agency: quiero entender bien el resultado de 2025, perfilar 2026 y definir el contrato antes de transformar. No hay tablas Silver creadas. El perfilador PySpark queda como alternativa de automatización; todavía no he ejecutado en Databricks la guía nueva ni ese notebook.

Verificación local del perfilador: 22 pruebas aprobadas y 3 omitidas que requieren Spark real. Las consultas SQL históricas fueron verificadas por separado en Databricks.
