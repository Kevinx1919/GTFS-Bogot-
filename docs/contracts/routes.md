# Mi contrato Silver de routes — routes_v1

## Qué representa una fila

Conservo una ruta publicada en un snapshot GTFS. Mi clave es `(source_feed_version, source_sha256, route_id)`. Relaciono su `agency_id` con Silver agency usando la misma versión y hash; un número de agencia de 2025 no representa automáticamente lo mismo en 2026.

Como ejemplo, es como guardar dos ediciones de un catálogo: el código y el nombre pertenecen a su edición. No los sustituyo con los de otra fecha. Tampoco interpreto las diferencias de conteo como altas o bajas reales de servicios.

## Tipos y obligatoriedad

| Campo | Tipo Silver | Mi regla |
| --- | --- | --- |
| route_id | string | Requerido, con contenido y sin espacios extremos. Único dentro del snapshot. |
| agency_id | string | Requerido en este contrato para feeds con varias agencias; debe existir en agency_v1 del mismo snapshot. |
| route_short_name | string | Debe tener contenido si route_long_name no lo tiene. Conservo ceros y letras. |
| route_long_name | string | Debe tener contenido si route_short_name no lo tiene. Un null aislado puede ser válido. |
| route_desc | string | Opcional. Si falta del encabezado, conservo null y su ausencia en source_columns. |
| route_type | int | Requerido. Acepto dígitos casteables sin desbordamiento y valores GTFS 0–7, 11 y 12. |
| route_url | string | Opcional. Comprobación básica HTTP(S), autoridad con contenido y sin espacios; no verifico DNS, puertos ni disponibilidad web. |
| route_color | string | Opcional. Seis caracteres hexadecimales, sin #; acepto mayúsculas y minúsculas y conservo el formato publicado. |
| route_text_color | string | Opcional. La misma regla de color. |
| route_sort_order | int | Opcional. Entero no negativo hasta 2.147.483.647; valores fuera de rango requieren revisar el contrato. |

No hay campos double en esta entidad: los números existentes son categorías u orden, no medidas continuas. La conversión se hace en Spark, después de identificar errores sobre los strings de Bronze. `try_cast` no oculta fallos: un valor presente que no convierte se rechaza con su código.

Los opcionales ausentes, nulos, vacíos o solo espacios quedan null. No invento colores por defecto ni relleno nombres. Los textos con contenido conservan sus espacios extremos con advertencia; IDs con esos espacios se rechazan. Rechazo caracteres de control incluso en campos opcionales. Una descripción igual a un nombre produce advertencia. No calculo contraste visual ni afirmo validar todas las recomendaciones GTFS.

Esta versión cubre las columnas observadas y route_url/route_sort_order. Si aparecen continuous_pickup, continuous_drop_off, network_id, cemv_support u otras columnas nuevas, bloqueo por evolución de esquema hasta revisar sus reglas y dependencias. No apruebo silenciosamente condiciones que dependen de otras tablas. Los códigos route_type extendidos requieren una ampliación explícita del contrato.

## Duplicados y procedencia

Comparo todas las columnas de negocio publicadas antes de convertirlas. Copias exactamente iguales se consolidan; elijo el timestamp Bronze más antiguo entre las copias válidas. Si un route_id tiene atributos distintos, rechazo todas sus filas, incluidas sus copias. No agrupo por nombre corto: diferentes rutas pueden compartir etiquetas.

Exijo versión, hash, ruta de archivo y timestamp Bronze válidos. Leo por hash para detectar una fila con versión o ruta equivocadas en vez de ocultarla. Las versiones Delta de Bronze y agency quedan fijadas al inicio. Solo traigo al proceso Python filas agregadas de métricas; las rutas, cruces, conversiones y duplicados se procesan en Spark.

## Dependencia y publicación

Antes de validar necesito agency_v1 publicado para ese mismo snapshot, con IDs válidos y únicos. Si falta, el pipeline falla con un mensaje accionable antes de escribir; el Job conserva ese error. Si encuentro rutas huérfanas, registro AGENCY_ID_NOT_FOUND como rechazo.

Reutilizo el escritor de agency: `silver_gtfs_routes`, `quarantine_gtfs_routes` y `audit_gtfs_silver_runs`. Un rechazo bloquea la publicación completa del snapshot; no publico un subconjunto sin avisar. La cuarentena conserva la fila original y sus motivos con input_copies. Las advertencias se resumen en auditoría y son consultables en el resultado de validación; no creo una nueva tabla de advertencias.

La reconciliación es entrada = candidatos + rechazados + copias consolidadas. La reejecución sustituye solo versión y hash mediante replaceWhere, verifica la salida y puede comprobar que las otras versiones sigan iguales. Mantengo el mismo esquema de auditoría y el contrato publicado de agency; no necesito migrar esas tablas para añadir routes.

## Referencias y alcance

Definí las reglas con la [referencia oficial GTFS](https://gtfs.org/documentation/schedule/reference/#routestxt) y el [perfil real de ambos snapshots](../routes_profile_2025_2026.md). La preparación local y sus pruebas no sustituyen ejecutar este código en el workspace. El contrato no valida continuidad de rutas entre años ni operación real.
