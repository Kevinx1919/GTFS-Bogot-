# Mi preparación del consumo de negocio

La conexión Databricks existente permite incorporar las nuevas tablas cuando estén publicadas.
No necesito exportar CSV ni importar todas las tablas Silver.
El manifiesto sources_plan.json define columnas y relaciones propuestas; no modifica el PBIP por sí solo.

El hecho diario ya está publicado en Workspace para 2026 con 305.165 filas únicas.
La incorporación al modelo local Power BI sigue pendiente.
Después importaré gold_gtfs_route_service_day con las quince columnas de negocio del manifiesto.
Conservaré las claves de fuente para relacionar datos y las ocultaré en la vista normal.
No importaré los tres campos técnicos de publicación como indicadores.

Los controles de componente y fecha deben alcanzar el nuevo hecho.
La dimensión de fecha no filtra automáticamente el catálogo de trips.
Las medidas diarias se crearán sobre el hecho diario ya publicado.
No crearé medidas apuntando a una tabla que todavía no existe en el modelo.

## Mapa

Propongo Azure Maps nativo con stop_lat y stop_lon como coordenadas, sin sumar ni promediar ubicaciones distintas.
El [visual admite coordenadas explícitas](https://learn.microsoft.com/en-us/azure/azure-maps/power-bi-visual-get-started).
Configuraré el identificador y el detalle para conservar cada ubicación como punto.
Distinguiré estaciones y paradas/plataformas por location_type.
Las coordenadas ya tienen categorías Latitude y Longitude en el modelo actual.

El catálogo 2026 tiene 8.314 ubicaciones con coordenadas presentes: 8.159 de tipo 0 y 155 de tipo 1.
Eso no certifica posición física exacta ni cobertura poblacional.
Para seleccionar una ruta y reducir el mapa necesito el puente ruta–ubicación.
No crearé una relación directa agency→stops ni convertiré un mapa de puntos en un trazado.
Los recorridos geométricos requieren shape_points y un orden de puntos propio.
Las tarjetas HTML acompañarán el mapa nativo; no necesito imponer HTML a cada visual.

## Diseño

El boceto anterior deja de ser la base de diseño.
El siguiente reporte partirá de preguntas, comparaciones y acciones, con identidad roja y amarilla.
No reutilizaré su distribución por obligación ni mostraré versión/hash como protagonista.
La implementación visual empieza después de comprobar las nuevas fuentes de negocio.


## Fuentes de mapa y extremos horarios preparadas localmente

El manifiesto conserva seis campos del puente ruta–ubicación y diecisiete de extremos horarios.
Ambas entidades tienen publicador local y requieren validate y publish en Workspace.
Las [guías de ruta–ubicación](../../docs/gold_route_stop_execution.md) y [extremos](../../docs/gold_trip_timing_execution.md) conservan los pasos.
El mapa filtrará puntos mediante existencia de parejas; las medidas de intervalos usarán elegibilidad y precisión.
No marqué esas dos tablas como importadas en el modelo Power BI.
