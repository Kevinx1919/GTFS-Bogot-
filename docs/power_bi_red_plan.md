# Mi tercer panel: Red publicada

> **Estado vigente — 20 de noviembre de 2026:** las cuatro Gold de 2026 están publicadas e importadas y los cuatro paneles están implementados. La navegación nativa funciona; la revisión integral y la actualización completa siguen pendientes. [Estado actual](project_status.md).

## Registro de diseño e implementación

Conservo a continuación las decisiones y comprobaciones de cada etapa. Los pendientes de esas fechas describen su momento; el estado vigente anterior los sustituye.

**Estado:** primera implementación comprobada sobre el catálogo 2026 importado y guardada en PBIP. Renderizado en Desktop pendiente.

## Pregunta de negocio

Como persona de planeación o información al público, quiero conocer las ubicaciones que relaciona una ruta.
También quiero identificar qué otras rutas comparten esos mismos IDs.

**Pregunta central:** ¿qué ubicaciones publica el catálogo de la selección y qué relaciones comparten sus rutas?
No respondo por cobertura poblacional, transbordos confirmados ni operación diaria.

## Qué mostraré

| Bloque | Pregunta | Definición |
| --- | --- | --- |
| Cantidades | ¿Cuántas ubicaciones y rutas relaciona la selección? | Distintos stop_key y route_key del puente, sin sumar visitas repetidas. |
| Ubicaciones compartidas | ¿Cuáles aparecen en al menos dos rutas? | Evalúo cada ID frente a todas las rutas del mismo snapshot, incluso fuera del componente seleccionado. |
| Mapa de coordenadas | ¿Dónde están las ubicaciones del contexto de rutas? | Muestro coordenadas, intensidad por cantidad de rutas y una referencia para la ubicación consultada. |
| Ficha de ubicación | ¿Qué nombre, tipo y padre publica ese ID? | Leo stops del mismo snapshot y distingo referencia padre de ubicación relacionada. |
| Tabla de ubicaciones | ¿Qué IDs permiten explorar relaciones concretas? | Tabla nativa ordenada por rutas relacionadas y limitada al contexto mediante una medida. |
| Rutas relacionadas | ¿Qué otras rutas comparten ubicaciones con una ruta elegida? | Comparo su conjunto de stop_key con otras rutas del snapshot; retiro solo el ámbito de comparación de rutas. |

Sin una ruta única, la comparación muestra rutas con más ubicaciones en la selección.
Con una ruta única, muestra otras rutas que comparten sus ubicaciones seleccionadas.
Los nombres de las medidas indicarán ese cambio de pregunta.

## Grano y claves

Gold route_stop contiene una pareja ruta–ubicación por versión y hash.
Sus coordenadas y nombres permanecen en stops.
La selección utiliza route_key y stop_key del mismo snapshot.
Las etiquetas muestran nombre e ID para distinguir nombres repetidos.
No agrupo IDs distintos solo porque compartan nombre o coordenadas.

Mantengo las relaciones físicas existentes.
La selección de ubicación llega al puente mediante TREATAS.
El cálculo de referencia global vuelve a aplicar versión y hash conjuntamente después de retirar filtros de ruta.
No retiro el ámbito histórico al buscar otras rutas.

## Fechas y padres

Este panel representa el catálogo del snapshot; no aplica A ni B.
Una pareja del catálogo no garantiza visita diaria a esa ubicación.
No añado estaciones padre como si fueran visitas ni fusiono sus plataformas.
La ficha permite consultar un padre y sus referencias por separado.
Un padre puede tener cero relaciones directas sin que eso signifique que no existan plataformas asociadas.

## Mapa y ausencia

El mapa mantiene el contexto de rutas cuando consulto una ubicación concreta.
La ubicación consultada aparece como referencia separada, incluso si no tiene relación directa en ese contexto.
El conteo de ubicaciones relacionadas y el de puntos de contexto pueden ser distintos.
Lo indicaré en sus etiquetas.
Las coordenadas ausentes producen un diagnóstico; no las relleno.
La cuadrícula no representa calles ni límites oficiales.
No conecto puntos como si fueran un trazado ordenado.

## Comprobaciones

- Concilio 62.715 parejas con 8.159 ubicaciones distintas y 1.045 rutas en el catálogo 2026.
- Compruebo 7.295 ubicaciones relacionadas con al menos dos rutas.
- Concilio categorías de una ruta, dos a cinco y seis o más.
- Compruebo que el grado global no cambia al elegir una sola ruta.
- Compruebo ubicación sin relación con la ruta, estación padre y TransMiCable.
- Verifico que cambiar A o B no modifica medidas del catálogo.
- Compruebo claves por snapshot, tabla nativa, navegación y ausencia de coordenadas.
- Reviso tres anchos en la vista previa y dejo pendiente el renderizado real de Desktop.

[Contrato de la fuente Gold](contracts/route_stop.md).

## Resultado del primer incremento

Implementé las cantidades, el mapa de coordenadas, la ficha de ubicación y la comparación de rutas.
Añadí tres selectores y una tabla nativa para consultar IDs del contexto.
Sincronicé componente y ruta con las dos páginas anteriores; no añadí fechas a esta página.
Configuré la selección de filas como filtro de los visuales HTML.

Precalculé el grado por stop_key en el modelo de consumo para acelerar la tabla nativa.
Conservé las 23 tablas y 21 relaciones físicas.
No cambié fuentes ni tablas de Databricks.

[Abro Red publicada](../BI/imagenes/red_publicada/red_publicada_preview.html).
[Consulto los resultados y las comprobaciones](../BI/imagenes/red_publicada/README.md).

La siguiente página será **Revisión de información**.
Mostrará los casos que requieren aclaración antes del análisis, utilizando cobertura y elegibilidad Gold.
No convertiré esos casos automáticamente en fallos del servicio.


## Definición de negocio documentada

Documenté [qué responde cada visual y cómo lo calculo](power_bi_red_negocio.md).
La explicación incluye filtros, referencia global, padres, ceros y ejemplos reales.
El [plan de cierre](power_bi_cierre_v1.md) concreta el cuarto panel y las comprobaciones restantes.
