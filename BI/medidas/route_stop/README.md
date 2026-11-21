# Filtro de ubicaciones del mapa

Creé Ubicación relacionada en gold_gtfs_route_stop, carpeta Red/Ubicaciones.
Uso TREATAS por stop_key para transferir la ubicación del mapa al puente.
El filtro de ruta llega al puente por su relación física.
El mapa aplicará valor 1 para conservar solamente ubicaciones relacionadas.

No activé una relación física stops→puente, porque snapshot ya filtra stops y ruta por caminos separados.
Así evito un segundo camino activo desde snapshot hasta el puente.
La identidad completa permite separar las ubicaciones históricas.
La fecha no filtra la red de catálogo.

La prueba de TransMiCable devolvió cuatro ubicaciones y la prueba general 8.159.
El filtro del visual de mapa debe configurarse cuando construya esa página.
