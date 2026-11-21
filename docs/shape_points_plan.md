# Mi plan para shape_points

**Fecha:** 11 de noviembre de 2026. **Estado:** perfil y revisión completados. Implementé shape_points_v1 localmente. Las 36 pruebas seleccionadas pasaron sin omisiones. El despliegue funcional en Databricks ya está comprobado. El [informe](shape_points_profile_2025_2026.md) conserva el perfil. El [contrato](contracts/shape_points.md) define las reglas implementadas. La [guía](silver_execution.md#despliegue-de-shape_points_v1) conserva los pasos de despliegue.

## Qué representa y por qué sigue ahora

Una fila representa un punto ordenado de un trazado GTFS. Al unir los puntos según su secuencia puedo dibujar el recorrido planificado. Es como un dibujo que se forma uniendo puntos numerados: varios puntos pertenecen a la misma figura.

No es una parada de stops ni una posición GPS observada. Un trazado puede pasar dos veces por una zona y varios viajes pueden compartirlo. Más adelante trips usará shape_id para indicar su trazado; por eso preparo esta referencia antes de validar viajes. No depende de service_dates para calcular sus puntos: el orden del Job también serializa escrituras de auditoría.

El archivo fuente conserva el nombre shapes.txt y la tabla Bronze bronze_gtfs_shapes. El nombre Silver implementado es silver_gtfs_shape_points para hacer visible el grano. Implementé ese mapeo explícitamente. Conservé Bronze y el nombre shapes.txt.

## Alcance y tipos implementados

Revisaré por separado los snapshots 2025-10-28 y 2026-09-29, con los hashes ya documentados. Llamo S a la pareja versión + hash; las claves, ventanas y relaciones siempre quedan dentro de S.

| Campo fuente | Tipo Silver | Qué revisaré |
| --- | --- | --- |
| shape_id | string | Requerido, no vacío, espacios extremos y conservación de identidad. Se repite entre puntos del mismo trazado. |
| shape_pt_sequence | int, con rango comprobado | Requerido, entero no negativo y único por trazado. Si el rango no cabe, acordaré un tipo mayor antes de publicar. |
| shape_pt_lat | double | Requerida, numérica finita y entre -90 y 90. |
| shape_pt_lon | double | Requerida, numérica finita y entre -180 y 180. |
| shape_dist_traveled | double, si está publicado | Opcional, numérica finita, no negativa y creciente según la secuencia; revisaré ausencias y unidades disponibles. |

La clave implementada es S + shape_id + shape_pt_sequence. Cerré los tipos con el perfil; la obligatoriedad y semántica se contrastan con la [referencia oficial de shapes.txt](https://gtfs.org/documentation/schedule/reference/#shapestxt).

GTFS admite saltos en la secuencia: 0, 6, 11 puede ser válido. No exigiré empezar en 1 ni números consecutivos. Si el orden físico del TXT es diferente, usaré la secuencia para interpretar el trazado. La distancia publicada debe crecer con esa secuencia; no asumiré metros o kilómetros ni la calcularé para rellenar un dato ausente.

## Preguntas del perfil antes del contrato

El primer pase de esta lista ya está ejecutado y documentado; la conservaré como guía para revisar nuevos snapshots. Encontré 676 / 1.045 trazados, sin errores de claves o conversiones en los controles ejecutados, pero con coordenadas consecutivas iguales y cuatro trazados sin referencias en 2025. Esos casos se conservan y su tratamiento se define en la propuesta, sin descartarlos automáticamente.

1. Revisaré encabezados originales, auditoría de esquema, tipos Bronze, procedencia y presencia por snapshot. Separaré campo ausente de campo publicado con valores vacíos.
2. Mediré filas, trazados distintos y completitud por campo: nulos, vacíos, solo espacios y espacios extremos. No traeré los puntos al driver para contar.
3. Separaré copias fuente idénticas de conflictos con la misma clave y atributos diferentes. Revisaré además colisiones de secuencias después del cast, por ejemplo 01 y 1; no elegiré una fila al azar.
4. Revisaré formatos y rangos numéricos, valores no finitos y secuencias negativas o fuera de rango. Un ID de trazado repetido en muchos puntos es normal; una clave de punto repetida requiere interpretación.
5. Agruparé por trazado y revisaré cantidad de puntos, posiciones repetidas y segmentos consecutivos de longitud cero. Un regreso a una coordenada puede representar un bucle, no un duplicado de clave. Perfilaré antes de decidir bloqueos o advertencias.
6. Si existe distancia publicada, revisaré cobertura, negativos y variaciones al ordenar puntos. Registraré descensos o igualdades sin corregirlos silenciosamente y cerraré su tratamiento en el contrato.
7. Consultaré desde trips Bronze la cobertura de shape_id dentro de S, separando ausencia de identificador y referencia no resuelta. Será diagnóstico de integración, no validación completa de trips ni una razón automática para eliminar trazados sin viajes referenciados.

Conservaré las consultas definitivas en un único notebook de perfilado y documentaré sus bloques en el runbook al crearlo. Un informe breve separará resultados medidos, requisitos GTFS y decisiones propias de calidad. No repetiré ingestion Raw/Bronze.

## Implementación después de revisar el perfil

Cerré el contrato y reutilicé la preparación Spark, el escritor, auditoría, cuarentena y notebook 10. La resolución shapes → shape_points es explícita. La fuente y la entidad Silver tienen nombres distintos. Consolidaré solo copias idénticas según el contrato; los conflictos y conversiones inválidas conservarán evidencia y bloquearán la primera publicación según la política acordada.

Aplicaré filtros de snapshot y selección de columnas al inicio. Las ventanas se particionarán por S + shape_id y se ordenarán por secuencia tipada; evitaré ordenamientos globales, UDF de Python y collect de puntos. No introduciré cache, particionado físico o una tabla de geometrías adicional sin medir y justificar su uso.

Para validar referencias de trips usaré un conjunto único de shape_id dentro de S, no un join contra cada punto: unir directamente viajes con todos los puntos multiplicaría las filas. La geometría completa se consumirá por separado cuando la pregunta lo requiera.

## Pruebas y primera publicación previstas

Usaré fixtures pequeñas para claves compuestas, casts, coordenadas inválidas, secuencias con saltos, bucles, copias y conflictos. Incluiré distancia ausente y, si está publicada, sus errores y orden. La integración Delta comprobará validación sin escritura, publicación, reintento sin duplicados, conservación de otro snapshot y rechazo sin alterar Silver.

Reutilicé el entorno local de Spark/Delta. Las 36 pruebas seleccionadas pasaron sin omisiones. La plantilla ya incorpora la séptima tarea. El flujo de shape_points ya funciona en Databricks. El [cierre](silver_execution.md#cierre-de-la-ejecución-de-shape_points) registra la confirmación funcional. Los conteos concretos de Workspace siguen sin adjuntarse en este cierre. El siguiente paso es trips.

## Qué sigue y qué podrá analizarse

El orden restante es shape_points → trips → frequencies → stop_times, con las dependencias condicionales que cierre cada contrato. Feed_info y tarifas siguen sujetos a la pregunta de negocio del plan general.

Shape_points permitirá representar trazados planificados; por sí sola no mide buses circulando, velocidad, puntualidad, demanda ni cantidad de viajes. Las longitudes y métricas Gold necesitarán unidades y definición de negocio explícitas; no sumaré una distancia acumulada punto por punto como si fueran segmentos independientes.

Referencias internas: [plan Silver](silver_design.md), [cierre de service_dates](silver_execution.md#cierre-de-la-ejecución-de-service_dates) y [ficha obligatoria de negocio Gold](silver_design.md#definición-de-negocio-obligatoria-para-cada-futura-tabla-gold).
