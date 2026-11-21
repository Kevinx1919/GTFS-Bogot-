# Mi perfil de shape_points de 2025 y 2026

**Fecha:** 11 de noviembre de 2026. **Estado:** perfil de lectura completado. El contrato ya tiene implementación local. Las 36 pruebas seleccionadas pasaron sin omisiones. El despliegue funcional Silver ya está comprobado; el cierre conserva el alcance de esa confirmación. Las fuentes son shapes Bronze y, para contexto, trips Bronze y routes Silver. La exploración no modificó tablas, Raw, el Job de Workspace ni Archify.

## Alcance y evidencia

Trabajé con los snapshots 2025-10-28 / 07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952 y 2026-09-29 / 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097. Las nueve consultas definitivas están en el [notebook 14](../databricks/notebooks/silver/14_profile_gtfs_shape_points.ipynb), con 55 filas estructuradas recuperadas sin truncamiento: 23 + 4 + 8 + 2 + 2 + 2 + 2 + 2 + 10.

Extendí la consulta de estructura para incluir coordenadas distintas; la versión final sustituye a su consulta preliminar, sin guardar ambas como pasos redundantes. Los resultados numéricos vienen de las filas estructuradas, no solo del resumen narrativo de Genie. El notebook no tiene todavía una ejecución completa documentada como cuaderno. Las lecturas exploratorias no fijan versiones Delta ni una transacción entre tablas.

## Qué estoy mirando

Una fila es un punto de un trazado. El ID identifica la forma completa y la secuencia identifica el punto dentro de ella. Como un dibujo que une puntos numerados, puedo volver al mismo lugar con otro número sin repetir la misma clave. La identidad del contrato es versión + hash + shape_id + secuencia; no equivale a contar paradas, buses o viajes.

## Conteos y geometría observada

| Medida | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| Puntos | 909.878 | 926.501 |
| Trazados distintos | 676 | 1.045 |
| Mínimo de puntos por trazado | 4 | 7 |
| Máximo de puntos por trazado | 3.711 | 3.424 |
| Mínimo de coordenadas distintas por trazado | 4 | 4 |
| Trazados con menos de dos coordenadas distintas | 0 | 0 |
| Trazados con alguna coordenada repetida | 326 | 1.044 |
| Repeticiones de coordenada dentro de cada trazado | 1.779 | 33.443 |
| Segmentos entre puntos | 909.202 | 925.456 |
| Segmentos con extremos de igual coordenada | 439 | 30.208 |
| Huecos de secuencia | 0 | 0 |

Los segmentos reconcilian exactamente con puntos menos trazados: 909.878 - 676 = 909.202 y 926.501 - 1.045 = 925.456. Los resultados agrupados también reconcilian con los conteos fuente. Todos los trazados tienen al menos cuatro coordenadas distintas; no encontré geometrías reducidas a una única posición en este control.

Las repeticiones de coordenada dentro del mismo trazado incluyen revisitas no consecutivas. Los 439 / 30.208 segmentos con extremos iguales son otra medida, limitada a puntos consecutivos. Ninguna de esas cifras representa copias idénticas de una fila ni autoriza a quitar puntos por coordenada.

## Campos, tipos y controles limpios

Ambos encabezados shapes.txt publican únicamente shape_id, shape_pt_lat, shape_pt_lon y shape_pt_sequence, los cuatro string en Bronze. La distancia shape_dist_traveled no está publicada y tampoco existe como columna histórica en la tabla consultada. No la interpreto como cero ni invento un valor medido por el proveedor.

En los cuatro campos de ambos snapshots encontré cero nulos, cadenas vacías, solo espacios y espacios extremos. Los controles dieron cero IDs inválidos, secuencias no convertibles a int no negativo, coordenadas inválidas/no finitas/fuera de rango y pares (0,0). La versión, la ruta Staging esperada y el timestamp de carga no presentaron incoherencias en las filas del hash seleccionado.

