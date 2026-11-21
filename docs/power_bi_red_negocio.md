# Qué responde Red publicada y cómo lo calculo

**Actualización del cierre — 20 de noviembre de 2026:** navegación nativa confirmada; cuatro paneles y cuatro Gold disponibles. [Estado vigente](project_status.md) y [menú y componentes](power_bi_navigation_images.md).

**Estado:** implementé el tercer panel y comprobé sus resultados DAX y su vista previa.
La revisión del renderizado y las interacciones dentro de Desktop sigue pendiente.

Quiero responder: **¿qué ubicaciones relaciona una ruta y qué otras rutas comparten esos mismos IDs?**
Este panel ayuda a explorar el catálogo publicado antes de investigar una ubicación concreta.
No demuestra operación diaria ni confirma transbordos físicos.

| Pregunta | Qué muestro | Cómo lo calculo |
| --- | --- | --- |
| ¿Cuántas ubicaciones relaciona mi selección? | Ubicaciones distintas. | Cuento stop_key distintos en las parejas Gold filtradas por componente, ruta y ubicación. |
| ¿Cuántas ubicaciones comparten varias rutas? | Cantidad compartida y proporción sobre las ubicaciones seleccionadas. | Comparo cada stop_key con todas las rutas del mismo snapshot; compartida significa dos rutas o más. |
| ¿Cuántas rutas participan? | Rutas con ubicaciones relacionadas. | Cuento route_key distintos en el contexto elegido. |
| ¿Qué ubicaciones carecen de coordenadas? | Cantidad sin latitud o longitud. | Consulto stops; no sustituyo coordenadas ausentes. |
| ¿Dónde están las ubicaciones del contexto? | Mapa de coordenadas con categorías por cantidad de rutas. | Proyecto latitud y longitud; distingo una ruta, dos a cinco y seis o más. |
| ¿Qué representa este ID? | Nombre, tipo, padre y rutas relacionadas. | Consulto stops del mismo snapshot y comparo rutas del contexto con rutas del catálogo. |
| ¿Qué otras rutas comparten ubicaciones con esta ruta? | Hasta cinco rutas y sus cantidades compartidas. | Comparo conjuntos de stop_key y excluyo la ruta elegida. |
| ¿Qué ID quiero investigar? | Tabla de ubicaciones con nombre, ID y cantidad de rutas. | Agrupo las etiquetas del puente y aplico la fila elegida como filtro de los visuales HTML. |

## Qué representa una fila de la fuente

Uso gold_gtfs_route_stop como fuente principal.
Cada fila representa una pareja ruta–ubicación dentro de una versión y un hash.
Una pareja puede conservar muchas visitas publicadas sin crear más ubicaciones distintas.
Los nombres, tipos y coordenadas proceden de silver_gtfs_stops.
Los componentes y las etiquetas de ruta proceden de agency y routes.

Esto es como separar una lista de lugares de la cantidad de veces que aparecen en los itinerarios.
Una ubicación compartida por diez rutas sigue siendo una ubicación única.
Por eso no sumo ubicaciones por ruta para calcular el total del sistema.

## Cómo llegan los filtros a los resultados

Primero elijo componente y ruta.
Las relaciones existentes llevan esa selección hasta el puente ruta–ubicación.
Después puedo consultar una ubicación mediante el selector o la tabla nativa.
Aplico la selección de stops al puente mediante TREATAS.
La tabla nativa también puede filtrar el puente directamente mediante su etiqueta.

Cada route_key y stop_key conserva versión, SHA-256 e ID.
Las etiquetas muestran nombre y código; no sustituyen esas claves.
No uno ubicaciones distintas porque tengan nombres iguales.

Componente y ruta comparten filtros sincronizados con Panorama y Programación.
Las fechas A y B no filtran este panel.
Una relación del catálogo no garantiza una visita a esa ubicación en una fecha concreta.

## Qué significa «compartida»

Para cada ubicación seleccionada, busco todas sus rutas dentro del mismo snapshot.
La referencia incluye rutas ajenas al componente o ruta que elegí.
Así puedo investigar relaciones con el resto del catálogo.

