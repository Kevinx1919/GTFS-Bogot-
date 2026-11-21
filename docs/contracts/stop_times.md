# Mi contrato Silver stop_times_v1

**Fecha:** 12 de noviembre de 2026. **Estado:** implementación local verificada y despliegue funcional confirmado en Databricks.
El [perfil](../stop_times_profile_2025_2026.md) explica la evidencia y sus límites.
El [plan](../stop_times_plan.md) conserva el propósito y las etapas.

## Qué representa una fila

Una fila representa una visita planificada de un viaje a una parada.
La fuente es stop_times.txt y bronze_gtfs_stop_times. La salida es silver_gtfs_stop_times.
Llamo S a source_feed_version + source_sha256.
La clave es S + trip_id + stop_sequence convertida.
Una parada puede aparecer varias veces en un viaje con secuencias distintas.
Acepto saltos y cualquier inicio no negativo de la secuencia.
No renumero las visitas para hacerlas comenzar en cero o uno.

## Campos y tipos

| Campo | Tipo | Regla |
| --- | --- | --- |
| trip_id | string | Obligatorio; referencia trips_v1 dentro de S. |
| stop_id | string | Obligatorio en este alcance; referencia stops_v1 dentro de S. |
| stop_sequence | int | Entero no negativo representable. No exige números consecutivos. |
| arrival_time | string nullable | Hora fuente; obligatoria en extremos y timepoint efectivo 1. |
| departure_time | string nullable | Hora fuente; obligatoria con timepoint efectivo 1 y al inicio de plantillas por frecuencia. |
| timepoint | int nullable | Fuente 0/1; conservo null cuando falta. |
| stop_headsign | string nullable | Texto de esta visita; no lo propago a visitas posteriores. |
| shape_dist_traveled | double nullable | Distancia publicada, finita y no negativa. No asumo unidades. |
| arrival_time_seconds | long nullable | Hora de llegada convertida a segundos del día de servicio. |
| departure_time_seconds | long nullable | Hora de salida convertida a segundos del día de servicio. |
| timepoint_effective | int nullable | Interpretación explícita; distingo ausencia total de ausencia parcial. |
| is_frequency_template | boolean | Indica que frequencies del mismo S referencia este viaje. No describe operación observada. |

Añado ocho columnas de procedencia, reglas y ejecución mediante el escritor existente.
La tabla publicada contiene veinte columnas. La cuarentena conserva la secuencia fuente como texto.
Source_columns distingue un campo ausente del encabezado de un campo publicado sin contenido.
No invento pickup_type, drop_off_type ni otros campos ausentes.
Un encabezado desconocido bloquea la preparación y exige revisar el contrato.
El alcance inicial excluye ubicaciones flexibles, reservas y servicio continuo.

## Horas y timepoint

Acepto H:MM:SS con minutos y segundos entre 00 y 59.
Acepto horas superiores a 24, dentro del rango long.
Por ejemplo, 25:20:00 representa 91.200 segundos del mismo día de servicio.
No convierto estas horas en timestamps UTC ni las ajusto automáticamente al día siguiente.
La zona del servicio procede de agency_timezone. Los timestamps técnicos permanecen en UTC.

Con timepoint=1 exijo llegada y salida.
Con timepoint=0 permito horas intermedias ausentes. No interpolo valores.
Exijo llegada en primera y última visita.
Exijo salida inicial para interpretar plantillas con frequencies.
Una pareja incompleta permitida produce PARTIAL_TIME_PAIR.

Si ningún registro informa timepoint, timepoint_effective vale 1 según GTFS.
Conservo timepoint fuente null. Ese valor derivado no simula contenido publicado.
Si solo algunas filas omiten timepoint, conservo timepoint_effective null y emito TIMEPOINT_UNSPECIFIED.
En esas filas exijo ambas horas para evitar una interpretación ambigua de ausencias.
La ausencia parcial con horas faltantes genera TIMEPOINT_AMBIGUOUS_MISSING_TIMES.
Esta restricción conservadora pertenece al contrato del proyecto.

Rechazo formatos inválidos, desbordamientos y llegada posterior a salida.
Comparo horas conocidas con el máximo previo del viaje, incluso después de visitas sin horas.
Un retroceso produce VISIT_TIME_BACKWARDS. No lo corrijo sumando 24 horas.
Permito horas iguales: no prueban por sí solas un error de operación.

## Calidad, relaciones y cobertura

Compruebo dependencias del mismo S, reglas compatibles, tipos y claves únicas antes de unir.
Trips y stops son obligatorias. Frequencies depende de su publicación declarada en auditoría Bronze.
Fijo versiones Delta de Bronze y dependencias para todo el run.
Una dependencia ausente, ambigua o incompatible impide preparar el resultado.
Una referencia fuente inexistente genera rechazo de esa fila.
Acepto visitas a paradas/plataformas: location_type 0 o ausente.
Rechazo visitas a estaciones padre. No sustituyo una estación por sus hijos.

