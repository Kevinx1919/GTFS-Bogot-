# Estrategia de fuentes y alcance analítico

## Objetivo

Quiero construir un lakehouse reproducible que relacione la **oferta planificada** de TransMilenio con la **demanda observada** publicada por la entidad. Antes de calcular una métrica, necesito entender qué representa cada fuente y hasta dónde me permite llegar.

## Fuentes priorizadas

Priorizo las fuentes que me permiten avanzar sin depender de que GTFS-Realtime esté disponible. El orden también me ayuda a aprender una integración a la vez.

| Prioridad | Fuente | Formato esperado | Pregunta que habilita | Frecuencia de ingesta |
| --- | --- | --- | --- | --- |
| 1 | GTFS estático versionado | ZIP con archivos GTFS | ¿Cómo cambió la oferta planificada? | Al detectar nueva versión |
| 2 | Validaciones mensuales | XLSX u otro recurso publicado | ¿Cómo evoluciona la demanda por mes y franja? | Mensual / carga histórica inicial |
| 3 | Salidas diarias del troncal | ZIP | ¿Dónde y cuándo se concentran flujos de salida? | Diario |
| 4 | Validaciones diarias | CSV/ZIP | ¿Qué variaciones diarias aparecen en accesos? | Diario |
| 5 | GTFS-Realtime | Protocol Buffers | ¿Qué ocurre con la flota observada? | Cada 5 minutos, cuando el proveedor se recupere |

## Contrato de cada fuente

Antes de llevar una fuente a Bronze, reviso y dejo registrado lo siguiente:

- URL o identificador oficial, responsable y condiciones de uso.
- Formato, tamaño aproximado, hash SHA-256 y fecha/hora UTC de captura.
- Frecuencia declarada y latencia observada.
- Esquema real: columnas, tipos, grano y claves candidatas.
- Reglas de calidad: campos requeridos, valores nulos, duplicados y rangos.
- Método de idempotencia y criterio para detectar una nueva versión.

## Workflow de GTFS estático: descubrimiento, selección e ingesta

Para automatizar el flujo usaré **Databricks Workflows**. n8n no ejecutará
PySpark ni escribirá en el lakehouse; podrá notificar el resultado de una
ejecución ya finalizada.

```text
Catálogo ArcGIS oficial
        ↓
06_discover_static_gtfs_catalog
        ↓
control_gtfs_static_catalog + auditoría append-only
        ↓
plan de ingesta determinista
        ↓
02 Raw → 03 Staging → 04/05 Bronze
        ↓
controles de calidad y alerta
```

El descubrimiento consulta el grupo oficial de GTFS alojado en ArcGIS Online y
registra la fecha publicada (`feed_version`), URL candidata, identificador del
ítem ArcGIS, fechas de portal y una huella de metadata. No descarga archivos ni
selecciona una URL no resuelta. El portal GIS operativo de TransMilenio expone
otros recursos y no contiene este grupo; usar el host incorrecto devuelve 400.

Estoy diseñando el Job para estos tres modos de selección:

| Modo | Propósito | Criterio |
| --- | --- | --- |
| `latest_uningested` | Operación incremental. | Versión directa más reciente que aún no tiene registros Bronze. |
| `backfill_range` | Carga histórica inicial. | Versiones publicadas dentro de un rango de fechas explícito. |
| `explicit_version` | Reproceso o análisis reproducible. | Una fecha de versión exacta indicada por el operador. |

La fecha de versión pertenece al proveedor y se extrae del catálogo. El momento
de descubrimiento y de ingesta se guarda aparte en UTC. Antes de descargar quiero que el
Workflow guarde el plan de ejecución; así podré reintentar las mismas versiones
aunque aparezca una publicación más reciente. La persistencia de ese plan sigue
pendiente de implementar.

### Contrato de parámetros entre notebooks

