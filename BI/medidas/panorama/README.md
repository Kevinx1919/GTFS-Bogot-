# Medidas del Panorama

Organicé nueve medidas de cálculo en `Inicio\Métricas` y nueve medidas HTML en `Inicio\Presentación HTML`.
La tabla base es `gold_gtfs_route_service_day`.
Una fila representa una ruta en una fecha de servicio para una identidad de feed.

| Pregunta | Medida o gráfico | Definición |
|---|---|---|
| ¿Cuántas rutas tienen programación? | `Panorama · Rutas` | Rutas distintas en la fecha analizada. |
| ¿Cuántos viajes declara el calendario? | `Panorama · Viajes sin frecuencia` | Suma de viajes declarados sin plantillas de frecuencia. |
| ¿Cuántas plantillas usa? | `Panorama · Plantillas` | Suma de plantillas activas, separadas de las salidas individuales. |
| ¿Qué cambia respecto a otra fecha? | Medidas con sufijo `comparación` | El mismo cálculo en la fecha comparada, conservando ruta y componente. |
| ¿Cómo se distribuye la semana? | `Panorama · Semana HTML` | Veintiocho días hasta el domingo de la semana analizada. |
| ¿Qué componente concentra la oferta? | `Panorama · Componentes HTML` | Dos barras por componente con la misma unidad y escala. |
| ¿Qué rutas explican la diferencia? | `Panorama · Rutas HTML` | Tres rutas con mayor diferencia absoluta entre fechas. |
| ¿Cambia el conjunto de rutas? | `Panorama · Lectura HTML` | Intersección y diferencias de conjuntos, mediante claves de ruta. |

## Reglas de interpretación

Calculo la diferencia como **analizada menos comparada**.
Calculo el porcentaje como **(analizada − comparada) / comparada**.
Si la comparada vale cero, presento cantidades y evito un porcentaje indefinido.
Diferencio una fecha fuera del horizonte de una fecha válida con cero programación.
Un resultado menor no demuestra un incumplimiento.
Una ruta exclusiva de una fecha no demuestra una apertura o un cierre físico.

`Panorama · Usa plantillas` identifica selecciones que solo tienen plantillas por frecuencia.
`Panorama · Volumen` y `Panorama · Volumen comparación` seleccionan la unidad de los gráficos.
Cada gráfico conserva una sola unidad en todas sus filas.
El ranking usa esta misma selección de unidad, sin mezclar viajes y plantillas entre rutas.

Conservo versión, hash e ID en las claves del modelo.
Uso `dim_gtfs_fecha_comparacion` sin relaciones físicas.
Las medidas comparativas aplican su fecha mediante `TREATAS` sobre `dim_gtfs_fecha`.
No añado caminos bidireccionales entre hechos.

## Comprobación inicial

Comparé el domingo 22 con el jueves 19 de noviembre de 2026.
Obtuve 789 frente a 863 rutas, 40.227 frente a 80.201 viajes sin frecuencias y 2 frente a 6 plantillas.
La diferencia de viajes es −49,8% al redondear a una cifra decimal.
Encontré 610 rutas comunes, 179 exclusivas de la analizada y 253 exclusivas de la comparada.

[Fuente de los cálculos](metricas.dax).
[Fuente de presentación](presentacion_html.dax).
[Diseño y comprobaciones](../../imagenes/panorama/README.md).


## Mapa de coordenadas y rediseño visual

Añadí `Panorama · Mapa HTML` y mantuve las medidas numéricas anteriores.
El mapa selecciona rutas con programación en A y sus ubicaciones del catálogo.
No calcula visitas diarias por ubicación.
Usa claves de snapshot en las relaciones virtuales.
La fecha B no cambia el mapa.

Incorporé perfiles semanales a las tarjetas y puntos conectados a la comparación por componente.
El panel temporal incrusta el fragmento `Rutas HTML`.
Las comparaciones sin una fecha válida presentan un mensaje de selección.
El [alcance del mapa](../../imagenes/panorama/README.md) conserva el detalle de negocio y las limitaciones.
