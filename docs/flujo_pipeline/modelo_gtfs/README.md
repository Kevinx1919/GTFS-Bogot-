# Mi modelo GTFS

Revisé el alcance el 20 de noviembre de 2026. Actualicé el panorama; el ERD conserva su evidencia anterior del 18 de noviembre.

| Vista | Qué explica |
| --- | --- |
| [Modelo Silver](modelo_silver.html) | Diez tablas físicas, 155 columnas y dos catálogos lógicos de IDs. |
| [Panorama GTFS](panorama_gtfs.html) | Entidades publicadas, siguiente contrato y alcance pendiente. |

## Cómo leo las tablas

El modelo incluye agency, routes, stops, calendar, calendar_dates, service_dates, shape_points, trips, frequencies y stop_times.
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
| stop_times | trip_id + stop_sequence |

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

Las diez tablas tienen despliegue funcional confirmado durante el desarrollo.
Service_dates permanece limitada a 2026. Los calendarios fuente conservan sus limitaciones temporales.
Frequencies conserva exact_times ausente y una interpretación efectiva derivada explícita.
Stop_times tiene despliegue funcional confirmado. El planificador 8b ya selecciona listas dinámicas y tiene piloto NO_WORK comprobado.
Las tres entidades opcionales fueron evaluadas; su necesidad depende de preguntas elegidas.
Gold dispone de cuatro tablas publicadas e importadas. Power BI contiene cuatro paneles y navegación nativa confirmada.

Las ramas del panorama agrupan responsabilidades. No representan joins ni el orden del Job.
Las animaciones no representan datos en vivo.

## Fuentes y comprobación

Conservo [el ERD](modelo_silver.erd.json) y [el panorama](panorama_gtfs.tree.json).
El ERD conserva su revisión 6c4490fd2846d8afeb70ee08f02d4680d535b76e. El panorama de alcance fija el código 5c23d4e327fb9d90f407dbfc12678623106e4ad6.
Los [contratos](../../contracts) y el [plan](../../silver_design.md) conservan las reglas completas.

Las dos vistas pasaron los controles automáticos, incluidos los de navegador.
El ERD utiliza el perfil standard por su densidad; conserva las 155 columnas físicas y las seis columnas lógicas.
El [resumen público](verificacion.json) registra hashes, legibilidad medida y avisos de rutas largas.
No hice una nueva revisión de capturas. Los recibos detallados permanecen fuera de Git.
Genero fuera de OneDrive y copio los HTML aprobados sin cambiar sus bytes.

Stop_times muestra sus veinte campos y relaciona visitas con trips y stops mediante la clave completa del snapshot.
Frequencies aporta contexto después de agrupar por viaje; no dibujo una FK directa hacia cada ventana.
Conservo las referencias lógicas de IDs como catálogos no persistidos.
El modelo conserva un aviso de recorrido largo entre calendar y service_ids. Los controles automáticos pasaron.
La clasificación de cobertura está publicada y consumida; varias visitas no demuestran un recorrido completo.
La [vista de consumo](../consumo_analitico/README.md) explica Gold, medidas DAX, páginas y herramientas de asistencia.


## Alcance del estado actualizado

Las referencias de código prueban la implementación comprometida en Git, no una publicación ni un clic.
Las confirmaciones de desarrollo y las definiciones PBIP locales todavía sin commit se explican en el [estado general](../../project_status.md).
El menú nativo ya funciona; la revisión integral, la actualización completa y Service mantienen sus pendientes propios.
