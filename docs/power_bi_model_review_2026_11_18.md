# Mi revisión del modelo Power BI y del plan Gold

**Fecha:** 18 de noviembre de 2026.
**Método:** consultas de lectura mediante el MCP de modelado al modelo abierto `GFTS_BI` y revisión del repositorio.
No utilicé control de pantalla ni modifiqué relaciones, medidas, tablas o datos en esta revisión.
La importación es una copia local; no volví a consultar las tablas de Databricks para estos conteos.

## Corrección posterior — 19 de noviembre de 2026

Corregí las claves y relaciones de negocio, añadí dimensiones de snapshot/servicio/fecha y configuré las agregaciones de columnas.
El [modelo corregido](../BI/modelado/README.md) registra implementación y resultados.
Los calendarios automáticos anteriores permanecen ocultos por compatibilidad; el calendario analítico explícito contiene 365 fechas de 2026.
El puente ruta–ubicación y la publicación Gold siguen pendientes.
La revisión inicial que sigue conserva el diagnóstico previo a esa corrección.

## Lo que comprobé en el modelo abierto

Encontré ocho tablas Silver en modo Importar.
Todas conservan `source_feed_version` y `source_sha256`.
Los IDs fuente permanecen como texto.
Las tablas no contienen columnas de procedencia técnica innecesarias para esta prueba.
Conservo `analysis_window_start`, `analysis_window_end` y `source_temporal_warning` porque explican el alcance de service_dates.
No encontré stop_times, shape_points ni una tabla Gold importada.
Encontré dos medidas numéricas de comprobación y una medida de presentación HTML en agency.

| Tabla | Snapshot 2025-10-28 | Snapshot 2026-09-29 |
| --- | ---: | ---: |
| agency | 7 | 7 |
| routes | 676 | 1045 |
| stops | 6530 | 8314 |
| calendar | 7 | 7 |
| calendar_dates | 140 | 133 |
| service_dates | Fuera del alcance | 1403 |
| trips | 107162 | 181060 |
| frequencies | 2 | 14 |

Verifiqué unicidad por versión, hash y clave de negocio:
agency_id; route_id; stop_id; service_id en calendar; service_id y date en calendar_dates;
service_id y service_date en service_dates; trip_id en trips; trip_id y start_time_seconds en frequencies.
Las quince combinaciones de tabla y snapshot devuelven tantas claves distintas como filas.
Esto comprueba estas claves, no sustituye todas las reglas Silver.

Comprobé cero referencias huérfanas de rutas a agencias, viajes a rutas,
ventanas a viajes, padres declarados de stops a stops y viajes al conjunto de servicios de calendar/calendar_dates.
Todos esos cruces incluyen versión y hash.

## Lo que debo corregir antes de confiar en indicadores filtrados

### Relaciones por snapshot

Encontré una relación automática entre frequencies[trip_id] y trips[trip_id].
Power BI la configuró uno a uno y con filtro en ambas direcciones.
Los IDs de viaje son globalmente distintos en estas dos importaciones y frequencies tiene dieciséis IDs distintos.
Por eso no atribuyo una mezcla de snapshots demostrada a esa relación actual.
Sin embargo, esa relación no conserva el contrato por snapshot ni admite como diseño general varias ventanas por viaje.
La sustituiré por una relación compatible con claves completas y dirección de filtro definida según su función.
Una dimensión de viajes única puede filtrar muchas ventanas del mismo viaje.

No encontré relaciones de negocio entre agency, routes, stops, calendar, calendar_dates y service_dates.
Las otras seis relaciones conectan fechas con calendarios automáticos ocultos.
No considero esas relaciones un modelo de negocio terminado.

Probé COUNTROWS(trips) sin filtros y después con agency_id=1 y versión 2026 aplicados únicamente sobre agency.
Ambas consultas devolvieron 288222.
El filtro de agency todavía no llega a trips; no utilizaré ese resultado como indicador por agencia.

Propondré snapshot_key y claves de entidad deterministas compartidas entre las tablas de consumo.
No generaré índices independientes ni uniré las tablas únicamente por sus IDs fuente.
No conectaré directamente stops con agency: necesito la relación distinta ruta–ubicación.

### Fechas

Encontré seis calendarios automáticos y una plantilla oculta de fechas.
Calendar contiene fechas entre 2000-01-01 y 2099-01-01.
Calendar_dates conserva excepciones desde 2023; no traslado esas fechas a otro año.
Service_dates abarca exclusivamente 2026-01-01 a 2026-12-31.
Prepararé una dimensión de fechas explícita para el horizonte analítico 2026.
No usaré start_date o end_date como sustitutos de fechas activas.

### Agregación de columnas

Power BI dejó Sum como agregación predeterminada en códigos y otros campos numéricos.
Entre ellos aparecen route_type, location_type, wheelchair_boarding, exception_type,
exact_times, exact_times_effective, coordenadas, segundos horarios y días semanales.
Configuraré los códigos como No resumir.
Definiré por separado cómo mostrar coordenadas, intervalos y horas.
No interpretaré la suma de headway_secs como intervalo típico del sistema.
No modifiqué esas propiedades durante esta revisión.

## Qué significa el plan Gold actual

Las preguntas e historias ya existen en [mis historias de negocio](power_bi_user_stories.md).
Las piezas siguientes siguen siendo propuestas salvo la cobertura, que tiene procesador local.
No convierto esta tabla en una afirmación de publicación en Databricks.

