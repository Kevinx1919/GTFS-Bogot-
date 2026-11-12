# Mi contrato Silver shape_points_v1

**Fecha:** 11 de noviembre de 2026. **Estado:** reglas revisadas e implementación local preparada. Las 36 pruebas seleccionadas pasaron sin omisiones. La primera publicación en Databricks sigue pendiente. El [perfil](../shape_points_profile_2025_2026.md) conserva las mediciones de Bronze. No las presento como resultados de Silver.

## Qué representa e identidad

Una fila representa un punto de un trazado planificado. La clave validada es source_feed_version + source_sha256 + shape_id + shape_pt_sequence. No confundo una coordenada repetida con una clave repetida: un recorrido puede regresar al mismo lugar con otra secuencia.

La fuente es shapes.txt y la tabla existente bronze_gtfs_shapes. La salida implementada es silver_gtfs_shape_points. Implementé un mapeo explícito entre entidad Silver, archivo y tabla fuente; no renombraré Bronze ni exigiré un shape_points.txt inexistente. El procesador lee una versión Delta fijada y el encabezado fuente del mismo snapshot.

## Tipos y controles implementados

| Campo | Tipo | Regla |
| --- | --- | --- |
| shape_id | string | Requerido, sin vacío, espacios extremos ni caracteres de control; identidad conservada sin normalizar. |
| shape_pt_sequence | int | Requerida, representación de entero no negativo y sin desbordamiento. No exijo que empiece en 0 o 1 ni que sea consecutiva. |
| shape_pt_lat | double | Requerida, numérica finita y en [-90, 90]. |
| shape_pt_lon | double | Requerida, numérica finita y en [-180, 180]. |
| shape_dist_traveled | double nullable | Opcional; no publicada en ninguno de estos dos snapshots. Ausencia se conserva como null, nunca como cero ni como una distancia calculada. Si aparece, compruebo finitud, no negatividad y crecimiento estricto entre distancias informadas. |

