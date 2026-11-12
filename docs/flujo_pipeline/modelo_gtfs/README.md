# Mi modelo GTFS

Actualicé las dos vistas el 12 de noviembre de 2026.

| Vista | Qué explica |
| --- | --- |
| [Modelo Silver](modelo_silver.html) | Nueve tablas físicas, 135 columnas y dos catálogos lógicos de IDs. |
| [Panorama GTFS](panorama_gtfs.html) | Entidades publicadas, siguiente contrato y alcance pendiente. |

## Cómo leo las tablas

El modelo incluye agency, routes, stops, calendar, calendar_dates, service_dates, shape_points, trips y frequencies.
Cada tabla muestra todos sus campos físicos, incluidos procedencia, reglas y ejecución.
Los tipos proceden del código. No infiero tipos por la apariencia de los valores.

Llamo S a la pareja source_feed_version y source_sha256.
Cada clave combina S con sus campos de negocio:

| Tabla | Campos de negocio de la clave |
| --- | --- |
| agency | agency_id |
| routes | route_id |
| stops | stop_id |
| calendar | service_id |
| calendar_dates | service_id + date |
| service_dates | service_id + service_date |
| shape_points | shape_id + shape_pt_sequence |
| trips | trip_id |
| frequencies | trip_id + start_time_seconds |

PK y FK representan claves y referencias comprobadas por el pipeline.
No afirman que Delta tenga restricciones PRIMARY KEY o FOREIGN KEY declaradas.
Las columnas compartidas de S participan en todas las referencias compuestas.
Una fila del dibujo solo puede mostrar un destino para cada columna compartida; las tarjetas explican esa limitación.

## Por qué aparecen dos catálogos lógicos

Service_ids representa servicios distintos de los calendarios disponibles.
Shape_ids representa trazados distintos de shape_points.
Ambos existen como catálogos lógicos del procesamiento; no son dos tablas Silver adicionales.

Trips valida service_id contra los servicios declarados. No exige días activos dentro del horizonte de service_dates.
Trips valida shape_id contra IDs distintos. No se une con cada punto del trazado.
Así evita multiplicar viajes por puntos o excepciones.

Parent_station referencia stops dentro del mismo snapshot.
Conservo sus columnas FK y explico la autorreferencia en una tarjeta, porque Archify no dibuja esa relación consigo misma.
No confundo una estación padre con una parada donde se registra una visita.

## Qué está publicado y qué sigue

Las nueve tablas tienen despliegue funcional confirmado durante el desarrollo.
Service_dates permanece limitada a 2026. Los calendarios fuente conservan sus limitaciones temporales.
Frequencies conserva exact_times ausente y una interpretación efectiva derivada explícita.
El siguiente contrato es stop_times. Tarifas, feed_info, Gold y Power BI continúan pendientes según el plan.

Las ramas del panorama agrupan responsabilidades. No representan joins ni el orden del Job.
Las animaciones no representan datos en vivo.

## Fuentes y comprobación

Conservo [el ERD](modelo_silver.erd.json) y [el panorama](panorama_gtfs.tree.json).
Las referencias fijan el código de 34e3769e1d6eaebca950161f4f47f0bf38f7bc40.
Los [contratos](../../contracts) y el [plan](../../silver_design.md) conservan las reglas completas.

Las dos vistas pasaron los controles automáticos, incluidos los de navegador.
El ERD utiliza el perfil standard por su densidad; conserva las 135 columnas físicas y las seis columnas lógicas.
El [resumen público](verificacion.json) registra hashes, legibilidad medida y avisos de rutas largas.
No hice una nueva revisión de capturas. Los recibos detallados permanecen fuera de Git.
Genero fuera de OneDrive y copio los HTML aprobados sin cambiar sus bytes.
