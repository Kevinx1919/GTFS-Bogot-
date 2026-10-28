# Runbook de notebooks

## Convención

Los notebooks se comentan por bloque, no línea por línea. Cada bloque documentado indica propósito, entradas, salida, efecto persistente y validación. Los comentarios dentro del código aclaran decisiones no obvias.

## Notebook 02 — `02_raw_static_gtfs_ingestion`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración | Define catálogo, schema, Volume y versiones fuente. | Valores de entorno y URLs oficiales. | Variables de sesión. | Se muestran las versiones configuradas. |
| Descarga | Obtiene el ZIP y registra metadata de la corrida. | URL de la versión seleccionada. | ZIP y metadata en memoria. | HTTP 200, tamaño y SHA-256. |
| Validación | Comprueba estructura GTFS mínima. | Bytes del ZIP. | Resultado en memoria. | ZIP, archivos esenciales y calendario válidos. |
| Raw | Conserva evidencia original e idempotente. | ZIP validado, hash y metadata. | ZIP y manifiesto JSON en `raw_gtfs`. | Ruta por versión/hash y manifest legible. |
| Verificación | Comprueba persistencia. | Rutas Raw creadas. | No escribe. | `path`, `name`, `size`, `modificationTime`. |

Resultado: la versión `2025-10-28` se almacenó con HTTP 200 y hash `07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952`.

## Notebook 03 — `03_bronze_static_gtfs`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Referencia a Raw | Selecciona un snapshot GTFS validado. | Versión y SHA-256 del manifest. | Variables de sesión. | Se lista el directorio del ZIP en Raw. |
| Extracción a staging | Extrae de forma idempotente los `.txt` del ZIP para lectura distribuida. | ZIP Raw. | Archivos y manifiesto de extracción en `staging_gtfs`. | Lista de archivos, tamaño descomprimido y estado de existencia. |
| Lectura de rutas | Lee `routes.txt` conservando sus columnas fuente como texto. | `routes.txt` en Staging. | DataFrame con procedencia técnica. | Esquema visible y 676 rutas en el snapshot actual. |
| Escritura Bronze | Persiste las rutas como tabla Delta administrada. | DataFrame de rutas con hash fuente. | `workspace.gtfs_bogota.bronze_gtfs_routes`. | Conteo del snapshot, `describe detail` e historial Delta. |

## Notebook 04 — `04_bronze_static_gtfs_reference_entities`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración | Selecciona el mismo snapshot validado en Staging. | Versión y SHA-256. | Variables de sesión. | Directorio de Staging visible. |
| Contrato | Declara las columnas GTFS mínimas por entidad. | Definiciones del feed. | Contratos en memoria. | Cada archivo debe contener sus columnas requeridas. |
| Carga Bronze | Lee y escribe `agency`, `stops`, `trips`, calendarios, frecuencias y tarifas. | Archivos `.txt` de Staging. | Tablas `bronze_gtfs_*`. | Conteo por archivo e indicador de idempotencia. |
| Verificación | Inspecciona las paradas persistidas. | `bronze_gtfs_stops`. | No escribe. | Muestra de filas y `describe detail`. |

## Notebook 05 — `05_bronze_static_gtfs_operational_entities`

| Bloque | Propósito | Entrada | Efecto / salida | Validación |
| --- | --- | --- | --- | --- |
| Configuración y contrato | Identifica el snapshot y las columnas mínimas de las entidades grandes. | `shapes.txt` y `stop_times.txt`. | Variables y contratos en memoria. | Archivos y encabezados válidos. |
| Carga de geometrías | Persiste la geometría planificada de recorridos. | `shapes.txt` en Staging. | `bronze_gtfs_shapes`. | Conteo e indicador de idempotencia. |
| Carga de horarios | Persiste la secuencia de paradas por viaje. | `stop_times.txt` en Staging. | `bronze_gtfs_stop_times`. | Conteo, muestra ordenada y `describe detail`. |
