# Mi segundo panel: Programación

**Estado:** primera implementación comprobada en el motor y en la vista previa.
La revisión del renderizado dentro de Power BI Desktop queda pendiente.

[Abro Programación](programacion_preview.html).
[Consulto el plan y las reglas de negocio](../../../docs/power_bi_programacion_plan.md).

## Qué responde

La pregunta principal es: **¿qué días y horas publica la programación de la selección?**
Puedo explorar todo el sistema, un componente o una ruta concreta.
El panel profundiza en los horarios después del Panorama general.

| Elemento | Pregunta | Interpretación |
| --- | --- | --- |
| Viajes elegibles | ¿Qué viajes sostienen el perfil horario? | Muestra el subconjunto con extremos comparables y su denominador activo. |
| Primera salida y última llegada | ¿Cuáles son los extremos publicados de la selección? | Pueden pertenecer a viajes distintos; no prueban continuidad ni duración de un recorrido. |
| Calendario mensual | ¿Qué patrón diario declara el mes de A? | Usa cantidades sin frecuencias o plantillas, con intensidad relativa al mes. |
| Muestra de seis viajes | ¿Qué ejemplos concretos publican esas horas? | Recupera las primeras salidas elegibles de A; cada tooltip conserva ID y precisión. |
| Perfil por hora | ¿Cuándo se concentran las primeras salidas declaradas? | Cada viaje elegible aporta un solo conteo; comparo A y B. |
| Ventanas de frecuencia | ¿Qué tramos e intervalos publica la selección? | Conservo segundos y exact_times; no genero salidas ni estimo espera. |
| Alcance | ¿Qué precisión publican los extremos y qué viajes quedan fuera? | Explico el denominador y las categorías excluyentes de timing. |

## Cómo conecté los datos

Obtengo los servicios activos de service_dates para A.
Aplico sus service_key a trips y sus trip_key a trip_timing mediante TREATAS.
Para B repito la selección retirando únicamente el filtro de fecha analizada.
Mantengo componente, ruta, versión y hash.
Las ventanas usan los mismos viajes activos de A.
No añadí relaciones físicas ni una expansión diaria de todos los viajes.

Conservo horas GTFS mayores de 24 y muestro también sus segundos.
Por ejemplo, 25:09:00 continúa a la 01:09 del día siguiente del servicio.
No lo convierto en una hora UTC ni reduzco el valor con módulo 24.
El calendario no identifica festivos a partir del nombre del día.
Las plantillas permanecen fuera del perfil de salidas individuales.

## Ejemplo que concilia ambos paneles

Comparé el domingo 22 con el jueves 19 de noviembre de 2026.
El domingo tiene 40.229 viajes activos: 40.210 elegibles, 17 sin visitas y dos plantillas.
Panorama muestra 40.227 viajes sin frecuencias: los elegibles más los 17 sin visitas.
Programación utiliza 40.210 para el perfil horario y explica los 19 excluidos.
Sus extremos publicados son 03:00:00 y 25:09:00.
Todos los extremos elegibles de ese contexto aparecen como aproximados publicados.

En TransMiCable encontré dos plantillas activas y ninguna salida individual elegible.
Las dos ventanas publican intervalos de 16 y 10 segundos.
No interpreto esos intervalos como minutos ni como espera observada.

La ruta L81, ID 13780, pertenece a Dual.
No tiene programación en A y conserva 293 viajes elegibles en B.
Muestro cero viajes y horas ausentes para A.

## Ruta y navegación

Encontré nombres cortos compartidos por varias filas de ruta.
Añadí report_route_label como código más ID en el modelo de Power BI.
Verifiqué 1.045 etiquetas distintas para 1.045 rutas del snapshot 2026.
La etiqueta sirve para seleccionar; las relaciones siguen usando route_key.

Configuré cuatro grupos de filtros sincronizados entre Panorama y Programación.
Fecha A, fecha B, componente y ruta usan los mismos campos en ambas páginas.
Los botones de navegación son nativos de Power BI.
La vista previa enlaza archivos HTML y cada página abre su selección inicial.
No promete sincronizar filtros entre archivos independientes.

## Archivos y comprobaciones

Creé 18 medidas en gold_gtfs_trip_timing: nueve numéricas y nueve de presentación.
La muestra es un fragmento incrustado en el calendario.
La página utiliza ocho visuales HTML, cuatro filtros y cuatro botones nativos.
El modelo conserva 23 tablas y 21 relaciones físicas.
La etiqueta de ruta es una columna calculada de presentación.

Consulté 90 contextos reales con tres fechas, cinco componentes y cuatro rutas de ejemplo.
La selección global también forma parte de las comprobaciones.
Concilié viajes activos contra el hecho diario.
Concilié conteos horarios, precisión, muestras, ventanas y valores del calendario.
Comprobé horas mayores de 24, TransMiCable y una ruta inactiva en A.
Probé fechas ausentes directamente en el motor.

La vista previa utiliza JavaScript para elegir resultados DAX ya calculados.
El visual de Power BI usa HTML, SVG y CSS, sin scripts ni recursos externos.
Revisé 1440, 768 y 390 píxeles en un navegador aislado.
El lienzo de Power BI permanece en 1440 × 900.
La versión móvil de la vista previa no constituye un diseño móvil nativo.

Para revisar el informe, abro GFTS_BI.pbip sin sobrescribirlo con el estado anterior de la instancia abierta.
Las cuatro tablas Gold ya estaban importadas; no necesito otra exportación desde Databricks.
El PBIX anterior conserva su diseño anterior.

[Medidas](../../medidas/programacion/README.md).
[CSS](programacion.css).
[Definición de negocio de Inicio](../../../docs/power_bi_panorama_negocio.md).


## Qué responde este panel y cuál sigue

Documenté [cada pregunta, cálculo y limitación de Programación](../../../docs/power_bi_programacion_negocio.md).
El diseño quedó aprobado; mantengo pendiente la revisión del renderizado dentro de Desktop.
Añadí un botón nativo y un enlace de vista previa hacia [Red publicada](../red_publicada/red_publicada_preview.html).
La página tiene ahora cuatro botones nativos, además de ocho visuales HTML y cuatro selectores.
Componente y ruta se sincronizan entre las tres páginas; las fechas solo entre Panorama y Programación.

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
