# Mis medidas de Red publicada

Creé 18 medidas en gold_gtfs_route_stop, organizadas en Red publicada\Métricas y Red publicada\Presentación HTML.
Nueve medidas calculan cantidades o disponibilidad y nueve producen HTML.
La medida Tabla previa HTML solo sirve para el prototipo; el PBIP utiliza una tabla nativa.

[metricas.dax](metricas.dax) contiene los cálculos.
[presentacion_html.dax](presentacion_html.dax) contiene el formato.
Las definiciones TMDL del PBIP son las utilizadas por Power BI.

## Referencia global y contexto

Conservo versión y hash conjuntamente al comparar otras rutas.
Una ubicación compartida tiene al menos dos rutas en todo el catálogo del mismo snapshot.
Ese denominador no se limita al componente elegido.
Las cantidades de la tarjeta sí responden al componente, ruta y ubicación seleccionados.

El mapa mantiene componente y ruta al consultar un ID.
La ficha diferencia rutas del contexto, rutas del catálogo y referencias padre.
Las fechas A y B no filtran este catálogo.

## Columnas del modelo de consumo

```dax
// silver_gtfs_stops
report_stop_label =
    COALESCE([stop_name], [stop_id]) & " · " & [stop_id]

// gold_gtfs_route_stop
report_stop_label =
    LOOKUPVALUE(silver_gtfs_stops[report_stop_label],
                silver_gtfs_stops[stop_key], [stop_key])

report_stop_route_count =
    CALCULATE(COUNTROWS(gold_gtfs_route_stop),
              ALLEXCEPT(gold_gtfs_route_stop,
                        gold_gtfs_route_stop[stop_key]))
```

Gold garantiza una pareja por route_key y stop_key.
Por eso COUNTROWS por stop_key representa rutas distintas.
No utilizo estas columnas para cambiar la identidad ni las relaciones históricas.
La medida Rutas por ubicación reutiliza MAX del grado almacenado y deja el total sin ubicación única en BLANK.
También comprueba la selección virtual de stops para limitar las filas de la tabla nativa.

[Explicación del panel y sus pruebas](../../imagenes/red_publicada/README.md).
