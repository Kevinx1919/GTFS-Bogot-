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
| Extracción a staging | Pendiente. Extraerá `.txt` para lectura distribuida de Spark. | ZIP Raw. | Archivos de trabajo en `staging_gtfs`. | Archivos esperados y conteos registrados. |
