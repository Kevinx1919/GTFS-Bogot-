# Mi mapa del lakehouse

[Abro el mapa interactivo](mapa_lakehouse.html).

Actualicé esta vista el 12 de noviembre de 2026.
Sigo el dato desde la fuente pública hasta Silver y distingo archivos, transformaciones y tablas.

| Zona | Qué conservo |
| --- | --- |
| Raw | ZIP original y manifiestos en el Volume raw_gtfs. |
| Staging | TXT extraídos en el Volume staging_gtfs. |
| Bronze | Filas fuente y procedencia en tablas bronze_gtfs_*. |
| Silver fuente | Nueve entidades tipadas y validadas desde Bronze. |
| Silver derivada | Service_dates: días activos calculados desde calendarios Silver, solamente para 2026. |
| Gold y Power BI | Métricas y consumo analítico pendientes. |

Mantengo Bronze y Silver en workspace.gtfs_bogota.
Sus responsabilidades y prefijos distinguen las capas. Un Volume almacena archivos; no equivale a una tabla Delta.

## Qué entradas necesita Silver

Las entidades fuente reciben filas Bronze y el encabezado TXT del mismo snapshot.
El encabezado distingue una columna ausente de una columna publicada con valores nulos.
Las dependencias Silver se validan según el contrato de cada entidad.

Service_dates recibe calendarios Silver y un horizonte explícito.
El mapa muestra ambas entradas. El año del feed no sustituye una decisión de horizonte.

Las diez entidades tienen despliegue funcional confirmado durante el desarrollo.
El [cierre de stop_times](../../silver_execution.md#cierre-de-la-ejecución-de-stop_times) registra la última confirmación.
Los conteos de perfil, las pruebas locales y las confirmaciones de publicación conservan evidencias separadas.

## Qué no interpreto como operación real

El GTFS estático describe oferta planificada.
Las ventanas de frequencies no cuentan vehículos observados ni garantizan salidas exactas.
Stop_times ya tiene despliegue funcional confirmado. Gold y Power BI siguen pendientes.
La selección automática de snapshots continúa pendiente 8b.

Uso Genie para explorar en lectura. El pipeline versionado ejecuta transformaciones y escrituras.
El mapa no consulta Databricks ni representa telemetría en vivo.

## Fuente y comprobación

La [fuente editable](mapa_lakehouse.dataflow.json) enlaza el código de 23dab92a64b6a1a9563274417b6928925baf1b4d.
La vista pasó controles automáticos de estructura, referencias, HTML y navegador.
El [resumen público](verificacion.json) conserva hashes y medidas de esta revisión.
No hice una nueva revisión de capturas. El aviso sobre la ruta del encabezado queda registrado.
Genero fuera de OneDrive y copio el HTML comprobado sin cambiar sus bytes.

La clasificación de cobertura antes de métricas Gold permanece planificada.
Conservo el aviso de recorrido largo del encabezado TXT en el resumen, sin quitar esa entrada real del pipeline.
