# Mi incorporación de las cuatro Gold a Power BI

Conecté el modelo local GFTS_BI mediante MCP, sin acceder a la pantalla.
Reutilicé la conexión Databricks existente y sus credenciales.
Conservé una copia de las definiciones antes de editar.
No necesité exportar CSV ni modificar datos en Databricks.

## Fuentes incorporadas

| Tabla | Filas importadas | Grano |
| --- | ---: | --- |
| gold_gtfs_trip_coverage | 181.060, ya existente | Un viaje declarado. |
| gold_gtfs_route_service_day | 305.165 | Una ruta y fecha de servicio. |
| gold_gtfs_route_stop | 62.715 | Una pareja ruta–ubicación. |
| gold_gtfs_trip_timing | 181.060 | Un viaje declarado con clasificación horaria. |

Seleccioné quince, seis y diecisiete campos de negocio para las tres fuentes nuevas.
Excluí sus campos de ejecución y carga del consumo normal.
Conservé versión/hash e IDs para las claves y los oculté en la vista de campos.
Añadí claves calculadas con la misma definición que usa el resto del modelo.
Importé datos reales y recalculé las relaciones antes de probar sus filtros.

## Relaciones

- routes filtra route_service_day por route_key.
- dim_gtfs_fecha filtra route_service_day por service_date.
- routes filtra route_stop por route_key.
- trips filtra trip_timing por trip_key.

Las cuatro relaciones nuevas son activas, muchos a uno y de dirección única desde la dimensión.
No añadí otra relación desde snapshot hacia cada hecho.
El modelo conserva veintidós tablas y veintiuna relaciones físicas.
Quince tablas son de negocio y siete son objetos internos de fechas.
Actualicé el diagrama Consumo GTFS con sus quince tablas de negocio.

## Ubicaciones y mapa

Creé la medida Ubicación relacionada y la organicé en Red/Ubicaciones.
Utiliza TREATAS para aplicar la ubicación del mapa al puente dentro de la medida.
El filtro de ruta y componente llega por la relación física de routes.

No activé una segunda relación desde stops hacia el puente.
Snapshot ya filtra routes y stops por caminos separados; una conexión física adicional introduciría dos caminos hasta el puente.
La relación virtual mantiene la selección del mapa sin alterar los filtros del catálogo.
La [medida y su fuente](../BI/medidas/route_stop/README.md) explican esa decisión.
El visual de mapa todavía debe construirse y aplicar Ubicación relacionada = 1.
La fecha no filtra este mapa de catálogo.

## Comprobaciones DAX

Las tres filas de fechas reprodujeron los resultados de Databricks:

| Fecha | Rutas | Viajes sin frecuencias | Plantillas |
| --- | ---: | ---: | ---: |
| 2026-11-19 | 863 | 80.201 | 6 |
| 2026-11-21 | 775 | 60.618 | 6 |
| 2026-11-22 | 789 | 40.227 | 2 |

Comprobé 305.165 claves únicas de ruta y fecha y 180.246 viajes horariamente elegibles.
La medida del mapa devolvió 8.159 ubicaciones relacionadas en el contexto general.
TransMiCable devolvió una ruta, catorce viajes del catálogo y cuatro ubicaciones relacionadas.
No encontré claves huérfanas de ruta, ubicación o viaje en los hechos incorporados.
Los conjuntos vacíos de COUNTROWS aparecieron como BLANK en las consultas de huérfanos.

El filtro de fecha actúa sobre el hecho diario.
No convierte automáticamente los intervalos del catálogo en horarios de una fecha activa.
Esa medida temporal sigue requiriendo aplicar explícitamente los servicios activos.

## Persistencia y siguiente paso

Guardé las definiciones del modelo en TMDL dentro de GFTS_BI.SemanticModel.
El proyecto de referencia es BI/GFTS_BI.pbip.
No actualicé el archivo PBIX anterior ni publiqué el reporte en Power BI Service.
El modelo abierto ya tiene las tablas; para cargar el diagrama guardado puedo volver a abrir el PBIP.
Evito sobrescribir las definiciones externas desde una sesión anterior.
La siguiente tarea es construir las medidas de negocio y las páginas desde sus preguntas.