Esto explica por qué una ubicación puede aparecer como compartida después de elegir una sola ruta.
La selección contiene una ruta; la referencia sigue incluyendo las demás.
La proporción divide ubicaciones compartidas entre ubicaciones relacionadas de la selección.

En el catálogo 2026 encontré 7.295 ubicaciones compartidas entre 8.159 ubicaciones relacionadas.
La proporción es aproximadamente 89,4 %.
No significa que el 89,4 % de Bogotá tenga cobertura ni que permita transbordos confirmados.

## Por qué el mapa y la tarjeta pueden mostrar cantidades diferentes

El mapa conserva las ubicaciones del contexto de componente y ruta.
La tarjeta responde también a la ubicación consultada.
La marca amarilla señala esa referencia sobre el mapa de contexto.

Por ejemplo, San Victorino, ID 57866, relaciona 44 rutas del catálogo.
Al consultarlo sin restringir rutas, la tarjeta muestra una ubicación y 44 rutas.
El mapa conserva los 8.159 puntos del contexto general y destaca ese ID.
Las etiquetas distinguen ambos conteos.

La cuadrícula no representa calles ni límites oficiales.
No conecto puntos como si fueran un trazado ordenado.
El color expresa cantidad de rutas relacionadas; no expresa frecuencia ni intensidad de pasajeros.

## Cómo leo una estación padre

Una estación padre agrupa referencias de ubicaciones hijas.
No añado automáticamente ese ID como visita del itinerario.
La ficha muestra las ubicaciones hijas relacionadas con las rutas del contexto por separado.

Portal 20 de Julio, ID 10000, permite consultar ese caso.
Puede mostrar cero relaciones directas y conservar referencias a ubicaciones hijas.
Eso no demuestra ausencia de servicio.
La palabra «estación» en un nombre tampoco determina su tipo: consulto location_type.

## Qué cambia en el gráfico inferior

Sin una ruta única, comparo rutas por cantidad de ubicaciones del contexto.
Con una ruta única, comparo otras rutas por cantidad de IDs compartidos con ella.
Con una ubicación única, puedo revisar las rutas que la relacionan.
El título indica la pregunta correspondiente.

TransMiCable relaciona cuatro ubicaciones en el catálogo revisado.
La ausencia de IDs compartidos con otras rutas no descarta conexiones físicas entre ubicaciones diferentes.
Para confirmar transbordos necesitaría una definición y evidencia adicionales.

## Cómo trato ceros y ausencias

Muestro cero cuando la fuente existe y no encuentro relaciones para los filtros elegidos.
Una ubicación ajena a la ruta puede conservar su ficha y mostrar cero rutas del contexto.
Si falta la fuente Gold de una identidad, muestro ausencia de evaluación, no cero relaciones.
No relleno coordenadas ni convierto una estación padre en una parada visitada.

## Cómo mantengo la consulta rápida

Precalculé la cantidad de rutas por stop_key en una columna del modelo de Power BI.
La tabla nativa reutiliza ese valor en lugar de recalcular todo el catálogo para cada fila.
La actualización del modelo recalcula la columna.
No cambié las tablas de Databricks ni las relaciones físicas para esa optimización.

## Evidencia y siguiente decisión

Concilié 62.715 parejas, 8.159 ubicaciones y 1.045 rutas del catálogo 2026.
Comprobé 15 selecciones DAX y 45 combinaciones de selección y tamaño de pantalla.
Revisé padres, referencias ajenas a una ruta y la selección equivalente de una fila nativa.
El motor y la vista previa están comprobados; Desktop requiere su propia revisión.

Después continúo en Revisión de información para entender qué casos limitan el análisis.
Una relación publicada no demuestra que el itinerario esté completo ni que el viaje haya operado.

[Abro Red publicada](../BI/imagenes/red_publicada/red_publicada_preview.html).
[Consulto las medidas](../BI/medidas/red_publicada/README.md).
[Reviso el cierre de esta versión](power_bi_cierre_v1.md).
