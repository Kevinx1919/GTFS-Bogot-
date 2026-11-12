# Mi perfil de trips de 2025 y 2026

**Fecha:** 11 de noviembre de 2026. **Estado:** perfil de lectura completado. El contrato ya tiene implementación local. Las 37 pruebas seleccionadas pasaron sin omisiones. La primera publicación Silver sigue pendiente.

## Alcance y evidencia

Después del cierre 9735d2a consulté trips Bronze y sus referencias. Conservé diez consultas definitivas en el [notebook 15](../databricks/notebooks/silver/15_profile_gtfs_trips.ipynb). Recuperé 112 filas estructuradas sin truncamiento: 77 + 12 + 2 + 10 + 2 + 2 + 2 + 2 + 2 + 1. Amplié la consulta de encabezados y conservé solo su versión final.

Usé estos snapshots:

| Versión | SHA-256 |
| --- | --- |
| 2025-10-28 | 07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952 |
| 2026-09-29 | 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097 |

Las consultas solo leen. No modifiqué tablas, archivos, Job ni Archify. El notebook todavía no tiene una ejecución completa documentada como cuaderno. Las consultas no fijan versiones Delta ni una transacción conjunta.

## Qué representa una fila

Una fila identifica un viaje del GTFS. route_id identifica su ruta. service_id identifica su calendario. shape_id identifica su trazado. trip_id identifica el viaje dentro del snapshot.

Un viaje puede servir como plantilla para frequencies. No cuento cada fila como un bus físico ni como un viaje efectivamente realizado. Para fechas concretas necesitaré el calendario activo. Para paradas y horas necesitaré stop_times.

## Conteos observados

| Medida | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| Filas de trips | 107.162 | 181.060 |
| trip_id distintos | 107.162 | 181.060 |
| route_id referenciados | 672 | 1.045 |
| service_id referenciados | 3 | 3 |
| shape_id referenciados | 672 | 1.045 |
| Grupos ruta + servicio + trazado | 1.641 | 2.427 |
| Grupos con varios trip_id | 1.636 | 2.407 |
| Máximo de viajes en un grupo | 290 | 348 |
| Viajes referenciados por frequencies | 2 | 14 |

El mínimo de viajes por ruta es uno en ambos snapshots. El máximo es 640 / 709. Encontré 512 / 772 rutas con varios servicios. No encontré rutas con varios trazados en estos datos. Esa observación no impone una relación uno a uno para futuros feeds.

Los grupos con varios trip_id son esperables. Dos viajes pueden compartir ruta, calendario y trazado. No eliminaré esas filas por compartir esos atributos. La clave propuesta conserva trip_id dentro de versión/hash.

No interpreto la diferencia de filas entre años como crecimiento de oferta. Las fechas y la interpretación de frecuencias todavía limitan esa comparación.

## Completitud y procedencia

Los cuatro identificadores publicados están completos en ambos snapshots. No encontré nulos, vacíos, solo espacios, espacios extremos ni caracteres de control en esos identificadores.

Los controles tampoco encontraron versiones incorrectas, rutas Staging incoherentes ni timestamps de carga ausentes. No encontré copias idénticas, trip_id repetidos ni atributos conflictivos para una misma clave. Los IDs siguen siendo string; no representan cantidades.

## Trip_headsign: dos ausencias diferentes

| Snapshot | Campo publicado | Resultado |
| --- | --- | --- |
| 2025 | No | El archivo no define trip_headsign. Sus métricas quedan como no aplicables. |
| 2026 | Sí | Las 181.060 filas Bronze contienen null. No aparece texto no blanco. |

Comparé el TXT Staging de 2026 con read_files. El lector CSV también devuelve 181.060 filas y 181.060 nulls en trip_headsign. No encuentra texto no blanco. La comparación coincide con Bronze para este campo bajo las mismas reglas de lectura.

Esto no distingue todas las representaciones léxicas originales de un vacío. No demuestra igualdad completa de todas las columnas del archivo. Sí descarta contenido no blanco perdido de trip_headsign bajo esta comparación.

Propongo conservar null y la evidencia en source_columns. No copiaré route_long_name para fabricar trip_headsign. Stop_times publica stop_headsign en 2026, pero todavía no revisé su contenido. Ese campo tiene su propia semántica y no completa automáticamente trips.

## Referencias sin multiplicar filas

Usé routes Silver, servicios de calendar/calendar_dates Silver y IDs distintos de shape_points Silver. No encontré referencias sin resolver. Los joins conservaron exactamente 107.162 / 181.060 filas.

No relacioné cada viaje con todos los puntos del trazado. Ese join multiplicaría filas. Tampoco usé service_dates para decidir si existe un servicio. Su horizonte acotado no define el catálogo de IDs.

Calendar contiene siete servicios por snapshot, pero trips usa tres. Un servicio sin viajes referenciados permanece en su catálogo. Las excepciones de 2023 del snapshot 2025 siguen limitando el análisis temporal. La resolución de un ID no certifica un calendario festivo correcto.

## Dependencia shape_points ya consultada en Silver

| Snapshot | Puntos Silver | Claves distintas | Trazados | Distancias informadas | Regla incorrecta |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2025 | 909.878 | 909.878 | 676 | 0 | 0 |
| 2026 | 926.501 | 926.501 | 1.045 | 0 | 0 |

Estos conteos proceden de una consulta actual de Silver. Son posteriores a la confirmación funcional del cierre. Todas las filas consultadas tienen shape_points_v1. No infiero nuevos conteos de advertencias ni un reintento a partir de esta consulta.

## Condiciones y frecuencias

Los encabezados de routes y stop_times no publican continuous_pickup ni continuous_drop_off en estos snapshots. El requisito condicional de shape_id no se activa por esos campos en el feed consultado. Todos los viajes actuales sí publican un identificador de trazado válido.

Frequencies contiene 2 / 14 filas y 2 / 14 trip_id distintos. Todas sus referencias resuelven. La fuente no publica exact_times. Revisaré su interpretación al implementar frequencies. No calculé salidas, intervalos válidos ni horarios expandidos.

## Próximas decisiones

El [contrato](contracts/trips.md) mantiene cinco campos de negocio string. Los tres IDs principales son obligatorios. shape_id requiere validación condicional. trip_headsign conserva sus ausencias. Las fuentes curadas deberán pertenecer al mismo snapshot.

Después de revisar el significado implementé las reglas y sus pruebas. Reutilicé notebook 10. El registro habilita trips y la plantilla añade su tarea. La primera publicación en Databricks sigue pendiente. El planificador de snapshots continúa pendiente 8b.

La [referencia GTFS](https://gtfs.org/documentation/schedule/reference/#tripstxt) define los campos. El proyecto define identidad histórica, controles de calidad y política de publicación.