Tampoco encontré grupos de copias idénticas, claves fuente repetidas, variantes conflictivas ni colisiones de clave por convertir la secuencia. Esta es evidencia del perfil; el pipeline deberá volver a validar antes de publicar.

Propongo ID string, secuencia int y coordenadas double. Las secuencias observadas están entre 0 y 3.711 en 2025, y entre 1 y 3.424 en 2026. El tipo int alcanza para estos valores; que se vean números en un ID no lo convierte en una cantidad.

## El inicio de la secuencia no tiene que ser uniforme

| Inicio del trazado | 2025 | 2026 |
| --- | ---: | ---: |
| Secuencia 0 | 1 | 0 |
| Secuencia 1 | 549 | 1.045 |
| Otro valor | 126 | 0 |

No todos los trazados de 2025 empiezan en 0: ese es solo el mínimo global. La secuencia sirve para ordenar y puede comenzar en otro valor o tener saltos válidos. Los controles actuales no encontraron huecos. No interpreté el orden físico de una tabla Delta como orden de viaje.

Las coordenadas extremas medidas fueron latitud 4,404851–4,820244 y longitud -74,215524–-74,005762 en 2025; latitud 4,385691–4,820270 y longitud -74,220389–-74,005729 en 2026, redondeadas a seis decimales. Comprobé rangos numéricos, no pertenencia a un polígono oficial ni cercanía a cada parada.

## Qué significan los segmentos largos

Calculé distancia recta aproximada entre puntos consecutivos como diagnóstico, con radio terrestre de 6.371.000 metros. No es shape_dist_traveled, no demuestra la distancia recorrida por calles y no incluye tiempo para calcular velocidad. El máximo es 1.716,316 metros en ambos snapshots y pertenece a C_1, relacionado vía trips con route_type 6 de routes Silver. Ese código corresponde a transporte por cable aéreo según la [referencia GTFS](https://gtfs.org/documentation/schedule/reference/#routestxt).

También aparece el trazado de bus 12793 de 2026, secuencia 210→211, con 1.400,538 metros. Queda como caso para revisión cartográfica, sin declararlo error o corregir coordenadas por esa sola cifra. El contexto del cable muestra por qué no usaré un umbral universal de rechazo para todo el sistema.

## Relación con trips

| Medida | 2025 | 2026 |
| --- | ---: | ---: |
| Filas trips consultadas | 107.162 | 181.060 |
| Viajes sin shape_id | 0 | 0 |
| Viajes con shape_id no encontrado | 0 | 0 |
| Trazados referenciados | 672 | 1.045 |
| Trazados sin referencia desde trips | 4 | 0 |

Usé IDs de trazado distintos dentro de versión/hash para no multiplicar viajes por su cantidad de puntos. Los cuatro trazados no referenciados permanecen en el catálogo: no prueban por sí solos un fallo ni un servicio operado. Esta revisión no valida toda la tabla trips ni demuestra una relación uno a uno con routes. No interpreto diferencias de registros entre versiones como crecimiento de oferta.

## Qué propongo para Silver

Conservaré las coordenadas y el orden publicados. Los puntos consecutivos iguales generarán advertencia, sin eliminarse; las revisitas y los trazados sin referencias serán información. Las claves conflictivas o conversiones obligatorias inválidas llevarán evidencia a cuarentena y bloquearán la publicación completa según el contrato. La distancia ausente permanecerá null con source_columns como evidencia de ausencia.

Dejé estas decisiones como [contrato shape_points_v1](contracts/shape_points.md), con implementación y despliegue funcional comprobados. El [plan](shape_points_plan.md) registra las etapas completadas y el despliegue pendiente. La implementación posterior añade el procesador, la tarea de plantilla y las pruebas. El [cierre posterior](silver_execution.md#cierre-de-la-ejecución-de-shape_points) registra su funcionamiento en Databricks. La siguiente relación a preparar después será trips.
