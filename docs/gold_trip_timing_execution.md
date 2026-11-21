# Mi ejecución de extremos horarios Gold

**Actualización: 20 de noviembre de 2026.**

## Publicación confirmada para 2026

La ejecución d39bc6b9-9cf2-478c-9830-0f72cd905b2a terminó SUCCEEDED, persisted=true y reconciled=true.
Conservé 181.060 viajes únicos: 180.246 elegibles, 739 sin visitas, 61 con una visita y 14 plantillas.
El resumen registró cero extremos ausentes y cero extremos invertidos.
La tabla ya está importada en Power BI; Programación y Revisión utilizan su clasificación.

## Procedimiento y comprobaciones previas

Los apartados siguientes conservan el procedimiento y las pruebas locales anteriores a esta publicación.

**Estado:** publicado en Workspace para 2026 e importado en el modelo local Power BI.
La [ficha](contracts/trip_timing.md) fija el significado de cada campo.

## Pasos

1. Sincronizo el repositorio completo y abro databricks/notebooks/gold/24_publish_gtfs_trip_timing.
2. Uso la misma raíz repo_root que en notebooks 22 y 23.
3. Configuro catalog=workspace, schema=gtfs_bogota, feed_version=2026-09-29.
4. Uso snapshot_sha256=08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097.
5. Mantengo mode=validate y ejecuto Run all.
6. Compruebo reconciled=true y candidate_rows=distinct_trips.
7. Reviso las seis categorías y confirmo que su suma coincide con los viajes del catálogo.
8. Después selecciono publish y repito Run all para publicar.

Si las fuentes actuales no cambiaron, espero 181.060 viajes únicos, 9.408.893 visitas y catorce ventanas.
No fijé la cantidad real de viajes elegibles antes de ejecutar este publicador.
El resumen conserva cero visitas, una visita, plantillas, extremos ausentes, extremos invertidos y elegibles.
Las dos primeras categorías no deben perderse al unir horarios.

Validate no escribe. Publish debe terminar SUCCEEDED con persisted=true y cierre auditado.
No necesito volver a publicar las Gold anteriores para ejecutar este notebook.
Las comprobaciones locales no sustituyen la validación Delta en Databricks.

## Cómo interpretar el resultado

25:00:00 y 26:05:00 se conservan como 90.000 y 93.900 segundos.
Su diferencia publicada es 3.900 segundos, si el viaje cumple los requisitos del contrato.
No convierto esas horas a 01:00:00 y 02:05:00 para hacer la resta.
Si falta la salida de la primera visita, no tomo la salida de otra visita como sustituto.
Si una plantilla tiene dos ventanas, sigue siendo una fila, con frequency_window_count=2.

## Power BI, después de publicar

Importaré los diecisiete campos de negocio y excluiré los tres técnicos de publicación.
Crearé trip_key con la misma definición de identidad que usa trips.
Relacionaré trips→trip_timing con dirección única y sin caminos adicionales desde ruta o fecha.
Las medidas conservarán solo los casos elegibles cuando calculen intervalos publicados.
Mostraré precisión y exclusiones; las ventanas por frecuencia tendrán un visual separado.
El hecho todavía no es programación diaria: la fecha de servicio requiere aplicar los servicios activos explícitamente.


Las [consultas posteriores](../databricks/sql/gold/trip_timing_checks.sql) permiten revisar categorías y recuperar un viaje concreto.


## Verificación local

Pasaron diecisiete pruebas en 55,960 segundos con Spark 4.0.1 dentro del Docker offline existente.
El repositorio se montó en solo lectura y los datos sintéticos quedaron fuera de OneDrive.
Los tests cubren secuencias no consecutivas, horas mayores de 24, ausencia de extremos, precisión y plantillas con varias ventanas.
También verifican categorías excluyentes, viajes preservados, claves duplicadas, referencias huérfanas, horas negativas y ámbito histórico.
Las comprobaciones de metadata prueban versiones fijadas, deriva y bloqueo de una publicación fallida previa.
Validate no llamó al escritor ni a la auditoría; la publicación con dobles comprobó el ámbito y el cierre exitoso.
Las transformaciones usan Spark real; el IO Delta se sustituye por dobles.
No ejecuté una integración Delta nativa nueva ni publiqué esta entidad en Workspace.
Comprobé sintaxis Python, dos bloques del notebook sin resultados guardados, diecisiete campos de consumo y enlaces.