| Pieza | Una fila | Indicadores y uso | Estado y dependencia |
| --- | --- | --- | --- |
| Contexto de snapshot y catálogos de agencia/ruta | Un snapshot o una entidad dentro de su snapshot, según la dimensión. | Rutas publicadas; viajes declarados; filtros coherentes. | Claves y proyecciones por completar. Correspondencia de componentes por aprobar. |
| gold_gtfs_trip_coverage | Un viaje declarado dentro del snapshot. | Total de viajes declarados; cero, una o varias visitas; proporciones por categoría; contexto de frecuencias. | Procesador local y contrato existentes. Publicación pendiente según la documentación. |
| Programación por ruta y fecha | Una ruta y fecha dentro del snapshot y horizonte. | Rutas con programación declarada; viajes asociados a servicios activos; días con programación. | Contrato e implementación pendientes. Empiezo solo con 2026. |
| Relación ruta–ubicación | Una pareja distinta ruta y ubicación dentro del snapshot. | Ubicaciones relacionadas con una ruta o componente. | Agregar en Databricks desde viajes y visitas. No necesito importar todas las visitas en Power BI. |
| Catálogo analítico de ubicaciones | Una ubicación dentro del snapshot. | Ubicaciones por tipo; estaciones y plataformas; jerarquías padre–hijo. | Conservar tipos, ausencias y claves; accesibilidad requiere cerrar su semántica. |
| Ventanas de frecuencia con contexto | Una ventana de un viaje/plantilla dentro del snapshot. | Ventanas, plantillas distintas e intervalo de cada ventana. | Silver ya aporta datos; contrato de consumo y relación con ruta/viaje pendientes. No equivale a salidas operadas. |
| Contexto de calidad y procedencia | Un snapshot o ejecución según su ficha. | Fuentes, exclusiones, horizonte y ejecución que sustentan cada resultado. | Contrato y proyección de auditoría pendientes. No necesito restaurar todas las columnas técnicas en cada dimensión. |

## Primer bloque que construiré

Priorizaré General y Calidad, como establece [el plan Gold](gold_plan.md).

1. Cerraré claves y proyecciones de snapshot, agencia y ruta.
2. Completaré las fichas de los indicadores de cobertura.
3. Validaré el publicador de cobertura existente en Databricks y reconciliaré sus resultados.
4. Publicaré la cobertura aprobada y las dimensiones o vistas de consumo necesarias.
5. Crearé las relaciones Power BI y las medidas DAX numéricas.
6. Comprobaré filtros de snapshot, agencia y ruta con un caso conocido antes de añadir tarjetas HTML.
7. Después ampliaré Programación y Red con sus hechos y puentes.

No necesito importar stop_times o shape_points completos para el primer bloque.
Sí necesito que Databricks los consulte cuando prepare los agregados correspondientes.
No hay motivo para volver a cargar Bronze o Silver.

## Indicadores iniciales de cobertura

| Indicador | Cálculo de negocio | Tratamiento del filtro y límite |
| --- | --- | --- |
| Viajes declarados | Filas de cobertura al grano viaje–snapshot. | Snapshot y ruta/agencia compatibles; no cuenta vehículos ni operación observada. |
| Viajes sin visitas | Filas con coverage_status=sin_visitas. | Conserva viajes declarados aunque falten visitas. |
| Viajes con una visita | Filas con coverage_status=una_visita. | No demuestra recorrido entre paradas. |
| Viajes con varias visitas | Filas con coverage_status=varias_visitas. | No certifica un recorrido completo. |
| Porcentaje sin visitas | Viajes sin visitas / todos los viajes declarados del mismo contexto. | Mantiene snapshot, agencia y ruta; retira únicamente el filtro de categoría del denominador. Denominador cero devuelve BLANK. |
| Viajes o plantillas con ventanas | Viajes declarados con frequency_window_count mayor que cero. | No sustituye el conteo de ventanas ni representa salidas exactas. |
| Visitas con pareja de horas completa | Suma de complete_time_pair_count. | Mide presencia de ambos horarios, no exactitud ni puntualidad. |
| Porcentaje de visitas con pareja completa | Suma de complete_time_pair_count / suma de visit_count. | Denominador de visitas; no de viajes. Denominador cero devuelve BLANK. |

El contrato Gold conserva conteos y categorías reutilizables.
Las medidas DAX calcularán totales y cocientes según los filtros.
La medida HTML solo representará esos resultados.
Las tarjetas siempre indicarán snapshot, unidad y alcance.

Como referencia previa, el perfil de Genie del 17 de noviembre documentó para 2026:
181060 viajes declarados; 739 sin visitas; 61 con una visita; 180260 con varias visitas;
9408893 visitas y 14 ventanas.
No volví a calcular esa clasificación desde stop_times durante esta revisión.
La reconciliación del notebook 20 deberá comprobarla de nuevo antes de publicar.

## Decisiones que todavía debo cerrar

- Qué componentes agrupan las agencias/rutas de cada snapshot, especialmente Alimentación y Dual.
- Qué ubicaciones incluye cada tarjeta: catálogo total o ubicaciones relacionadas con rutas.
- Qué definición usaré para extremos horarios y sus exclusiones.
- Cómo mostraré accesibilidad desconocida y herencia entre ubicaciones.
- Qué detalles necesito conservar para investigar casos concretos.

Cada nueva tabla Gold debe responder las seis preguntas de negocio acordadas.
No añadiré métricas de puntualidad, ocupación, espera real o cumplimiento contractual con GTFS estático.

## Referencias

- [Plan Gold](gold_plan.md).
- [Selección de consumo](power_bi_consumption_model.md).
- [Historias y preguntas](power_bi_user_stories.md).
- [Contrato de cobertura](contracts/trip_coverage.md).
- [Perfil previo de cobertura](trip_coverage_profile_2026.md).
