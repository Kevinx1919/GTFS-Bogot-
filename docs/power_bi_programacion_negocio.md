# Qué responde Programación y cómo lo calculo

**Actualización del cierre — 20 de noviembre de 2026:** navegación nativa confirmada; cuatro paneles y cuatro Gold disponibles. [Estado vigente](project_status.md) y [menú y componentes](power_bi_navigation_images.md).

**Estado:** diseño revisado y aprobado; implementación guardada. Renderizado dentro de Desktop pendiente.

Construí este panel para revisar días y horas de la oferta publicada.
La pregunta es: **¿qué programación declara la selección y qué viajes sostienen sus horarios?**

| Pregunta | Qué muestro | Cómo lo calculo |
| --- | --- | --- |
| ¿Qué días tienen programación? | Calendario mensual de A. | Consulto cantidades de route_service_day por día; separo viajes sin frecuencias y plantillas. |
| ¿Qué horarios publica la selección? | Primera salida y última llegada para A y B. | Selecciono viajes activos y tomo extremos únicamente de timing_status=eligible. |
| ¿Cuándo se concentran las primeras salidas? | Conteos por hora para A y B. | Cada viaje elegible aporta una primera salida; la suma concilia con elegibles. |
| ¿Qué ejemplos explican esos horarios? | Seis primeros viajes elegibles de A. | Ordeno por primera salida y clave, preservando ID y precisión en el tooltip. |
| ¿Qué intervalos publican las plantillas? | Ventanas activas de A e intervalo en segundos. | Relaciono sus trip_key con los servicios activos y leo frequencies sin expandir salidas. |
| ¿Qué queda fuera del cálculo horario? | Denominador, exclusiones y precisión. | Particiono viajes activos por timing_status y elegibles por endpoint_time_precision. |

## Cómo una fecha llega a los horarios

Primero elijo A y B, componente y ruta.
Service_dates indica qué service_key están activos en cada fecha.
Service_id representa un patrón de calendario, no un bus.
Aplico esos servicios a trips mediante TREATAS.
Después aplico sus trip_key a trip_timing y frequencies.
Cada clave incluye versión, SHA-256 e ID de la misma fuente.

La dimensión de fechas no convierte automáticamente un catálogo de viajes en programación diaria.
Por eso realizo esa selección explícita y no añado relaciones bidireccionales.
Para B retiro únicamente la fecha A y conservo componente y ruta.

## Cómo leo las horas

Mantengo horas de servicio y segundos originales.
25:09:00 equivale a la 01:09 del día siguiente del servicio.
No reduzco las horas con módulo 24 ni las convierto en timestamps UTC.
La menor salida y la mayor llegada pueden pertenecer a viajes distintos.
No representan un recorrido de esa duración ni prueban continuidad entre ambos extremos.

Exacto según publicación describe un código GTFS; no demuestra puntualidad.
Aproximado publicado tampoco significa automáticamente que la fila sea inválida.
Las plantillas se analizan mediante ventanas, no como salidas individuales elegibles.
Un intervalo de 16 segundos permanece en segundos; no lo convierto en 16 minutos ni en espera observada.

## Ejemplo entre ambos paneles

El domingo 22 de noviembre de 2026 tiene 40.229 viajes activos.
Son 40.210 elegibles, 17 sin visitas y dos plantillas.
Panorama cuenta 40.227 viajes sin frecuencias, incluidos los 17 sin visitas.
Programación usa 40.210 para su perfil y explica las 19 exclusiones.

Esto es como comparar la lista completa del horario con las filas que permiten leer ambos extremos.
Las filas restantes siguen presentes y conservan su motivo de exclusión.

L81, ID 13780, tiene cero viajes en A y 293 elegibles en B.
En A muestro cero viajes y horas ausentes.
La ausencia de una hora no se convierte en medianoche.

## Acción siguiente

Elijo una ruta para revisar un patrón o un ejemplo concreto.
Después continúo en Red publicada para explorar sus ubicaciones del catálogo.
La red no garantiza visitas a cada ubicación en una fecha concreta.

[Abro Programación](../BI/imagenes/programacion/programacion_preview.html).
[Consulto las medidas](../BI/medidas/programacion/README.md).
