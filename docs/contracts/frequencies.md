# Mi contrato Silver frequencies_v1

**Fecha:** 12 de noviembre de 2026. **Estado:** implementación local comprobada. Pasaron 42 pruebas seleccionadas sin omisiones.
Implementé el procesador y añadí la novena tarea a la plantilla. El despliegue funcional quedó confirmado el 12 de noviembre de 2026.
El [perfil](../frequencies_profile_2025_2026.md) conserva las comprobaciones y sus límites.

## Qué representa una fila

Una fila define una ventana de frecuencia para un viaje plantilla.
La ventana indica inicio, fin e intervalo entre salidas desde la primera parada.
Trip_id referencia trips del mismo snapshot. No identifica un vehículo observado.

La fuente es frequencies.txt y bronze_gtfs_frequencies. La salida es silver_gtfs_frequencies.
Llamo S a la pareja source_feed_version y source_sha256.
La clave validada es S + trip_id + start_time_seconds.
La conversión reconoce la misma hora escrita como 4:30:00 o 04:30:00.

## Campos y tipos implementados

| Campo | Tipo | Decisión |
| --- | --- | --- |
| trip_id | string | Obligatorio. Conservo su identidad y valido la referencia a trips_v1 dentro de S. |
| start_time | string | Obligatorio. Conservo la hora fuente y valido su formato. |
| end_time | string | Obligatorio. Conservo la hora fuente y valido su formato. |
| headway_secs | int | Obligatorio. Acepto solamente enteros positivos representables. Su unidad es segundos. |
| exact_times | int nullable | Opcional. Admito 0 o 1 cuando existe contenido válido. Conservo null cuando falta. |
| start_time_seconds | long | Derivado. Segundos desde el inicio del día de servicio. |
| end_time_seconds | long | Derivado. Segundos desde el inicio del día de servicio. |
| exact_times_effective | int | Derivado. Uso exact_times informado o el valor predeterminado 0 definido por GTFS. |

