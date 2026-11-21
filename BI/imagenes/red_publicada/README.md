# Red publicada: mi tercer panel

**Estado:** primera implementación comprobada en DAX y guardada en PBIP. Renderizado e interacción real en Desktop pendientes.

[Abro la vista previa](red_publicada_preview.html). [Leo el plan y las definiciones](../../../docs/power_bi_red_plan.md).

Quiero responder: **¿qué ubicaciones relaciona una ruta y qué otras rutas comparten esos IDs?**
Uso el catálogo completo del snapshot 2026, sin aplicar las fechas A y B.
Una relación publicada no garantiza una visita en una fecha concreta.

| Elemento | Qué responde | Cómo lo calculo |
| --- | --- | --- |
| Ubicaciones relacionadas | ¿Cuántas ubicaciones distintas tiene la selección? | Distintos stop_key en las parejas Gold filtradas. |
| Compartidas | ¿Cuáles aparecen en dos rutas o más? | Busco el grado de cada stop_key frente a todas las rutas del mismo snapshot. |
| Rutas y coordenadas | ¿Cuántas rutas participan y qué coordenadas faltan? | Distintos route_key; coordenadas desde stops sin rellenar ausencias. |
| Mapa | ¿Dónde están las ubicaciones del contexto? | Proyecto latitud y longitud; agrupo símbolos por una, dos a cinco y seis o más rutas. |
| Ficha | ¿Qué representa este ID? | Consulto su nombre, tipo, padre y cantidad de rutas dentro y fuera de la selección. |
| Comparación de rutas | ¿Quién comparte ubicaciones con una ruta? | Intersección de conjuntos de stop_key; excluyo la ruta elegida. |
| Tabla nativa | ¿Qué ubicación quiero consultar? | Agrupo etiquetas del puente; selecciono una fila para filtrar la ficha y las medidas. |

Sin una ruta única, el gráfico inferior muestra rutas con más ubicaciones en el contexto.
Con una ubicación única, muestra sus rutas relacionadas.
El título cambia con la pregunta.

## Cómo leo el mapa y los padres

El mapa conserva el contexto de componente y ruta cuando consulto una ubicación.
La marca amarilla indica la referencia consultada, incluso fuera de ese contexto.
Por eso sus puntos de contexto pueden superar el conteo filtrado de la tarjeta.
La cuadrícula no representa calles ni límites oficiales.
No dibujo líneas entre puntos ni confirmo transbordos físicos.

Una estación padre puede tener cero relaciones directas.
La ficha consulta sus ubicaciones hijas por separado.
No añado el padre como visita ni fusiono plataformas.
El nombre «Estación San Victorino» no determina su tipo: respeto location_type.

## Identidad y rendimiento

Mantengo versión, SHA-256 e ID en cada clave.
Las etiquetas muestran nombre y código para evitar seleccionar nombres ambiguos.
Aplico la ubicación al puente mediante TREATAS y conservo las 21 relaciones físicas.

Añadí report_stop_label a stops y al puente en el modelo de consumo.
Añadí report_stop_route_count al puente para reutilizar el grado del catálogo.
Calculo esas columnas al actualizar el modelo; no modifican Silver ni Gold de Databricks.
La clave de ubicación incluye el snapshot, así que el grado no mezcla versiones.

La tabla nativa anterior recalculaba el catálogo para cada fila.
En una consulta de ocho filas medí 100.276 ms; con el grado precalculado medí 460 ms.
La prueba completa de 8.159 filas concilió una suma de grados de 62.715 en 118 ms.
Son mediciones del motor local, no tiempos garantizados del informe completo.

Configuré la selección de la tabla como filtro de los visuales HTML.
Esa selección no modifica los selectores de componente y ruta.
No uso JavaScript para interacciones dentro del visual HTML de Power BI.
La tabla HTML del prototipo muestra hasta ocho filas y no sustituye la tabla nativa del PBIP.

## Qué comprobé

