# Mi mapa del lakehouse

[Abro el mapa interactivo](mapa_lakehouse.html).

Actualicé esta vista el 20 de noviembre de 2026.
Sigo el dato desde la fuente pública hasta Silver y distingo archivos, transformaciones y tablas.

| Zona | Qué conservo |
| --- | --- |
| Raw | ZIP original y manifiestos en el Volume raw_gtfs. |
| Staging | TXT extraídos en el Volume staging_gtfs. |
| Bronze | Filas fuente y procedencia en tablas bronze_gtfs_*. |
| Silver fuente | Nueve entidades tipadas y validadas desde Bronze. |
| Silver derivada | Service_dates: días activos calculados desde calendarios Silver, solamente para 2026. |
| Gold | Cuatro tablas publicadas e importadas para 2026. |
| Power BI | Modelo conectado y cuatro paneles implementados; navegación nativa confirmada. |

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
Stop_times tiene despliegue funcional confirmado. Las cuatro Gold y el modelo local Power BI ya están disponibles.
El planificador Silver ya entrega listas dinámicas; el piloto NO_WORK quedó comprobado.

Uso Genie para explorar en lectura. El pipeline versionado ejecuta transformaciones y escrituras.
El mapa no consulta Databricks ni representa telemetría en vivo.

## Fuente y comprobación

La [fuente editable](mapa_lakehouse.dataflow.json) enlaza el código de 5c23d4e327fb9d90f407dbfc12678623106e4ad6.
La vista pasó controles automáticos de estructura, referencias, HTML y navegador.
El [resumen público](verificacion.json) conserva hashes y medidas de esta revisión.
Las comprobaciones actuales se registran en el resumen público. El aviso de rutas se conserva cuando corresponde.
Genero fuera de OneDrive y copio el HTML comprobado sin cambiar sus bytes.

Las cuatro Gold conservan contratos, procesadores y publicaciones confirmadas.
Service_dates alimenta route_service_day; no es entrada del procesador trip_coverage.
La [vista de consumo](../consumo_analitico/README.md) desarrolla sus siguientes pasos.
Conservo el aviso de recorrido largo del encabezado TXT en el resumen, sin quitar esa entrada real del pipeline.


## Alcance del estado actualizado

Las referencias de código prueban la implementación comprometida en Git, no una publicación ni un clic.
Las confirmaciones de desarrollo y las definiciones PBIP locales todavía sin commit se explican en el [estado general](../../project_status.md).
El menú nativo ya funciona; la revisión integral, la actualización completa y Service mantienen sus pendientes propios.