La [referencia GTFS](https://gtfs.org/documentation/schedule/reference/#frequenciestxt) define campos, unidades, clave y significado de exact_times.
El proyecto define tipos físicos, procedencia, rechazos y protección del histórico.

## Horas de servicio

Acepto H:MM:SS y HH:MM:SS. También admito horas superiores a 24 dentro del rango long.
Minutos y segundos deben permanecer entre 00 y 59.
No uso un tipo TIME limitado a 24 horas.
Por ejemplo, 25:10:00 equivale a 90.600 segundos del mismo día de servicio.
No cambio 01:00:00 por 25:00:00 para corregir una ventana invertida.
Exijo end_time_seconds mayor que start_time_seconds.
Los errores de formato o desbordamiento producen rechazo.

Estas horas describen servicio local. No representan timestamps UTC de ejecuciones.
Conservo los timestamps técnicos en UTC.

## Ausencias y significado de exact_times

Los dos archivos actuales no publican exact_times.
Conservo esa ausencia mediante null y source_columns.
El campo derivado exact_times_effective hace explícita la interpretación predeterminada del estándar.
No presento ese cero derivado como un valor publicado por la fuente.

El valor efectivo 0 describe servicio por frecuencia. No garantiza salidas exactas cada cierto número de segundos.
El valor 1 describe horarios regulares exactos. Su publicación requiere comprobar también las condiciones específicas del estándar.
Para exact_times=1 exijo un fin estrictamente posterior a la última salida y anterior al siguiente intervalo.
Compruebo que la duración positiva no sea un múltiplo exacto de headway_secs.
Por ejemplo, 04:30:00–05:30:01 admite intervalo 60. El fin 05:30:00 requiere revisión bajo esa condición estricta.
No cambio automáticamente ese límite.
Todas las ventanas del mismo viaje deben compartir exact_times_effective.
La [guía de validación](https://developers.google.com/transit/gtfs/guides/static-errors-warnings) también documenta ese control de coherencia.
No expando salidas desde esta primera tabla Silver.

## Calidad y relaciones

Exijo los cuatro campos obligatorios del encabezado. Un campo desconocido requiere revisar el contrato.
Un archivo opcional ausente no genera registros inventados.
Rechazo campos obligatorios sin contenido, IDs con espacios extremos y caracteres de control.
No corrijo unidades ni multiplico intervalos por 60.

Valido trips Silver dentro de S antes del join. Exijo claves únicas y trips_v1.
Una dependencia ausente, ambigua o incompatible bloquea la preparación.
Una referencia trip_id sin resolver genera rechazo de la fila.
El join debe conservar el conteo de ventanas.
Routes y calendarios aportan contexto mediante trips. No necesito unirlos otra vez para tipar frequencies.
Stop_times aportará tiempos relativos entre paradas cuando complete su contrato.

Consolido solamente copias de negocio idénticas.
Una misma clave con atributos diferentes conserva sus variantes en cuarentena.
También detecto colisiones después de convertir la hora de inicio.
No elijo una variante mediante orden arbitrario.

Compruebo superposiciones dentro de S + trip_id, después de consolidar copias.
Una ventana puede comenzar cuando termina la anterior.
Marco todas las filas involucradas en una superposición.
Las pruebas incluirán ventanas contenidas para evitar errores de una comparación con una sola fila anterior.
No aplico esa regla automáticamente entre viajes distintos que comparten ruta.

Los errores conservan originales y motivos en cuarentena. Un rechazo bloquea la publicación del snapshot completo.
Fijo versiones Delta de Bronze y trips. La auditoría conserva esas referencias.
Reutilizo notebook 10 y el escritor común. La reejecución protege los demás snapshots.

## Límites para Gold y Power BI

Una ventana no cuenta vehículos, pasajeros ni viajes realmente operados.
Un intervalo pequeño no demuestra un error de unidades ni una mejora operativa.
Compararé frecuencias solo después de comprobar modo, calendario y alcance equivalente.
No convertiré el crecimiento de filas GTFS en crecimiento de la red.

Los nombres de trip_id no determinan días festivos.
Usaré service_id, calendar_dates y service_dates para fechas concretas.
La limitación temporal del snapshot 2025 permanece visible.
La futura expansión de horarios evitará contar la plantilla como una salida adicional.

## Comprobaciones antes de publicar

Preparé fixtures de horas extendidas, formatos, desbordamientos, valores ausentes, claves y referencias.
Preparé pruebas de copias, conflictos, colisiones, ventanas contiguas y superposiciones contenidas.
Preparé pruebas de exact_times ausente, vacío, 0, 1 e inválido con sus reglas explícitas.
La integración Delta comprueba validate sin escritura, publicación, reintento, cuarentena e histórico.
La [guía de ejecución](../silver_execution.md#despliegue-de-frequencies_v1) conserva el resultado de las pruebas actuales.


## Advertencias y alcance operativo

HEADWAY_LONGER_THAN_WINDOW conserva la fila cuando el intervalo supera la duración de la ventana.
La advertencia requiere interpretación. No modifica unidades ni crea salidas.
No aplico un umbral genérico de frecuencia mínima pensado para buses al transporte por cable.
Los snapshots actuales no presentaron esa condición en el perfil.

El procesador usa Spark nativo. Solo recupera un resumen agregado de trips y otro resumen de validación.
No trae ventanas ni viajes al driver. Los registros de negocio permanecen distribuidos.
La detección de superposiciones agrupa inicios para evitar falsas alarmas por copias.
Usa máximo final previo y siguiente inicio para marcar ambos extremos de cada conflicto.
Una clave conflictiva permanece rechazada; esa agrupación no elige una variante para publicar.

Mantengo ocho campos de negocio y ocho columnas técnicas en la salida publicada.
El escritor utiliza trip_id + start_time_seconds dentro del snapshot.
Los rechazos conservan esa clave convertida, los originales completos y sus motivos.
Un inicio inválido puede quedar null en cuarentena; el original conserva su texto.