Los enteros encajan en int según el perfil: las secuencias máximas son 3.711 y 3.424. La referencia de campos y secuencia procede de [GTFS shapes.txt](https://gtfs.org/documentation/schedule/reference/#shapestxt); los tipos Spark, las advertencias y el bloqueo completo de un snapshot son decisiones del proyecto. Las secuencias admiten solo dígitos y pueden contener ceros iniciales. Los decimales admiten signo y notación científica finita. No quito espacios extremos de valores numéricos. Los espacios simples de una distancia opcional producen null. Los caracteres de control generan rechazo, incluso en opcionales. No altero IDs.

Conservo las cuatro columnas técnicas de procedencia, source_columns, silver_rule_version y los campos de ejecución del escritor común. La tabla tiene 13 columnas físicas. source_columns distinguirá distancia no publicada de una columna publicada con valores nulos. Un campo desconocido o una procedencia incoherente detendrá la revisión del contrato.

## Copias, conflictos y alcance del rechazo

Consolido solo copias fuente idénticas, contabilizando su multiplicidad. Si una misma clave tiene atributos distintos, preservaré las variantes en cuarentena y bloquearé la publicación completa del snapshot. Compruebo conflictos antes de normalizar y después de convertir la secuencia: 01 y 1 no pueden acabar en la misma clave sin una decisión explícita. No usaré dropDuplicates sobre shape_id, coordenadas o clave para elegir una fila arbitraria.

Una conversión requerida inválida, coordenada fuera de rango o clave vacía llevará su causa a cuarentena; no publicaré un trazado incompleto eliminando únicamente su punto malo. Los resultados existentes de otro snapshot permanecerán intactos. Un cambio de esquema destino requerirá migración explícita.

## Geometría: advertencias e información

Conservo los puntos consecutivos con igual coordenada. Emito CONSECUTIVE_POSITION_REPEATED en el punto posterior. Las copias idénticas no generan segmentos falsos. El perfil encontró 439 segmentos así en 2025 y 30.208 en 2026. Son secuencias distintas; no justifican eliminar evidencia fuente. Las revisitas no consecutivas se conservarán como información, porque también pueden representar un regreso o un bucle.

Un trazado con menos de dos coordenadas distintas genera SHAPE_WITH_FEWER_THAN_TWO_POSITIONS en sus puntos; no lo convierto aquí en un requisito GTFS adicional. El perfil encontró cero casos y un mínimo de cuatro coordenadas distintas por trazado en ambos snapshots; la regla implementada conserva sus puntos con advertencia. Un par (0,0) también se señalará sin asumir una regla geográfica universal de rechazo. No verifico pertenencia al polígono administrativo de Bogotá en esta v1.

Los segmentos largos quedan como diagnóstico. El máximo medido, 1.716,316 metros en línea recta, corresponde a C_1 y se relaciona con route_type 6. Ese contexto impide usar un umbral uniforme arbitrario para rechazar trazados. El segmento de bus 12793 de 2026, secuencia 210→211 y 1.400,538 metros, queda anotado para revisión cartográfica; no lo declaro corregido ni erróneo solo con esa medida.

Los cuatro trazados de 2025 sin referencias desde trips se conservan como información. No crearé una dependencia obligatoria de trips para publicar sus puntos ni eliminaré los que no estén usados en este feed. Para validar trips posteriormente usaré un catálogo único de shape_id dentro del snapshot, evitando multiplicar viajes al unirlos con cada punto.

## Ejecución prevista y límites de negocio

Reutilizo la preparación Spark, el escritor, auditoría, cuarentena y notebook 10. La plantilla añade publish_shape_points después de service_dates. Esa dependencia serializa escrituras; shape_points no necesita sus datos. Aplicaré filtro por hash con controles de versión/ruta antes de las ventanas. Las comparaciones de secuencia se harán dentro del snapshot y trazado; no usaré collect de puntos, ordenamiento global ni UDF de Python.

Las pruebas cubren tipos, conflictos, saltos, revisitas, advertencias y publicación. La integración comprueba reintento, histórico y cuarentena. Las 36 pruebas seleccionadas pasaron sin omisiones. Tampoco afirmo que la consulta exploratoria sustituya la validación de stop_times o trips.

La tabla servirá para dibujar trazados publicados. No mide posición observada, velocidad, puntualidad ni pasajeros. Las distancias rectas calculadas en el perfil son diagnósticas y no se publicarán como shape_dist_traveled ni como longitud vial real. Gold requerirá su ficha de negocio, unidades y grano aprobados.


## Códigos y métricas

SHAPE_POINT_KEY_CONFLICT rechaza variantes diferentes de una clave fuente. SHAPE_SEQUENCE_CAST_COLLISION rechaza las representaciones distintas que producen una misma clave tipada. SHAPE_DISTANCE_NOT_INCREASING rechaza distancias que no crecen. La comparación salta ausencias y usa la última distancia informada. No rellena la ausencia.

COORDINATES_ZERO_PAIR genera advertencia para el par (0,0). Los trazados sin referencias desde trips son información del perfil. No consulto trips durante esta transformación.

warning_rows cuenta filas fuente con alguna advertencia. Puede incluir copias idénticas antes de consolidarlas. Las métricas consecutive_position_repeated_rows, degenerate_shape_rows y zero_coordinate_pair_rows cuentan candidatos únicos. Pueden solaparse y no deben sumarse como categorías exclusivas.

La cuarentena conserva shape_pt_sequence como texto fuente. Así registra errores de conversión y ceros iniciales. Silver publica la secuencia int. Las ventanas geométricas usan únicamente puntos válidos con procedencia coherente. Un rechazo bloquea el snapshot completo; no publico una geometría recortada.


El resultado de validación incluye un DataFrame de advertencias con warning_codes. No publico warning_codes como columna Silver. La auditoría conserva warning_rows. El resumen del Job también incluye las métricas adicionales.
