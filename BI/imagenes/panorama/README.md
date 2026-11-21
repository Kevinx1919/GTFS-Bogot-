# Inicio · Panorama de oferta

[Abro el Panorama actual](panorama_v2_preview.html).

Rediseñé la composición después de revisar la referencia SiteOps y Power BI Design Files.
Ahora combino tarjetas con perfiles semanales, un panel de lectura y un mapa de coordenadas GTFS.
El perfil temporal muestra cuatro semanas y comparte espacio con las tres rutas de mayor diferencia.
Los componentes se comparan con puntos conectados y una escala común.

## Cómo leo la página

1. Elijo una fecha analizada A y una fecha comparada B.
2. Filtro Troncal, Zonal (SITP), Alimentación, Dual o TransMiCable.
3. Leo rutas, viajes sin frecuencias y plantillas como cantidades diferentes.
4. Reviso la diferencia y el componente con mayor variación absoluta del contexto.
5. Localizo las ubicaciones del catálogo vinculadas a las rutas con programación en A.
6. Examino el patrón de 28 días y las tres rutas que más cambian.

Esto es como comparar el horario de un domingo con el de un jueves.
Una cantidad menor puede corresponder al calendario publicado.
No demuestra una cancelación ni un incumplimiento.

## Decisiones visuales

Usé rojo `#DD212C` para A y amarillo `#FFC928` para B.
Las letras A y B acompañan los colores para identificar las fechas.
Una superficie oscura concentra el hallazgo de la selección.
Las tarjetas muestran siete días con escalas propias; no comparo alturas entre tarjetas.
El gráfico de componentes usa una sola escala para las cinco categorías.
Las barras del ranking representan diferencias absolutas y muestran el signo numérico.
Las transiciones duran 200 ms y respetan movimiento reducido.

Tomé las tarjetas con micrográficos de la dirección solicitada en la referencia.
Conservé esos micrográficos aunque la guía general de diseño favorece tarjetas más simples.
La decisión responde al diseño aprobado y mantiene los datos verificables.

## Qué representa el mapa

**Pregunta:** ¿qué ubicaciones del catálogo se relacionan con rutas programadas en A?

Parto de las claves de ruta presentes en `gold_gtfs_route_service_day` para A.
Cruzo esas claves con `gold_gtfs_route_stop`.
Obtengo ubicaciones únicas mediante `stop_key` y sus coordenadas desde `silver_gtfs_stops`.
Mantengo componente, ruta e identidad del feed.

El puente ruta–ubicación representa el catálogo completo de cada ruta del snapshot.
No distingue qué variante de viaje visita cada ubicación en una fecha concreta.
Por eso el mapa no garantiza visitas a cada punto ese día.
Tampoco representa ubicaciones de vehículos ni actividad en tiempo real.

El conteo incluye ubicaciones relacionadas con coordenadas disponibles.
Los puntos sin coordenadas no pueden dibujarse.
Una selección sin puntos presenta un mensaje explícito.
La selección inicial contiene 7.834 ubicaciones relacionadas y 789 rutas programadas.
TransMiCable contiene cuatro ubicaciones relacionadas y una ruta programada.

Dibujo cada ubicación mediante coordenadas GTFS y una escala uniforme.
Aplico una corrección coseno a la longitud para conservar proporciones locales.
La extensión se adapta a cada selección; no comparo tamaños de mapas entre componentes.
La cuadrícula orienta el dibujo; no representa calles ni divisiones administrativas.
No conecto puntos para inventar un trazado.
El mapa no incluye fondo cartográfico, desplazamiento ni zoom manual.
Los filtros nativos de Power BI actualizan su selección.

## Cálculo y presentación

Conservo nueve medidas de cálculo y nueve medidas HTML en la tabla de programación diaria.
`Rutas HTML` es un fragmento usado dentro de `Semana HTML`.
La página contiene nueve visuales HTML, cuatro filtros nativos y cuatro botones de navegación.
Las relaciones físicas permanecen iguales: 23 tablas y 21 relaciones, incluidos objetos automáticos.
La fecha comparada sigue desconectada y las medidas usan `TREATAS`.
Las claves conservan versión, SHA-256 e ID.

El perfil incluye 28 días hasta el domingo de la semana analizada.
Fuera del horizonte publicado conservo ausencia en lugar de inventar programación.
Si borro una fecha, la comparación pide una selección válida.
El mapa requiere A y no depende de B.

Las plantillas por frecuencia permanecen separadas de los viajes sin frecuencias.
En selecciones que solo tienen plantillas, los gráficos comparan plantillas.
Su variación no representa variación de salidas, capacidad, pasajeros ni espera.
El gráfico de componentes elimina únicamente el filtro de componente como referencia del sistema.
Conserva el filtro de ruta.

## Comprobaciones y alcance