Agrupo las ventanas de frequencies por viaje antes del join.
Varias ventanas no multiplican las visitas.
Is_frequency_template permite reconocer plantillas; no expando salidas en esta tabla.
Las duraciones relativas requieren comparar horas dentro del mismo viaje.
No cuento la plantilla como una salida adicional al interpretar frequencies.

Consolido solamente copias de negocio idénticas.
Comparo variantes sobre la clave convertida antes de publicar.
Una secuencia 01 y otra 1 generan conflicto cuando representan dos filas fuente diferentes.
Conservo todas las variantes y sus copias en cuarentena.
Rechazo campos obligatorios vacíos, espacios extremos y caracteres de control.
Normalizo opcionales vacíos a null sin completar contenido.
Bronze conserva los originales.

Las distancias descendentes generan SHAPE_DISTANCE_BACKWARDS.
Las distancias repetidas generan SHAPE_DISTANCE_REPEATED como advertencia local.
GTFS pide distancias crecientes; esta tolerancia no equivale a conformidad estricta.
Los perfiles actuales no detectaron igualdades. No relleno distancias de 2025 ni invento sus unidades.

Un viaje con una visita produce TRIP_TOO_FEW_VISITS. Conservo la visita disponible.
Un viaje sin visitas no tiene una fila stop_times para enviar a cuarentena.
Lo cuento en trips_without_visits y en diagnostic_trips_without_visits dentro de las referencias de auditoría.
Ese diagnóstico no aumenta warning_rows, que cuenta únicamente filas fuente con advertencias.
No elimino esos viajes de trips ni afirmo que estén cancelados.
Gold clasificará viajes con cero, una o varias visitas antes de calcular métricas.
Varias visitas no demuestran un recorrido completo.
El [plan de cobertura](../stop_times_plan.md#clasificación-de-cobertura-antes-de-las-métricas-gold) conserva el grano y las reglas propuestas.

## Publicación, costo y pruebas

Mode=validate calcula el resumen sin crear tablas ni auditoría.
Mode=publish utiliza el escritor común: Silver, cuarentena y auditoría.
Cualquier rechazo bloquea el snapshot completo sin sustituir su publicación válida anterior.
ReplaceWhere limita la escritura a S. Un reintento no añade duplicados.
No necesito recargar Bronze.

Filtro hash y proyecto columnas temprano. Compruebo versión y procedencia sin esconder inconsistencias.
Agrupo visitas por clave convertida antes de aplicar ventanas por viaje.
No uso UDF Python ni collect de visitas.
Si el resumen confirma cero rechazos, construyo la cuarentena vacía sin reevaluar las visitas.
Preparé persistencia optativa para reutilizar el resultado validado entre controles y escrituras.
El registro mantiene persist_result=false para conservar compatibilidad con el entorno Serverless 4.
La caché de DataFrames requiere entorno 5 o superior y la preview habilitada.
Solo activaré persist_result después de comprobar ese soporte y medir su costo.
Cuando la activo, libero el recurso en finally, incluso cuando falla la publicación.
Las otras entidades mantienen el comportamiento anterior sin persistencia adicional.
Las pruebas locales usan fixtures pequeñas; todavía no tengo un benchmark de publicación masiva.
Mediré duración y almacenamiento temporal en la primera ejecución real.
No fijo particiones, clustering ni caché en memoria sin esas mediciones.

La décima tarea propuesta es publish_stop_times, después de publish_frequencies.
Reutiliza notebook 10, entorno existente, concurrencia 1 y ambos snapshots.
La plantilla versionada documenta el Job. Ya sincronicé el código y ejecuté stop_times en Databricks.
El notebook 17 conserva consultas de lectura; no constituye una etapa adicional obligatoria.

## Qué significa para negocio y Gold

Puedo analizar el orden de visitas y duraciones planificadas donde existan horas.
Necesito calendarios y tratamiento de frecuencias para contar oferta por fecha.
Una sola visita no permite calcular un recorrido entre paradas.
Los 739 viajes sin visitas de 2026 limitan la cobertura de ese análisis.
No confundo visitas planificadas con buses observados, pasajeros ni viajes operados.
No calculo puntualidad, ocupación ni velocidad operacional desde esta tabla.
Cada futura tabla Gold completará la [ficha de negocio](../silver_design.md#definición-de-negocio-obligatoria-para-cada-futura-tabla-gold).

La [referencia GTFS](https://gtfs.org/documentation/schedule/reference/#stop_timestxt) define clave, campos y semántica.
El proyecto define tipos físicos, políticas de rechazo, advertencias, ejecución e identidad histórica.

La [documentación oficial de caché Serverless](https://docs.databricks.com/aws/en/compute/serverless/dataframe-cache) exige entorno 5 o superior.
No cambié la versión 4 del Job ni sus dependencias. Esta optimización queda desactivada por defecto.

Pasaron 56 pruebas seleccionadas y ocho comprobaciones finales de los últimos ajustes, sin omisiones.
La [guía de ejecución](../silver_execution.md#verificación-local-de-stop_times) conserva tiempos, entorno y alcance.

El [cierre funcional](../silver_execution.md#cierre-de-la-ejecución-de-stop_times) registra la ejecución y sus límites de evidencia.