- Catálogo: 62.715 parejas, 8.159 ubicaciones y 1.045 rutas.
- Ubicaciones compartidas: 7.295 de 8.159, equivalentes al 89,4 %.
- Grados: 864 ubicaciones con una ruta, 3.134 con dos a cinco y 4.161 con seis o más.
- San Victorino, ID 57866: 44 rutas del catálogo.
- TransMiCable: cuatro ubicaciones relacionadas; compartir cero IDs no descarta una conexión física.
- Padres, referencias ajenas a una ruta, coordenadas y selección de una fila nativa.
- Independencia respecto a A/B y fuente Gold ausente en 2025: BLANK, no cero.
- Quince contextos DAX y 45 combinaciones de contexto y tamaño, sin desbordamiento ni recortes de paneles.
- Esquemas oficiales PBIR de las tres páginas y sus visuales.

La vista previa permite cinco componentes, cuatro rutas y tres ubicaciones de ejemplo.
Su JavaScript elige resultados reales ya calculados por DAX.
El informe conserva el catálogo completo.
El diseño adaptable del HTML no constituye un diseño móvil nativo de Power BI.

## Cómo reviso la entrega

Abro BI/GFTS_BI.pbip y reviso **Red publicada**.
Evito guardar encima desde una instancia que todavía conserve el diseño anterior.
Pruebo componente, ruta, ubicación y una fila de la tabla.
Compruebo la navegación entre Panorama, Programación y Red publicada.
No necesito otra importación desde Databricks.
El PBIX anterior conserva su diseño anterior.

[Medidas y columnas de presentación](../../medidas/red_publicada/README.md).


## Explicación de negocio y siguiente panel

Documenté [qué responde Red publicada y cómo lo calculo](../../../docs/power_bi_red_negocio.md).
Uso ejemplos de San Victorino, estaciones padre y TransMiCable para explicar sus límites.
El [cierre de la primera versión](../../../docs/power_bi_cierre_v1.md) incluye Revisión de información y la revisión final del informe.

## Navegación completa

Añadí el enlace y el botón nativo hacia [Revisión de información](../revision_informacion/revision_preview.html).
Componente y ruta se sincronizan entre las cuatro páginas.
La revisión de navegación real en Desktop sigue pendiente.


## Menú lateral depurado

Retiré el título Laboratorio y los botones hacia las páginas de prueba Agency y Control.
Conservo Panorama, Programación, Red publicada y Revisión.
Actualicé las medidas HTML, los botones nativos y las vistas previas.


## Texto y acción en el mismo botón

Sustituí las etiquetas HTML con botones transparentes superpuestos por cuatro botones nativos con texto propio.
Cada botón ocupa la misma fila en las cuatro páginas y apunta a su página correspondiente.
Marco la página actual en rojo y con un fondo suave.
Conservo la marca y la nota inferior en HTML. La vista previa usa enlaces HTML equivalentes.
En Power BI Desktop pruebo la navegación con Ctrl + clic; en modo lectura uso un clic.
La navegación nativa quedó confirmada en la revisión del 20 de noviembre de 2026.


## Estado activo y protección frente a etiquetas antiguas

La página actual usa fondo rojo suave y texto rojo oscuro en el botón nativo.
Los otros botones cambian de fondo al pasar el cursor.
El CSS del fondo HTML oculta cualquier menú o etiqueta Laboratorio que pueda quedar de una versión anterior.
Comprobé por MCP que las cuatro medidas del modelo abierto ya no devuelven etiquetas de navegación ni Laboratorio.
Queda la revisión integral de filtros, legibilidad y rendimiento en Desktop.


## Confirmación del menú — 20 de noviembre de 2026

La navegación ya funciona en el informe. El texto pertenece al botón nativo y solo la página actual conserva el fondo rojo suave.
No dibujo nombres de páginas ni Laboratorio en el HTML del lateral.
La confirmación de navegación no certifica todos los filtros combinados ni el rendimiento.