| Notebook | Parámetros de entrada | Salida que habilita |
| --- | --- | --- |
| `06_discover_static_gtfs_catalog` | `selection_mode`, `explicit_version`, `start_date`, `end_date` | Plan de versiones pendientes. |
| `02_raw_static_gtfs_ingestion` | `feed_version` | Resuelve URL desde control, conserva Raw y publica `snapshot_sha256`. |
| `03_bronze_static_gtfs` | `feed_version`, `snapshot_sha256` | ZIP expandido en Staging y rutas Bronze. |
| `04_bronze_static_gtfs_reference_entities` | `feed_version`, `snapshot_sha256` | Entidades de referencia Bronze. |
| `05_bronze_static_gtfs_operational_entities` | `feed_version`, `snapshot_sha256` | Geometrías y horarios Bronze. |

`02` no acepta una URL suministrada por el operador: la resuelve desde la tabla
de control. Esta restricción evita descargar un origen no descubierto ni perder
la relación entre la versión publicada, el ítem ArcGIS y el ZIP conservado.

### Evolución del contrato GTFS

Las versiones GTFS pueden añadir u omitir archivos opcionales. La capa Raw y
Staging preservan todos los `.txt` publicados; Bronze carga los disponibles y
registra cuáles opcionales faltan. Un archivo requerido ausente detiene la
ingesta, mientras que la ausencia de uno opcional no se convierte en filas
ficticias.

En la comparación inicial entre 2025-10-28 y 2026-09-29, `feed_info.txt`
apareció y `fare_rules.txt` dejó de estar publicado. Ambos cambios se tratan
como evolución de contrato: el primero crea `bronze_gtfs_feed_info` y el
segundo queda registrado como archivo opcional ausente.

La versión 2026 también agregó `agency_fare_url` en agencias,
`wheelchair_boarding` en paradas y `trip_headsign` en viajes. Bronze permite
estas nuevas columnas mediante `mergeSchema` solamente en la escritura
auditada de cada tabla; no se habilita evolución automática global de Delta.

Para analizar cambios usaré tres referencias: versión actual (última
validada), versión anterior válida y versión histórica seleccionada por período.
No se interpretan estas comparaciones como demanda ni operación observada.

## Relación entre oferta y demanda

Lo pienso como tener un horario de buses y un conteo de entradas a una estación: el primero me habla de lo planificado y el segundo de accesos registrados. Para relacionarlos necesito comprobar que fecha, lugar y franja realmente coincidan.

Solo avanzaré con el cruce cuando pueda demostrar una correspondencia válida entre las fuentes:

```text
fecha + franja + estación/parada o zona + componente
```

Si las identificaciones no coinciden, necesitaré una tabla de mapeo explícita, con fuente y fecha de vigencia. No usaré nombres parecidos como prueba suficiente para unir datos en Gold.

La métrica resultante se llamará **proxy de presión demanda-oferta planificada**. No representa ocupación por vehículo, puntualidad, tiempos de espera ni origen-destino.

## Autenticación

Los portales ArcGIS pueden exponer un servicio de tokens y, a la vez, publicar recursos anónimos. Por eso evalúo la necesidad de token para cada recurso:

- HTTP 200 anónimo: usar el recurso público sin token.
- HTTP 401/403 o metadato privado: detener integración y evaluar autorización.
- Si se autoriza un token: almacenarlo exclusivamente en Databricks Secrets; nunca en código, manifiestos, logs o Git.

## Estado de GTFS-Realtime

Los endpoints oficiales de posiciones, alertas y actualizaciones de viaje devolvieron HTTP 500 durante la prueba inicial. Por lo tanto:

- La capa raw no almacena la respuesta fallida como feed.
- La auditoría registra el fallo, reintentos y último snapshot exitoso.
- Ninguna métrica traduce el fallo en “cero vehículos”.
- La fuente se reevalúa periódicamente sin bloquear las fuentes estáticas y de demanda.

## Referencias oficiales

- [Portal de Datos Abiertos de TransMilenio](https://datosabiertos-transmilenio.hub.arcgis.com/)
- [Grupo de datos GTFS de TransMilenio](https://datosabiertos-transmilenio.hub.arcgis.com/search?groupIds=ca6e3d0acf57461d91228659c1b0d2dd)
- [Datos Abiertos Bogotá: TransMilenio](https://datosabiertos.bogota.gov.co/organization/transmilenio?groups=transporte)
- [Endpoints GTFS-Realtime](https://gis.transmilenio.gov.co/gtfs/)
