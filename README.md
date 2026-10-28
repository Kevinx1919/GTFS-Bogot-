# Bogotá GTFS Mobility Lakehouse

Lakehouse de movilidad urbana para Bogotá. El proyecto integra la oferta planificada de GTFS estático con demanda observada en validaciones y salidas del sistema. GTFS-Realtime se incorpora cuando el proveedor esté disponible para enriquecer el análisis con operación de flota. Está diseñado como un proyecto de portafolio de ingeniería de datos, con Databricks, PySpark, Delta Lake, Power BI y n8n/Ollama.

> La velocidad operacional se deriva de posiciones consecutivas de vehículos. No representa ni pretende medir la congestión total de la ciudad.

## Problema de negocio

Los equipos de operación necesitan detectar degradaciones del servicio y entender qué rutas, franjas horarias o eventos las explican. La información en tiempo real es efímera y los archivos GTFS estáticos describen la operación planificada, por lo que se requiere conservar ambos y convertirlos en métricas confiables.

El producto responderá preguntas como:

- ¿Qué rutas tienen menor cobertura de vehículos frente a su patrón histórico?
- ¿Cómo evoluciona la velocidad operacional por ruta, dirección y franja de cinco minutos?
- ¿Qué alertas de servicio y actualizaciones de viajes coinciden con una degradación operativa?
- ¿Qué tan fresco y completo está el dato que alimenta el tablero?

## Arquitectura objetivo

```text
GTFS estático + validaciones/salidas oficiales + GTFS-Realtime
                |
                v
Databricks Jobs por frecuencia de fuente (America/Bogota)
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

Las fuentes, contratos y límites analíticos se documentan en [docs/source_strategy.md](docs/source_strategy.md).

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

Las líneas base requieren historial suficiente; durante los primeros días el pipeline recolecta evidencia y reporta calidad, sin presentar una conclusión de anomalía estadística como definitiva.

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
2. Implementar captura raw idempotente del GTFS estático versionado.
3. Inspeccionar e incorporar validaciones mensuales como primera fuente de demanda.
4. Incorporar salidas y, después, validaciones diarias según su esquema y volumen.
5. Construir Bronze/Silver, modelo dimensional y controles de calidad.
6. Comparar oferta planificada y demanda observada sin inferir ocupación o puntualidad.
7. Reintentar la incorporación de GTFS-Realtime con auditoría y reglas de frescura.
8. Construir métricas Gold, Power BI y detección determinista de anomalías.
9. Conectar n8n/Ollama únicamente a una vista de anomalías aprobadas.
10. Automatizar, observar costos y documentar operación/recuperación.

## Estado actual

La primera versión GTFS estática (`2025-10-28`) fue validada y preservada en Raw con manifiesto. También existe la primera tabla Delta Bronze, `bronze_gtfs_routes`, con 676 rutas. Los notebooks de Raw y Bronze están versionados en `databricks/notebooks`; las entidades restantes de Bronze están listas para ejecutarse desde el Git folder de Databricks.