Consulté 81 contextos DAX y 27 contextos geográficos diferentes.
Reutilizo cada mapa cuando solo cambia B para reducir el tamaño de la vista previa.
Comprobé cantidad de puntos, rutas, unidades y perfiles temporales.
Probé A ausente, B ausente y TransMiCable directamente en el motor DAX.
Validé 16 archivos PBIR contra esquemas oficiales.
Probé tres anchos en un navegador aislado: 1440, 768 y 390 píxeles.
Las comprobaciones finales no encontraron desbordamientos ni datos recortados en la selección inicial.

Contrasté etiquetas y estilos con la documentación de HTML Content Secure.
El contenido del visual usa HTML, SVG y CSS, sin JavaScript ni recursos externos.
La vista previa usa JavaScript para elegir resultados DAX ya calculados.
Contiene tres fechas y tres rutas de ejemplo.
El PBIP ofrece el calendario y el catálogo completos.

La revisión del renderizado dentro de Power BI Desktop sigue pendiente.
Para verla, abro el PBIP actualizado sin sobrescribirlo con el estado anterior de la instancia abierta.
El PBIX anterior conserva el diseño anterior.
El diseño móvil de la vista previa no constituye un diseño móvil nativo de Power BI.
No usé control ni captura de pantalla del escritorio.

## Fuentes y archivos

- [Medidas y definiciones](../../medidas/panorama/README.md).
- [CSS del Panorama](panorama_v2.css).
- [Versión anterior de la vista previa](panorama_preview.html).
- [Biblioteca Power BI Design Files](https://github.com/Dashboard-Design/Power-BI-Design-Files).
- [Patrón de variaciones SVG y HTML](https://github.com/Dashboard-Design/Power-BI-Design-Files/tree/main/SVG%20Visuals/Variance%20Chart%2C%20IBCS%20Style).
- [Etiquetas aceptadas por HTML Content Secure](https://html-content.com/docs/accepted-tags).
- [Sanitización de HTML Content Secure](https://html-content.com/docs/sanitization).

Implementé SVG propios sobre nuestro modelo y conservé las referencias de diseño.
Las cuatro páginas tienen una implementación local; falta comprobar su interacción y renderizado en Desktop.


## Navegación y selección de ruta

Añadí el enlace nativo hacia Programación y grupos sincronizados para A, B, componente y ruta.
La ruta se selecciona mediante una etiqueta de código e ID, conservando route_key como identidad.
La vista previa enlaza [Programación](../programacion/programacion_preview.html) con una selección inicial independiente.
La [definición de negocio de Inicio](../../../docs/power_bi_panorama_negocio.md) relaciona cada visual con su pregunta.


## Navegación hacia Red publicada

Añadí el enlace de vista previa y el botón nativo hacia [Red publicada](../red_publicada/red_publicada_preview.html).
Conservo los cálculos existentes de Panorama.
La página tiene ahora nueve visuales HTML, cuatro selectores y cuatro botones nativos.
Componente y ruta comparten sincronización entre las tres páginas.

## Navegación completa

Añadí el enlace y el botón nativo hacia [Revisión de información](../revision_informacion/revision_preview.html).
Componente y ruta se sincronizan entre las cuatro páginas.
La revisión de navegación real en Desktop sigue pendiente.


## Selector ilustrado de componente

Añadí las tarjetas de Troncal, Zonal (SITP), Alimentación, Dual y TransMiCable a Panorama.
Reutilizo las ilustraciones SVG y la medida `General · Componente ficha HTML` de la página anterior.
Agrupo por componente para mostrar cinco tarjetas, aunque varias agencias pertenezcan a Zonal.
Las ilustraciones identifican componentes; no representan la flota disponible.

Las tarjetas usan el filtrado cruzado de HTML Content sobre los indicadores, el mapa y el selector de ruta de Panorama.
El gráfico de comparación por componente conserva su referencia del sistema, según su definición DAX.
El desplegable de componente conserva su grupo sincronizado entre las cuatro páginas.
Las tarjetas no sincronizan su selección con ese desplegable ni con las otras páginas.
Si el desplegable ya limita el componente, puede limitar también las tarjetas disponibles.
Para explorar las cinco tarjetas, primero dejo el desplegable en todos los componentes.
Los filtros de ruta y componente pueden combinarse; una combinación sin datos no representa un fallo.

Amplié el lienzo de Panorama a 1440 × 1004 para conservar el tamaño de los gráficos.
Las otras páginas mantienen su tamaño.
La vista previa permite seleccionar una tarjeta y pulsarla otra vez para volver a todos los componentes.
Esa vista previa usa JavaScript y resultados DAX ya calculados; la selección nativa depende de HTML Content.
No doy por comprobado el gesto de deselección dentro de Desktop hasta revisarlo allí.

Comprobé las cinco selecciones en anchos de 1440, 768 y 390 píxeles, sin desbordamientos.
Contrasté los conteos por componente con el motor DAX para la fecha inicial.
Validé los 19 archivos PBIR de Panorama contra sus esquemas y revisé las interacciones declaradas.
La comprobación real del filtrado en Power BI Desktop sigue pendiente.

- [CSS del selector](component_selector.css).
- [Ilustraciones obtenidas de la medida DAX](component_selector_data.json).
- [Filtrado cruzado de HTML Content](https://html-content.com/docs/interactivity).


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
