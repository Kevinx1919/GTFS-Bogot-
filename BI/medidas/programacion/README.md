# Mis medidas de Programación

Organicé nueve medidas numéricas en `Programación\Métricas`.
Organicé nueve medidas HTML en `Programación\Presentación HTML`.
La tabla de inicio es gold_gtfs_trip_timing.

## Núcleo de selección

Obtengo servicios activos por fecha desde silver_gtfs_service_dates.
Aplico service_key a silver_gtfs_trips y trip_key a gold_gtfs_trip_timing mediante TREATAS.
Cada clave conserva versión, SHA-256 e ID fuente.
El filtro de ruta llega mediante las relaciones existentes.

| Medida | Definición |
| --- | --- |
| Viajes activos | Filas de timing asociadas a servicios activos de A. |
| Elegibles | Viajes activos con timing_status=eligible. |
| Excluidos | Viajes activos menos elegibles; no resta plantillas del denominador antes de explicar sus motivos. |
| Primera salida segundos | Menor primera salida entre los viajes elegibles de A. |
| Última llegada segundos | Mayor última llegada entre los viajes elegibles de A. |
| Ventanas activas | Filas de frequencies para las plantillas con servicios activos en A. |
| Elegibles B | El mismo subconjunto elegible aplicado a B. |
| Primera salida B segundos | El mismo extremo de salida aplicado a B. |
| Última llegada B segundos | El mismo extremo de llegada aplicado a B. |

Uso Panorama · Rutas únicamente para comprobar fecha y horizonte conocidos.
Una ruta inactiva en una fecha válida devuelve cero viajes, no una fecha inválida.
Los extremos de una selección sin viajes elegibles permanecen ausentes.
Los porcentajes, intervalos y horas nunca se interpretan como operación observada.

## Presentación

Las medidas HTML incluyen encabezado, indicadores, muestra, calendario, horas, frecuencias, alcance, navegación y fuente.
Muestra HTML se incrusta en Calendario HTML.
Cada barra horaria cuenta la primera salida de un viaje elegible.
La suma de barras concilia con Elegibles, separadamente para A y B.
La precisión se refiere a los extremos publicados, no a puntualidad real.

Los horarios se muestran como HH:MM:SS con horas mayores de 24 intactas.
La muestra contiene hasta seis viajes, con el ID y la precisión en el tooltip.
El panel de frecuencia presenta hasta ocho ventanas y declara cuántas muestra.
El código exact_times permanece en sus tooltips.
No infiero salidas individuales, espera ni capacidad a partir de headway_secs.

[Expresiones numéricas](metricas.dax).
[Presentación HTML](presentacion_html.dax).
[Panel y comprobaciones](../../imagenes/programacion/README.md).
