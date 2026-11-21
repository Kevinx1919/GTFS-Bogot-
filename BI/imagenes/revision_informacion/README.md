# Revisión de información: mi cuarto panel

**Estado:** implementación guardada en PBIP y comprobada en DAX y en la vista previa.
La revisión del renderizado y de las interacciones reales dentro de Desktop sigue pendiente.

[Abro la vista previa](revision_preview.html).
[Leo la explicación de negocio](../../../docs/power_bi_revision_negocio.md).

Quiero localizar viajes que necesitan contexto antes de analizar sus horarios.
Uso cobertura y extremos horarios Gold del catálogo 2026.
No interpreto los motivos como cancelaciones, incumplimientos ni operación observada.

## Cómo recorro el panel

1. Elijo componente y ruta.
2. Leo los totales del contexto y la clasificación horaria.
3. Selecciono un motivo para filtrar el ranking y la tabla.
4. Consulto un viaje y leo qué representa y qué información revisaría después.

Las cantidades superiores y la clasificación conservan el contexto anterior al motivo.
El ranking muestra hasta cinco rutas, sus cantidades y sus porcentajes sobre el total de cada ruta.
La tabla nativa muestra todos los viajes del contexto excluidos del perfil horario.
Una fila actualiza solamente la ficha Siguiente revisión.
No cambia las cantidades ni los filtros superiores.

## Archivos

- revision.css conserva los estilos propios de la página.
- revision_preview.html combina el marco compartido y los resultados de la vista previa.
- revision_preview_data.json conserva 70 contextos reales calculados por DAX.
- [Medidas](../../medidas/revision_informacion/README.md) separa cálculos y presentación.
- [Plan](../../../docs/power_bi_revision_plan.md) conserva las decisiones de implementación.

La página PBIR contiene ocho visuales HTML, tres selectores, una tabla nativa y cuatro botones de navegación.
Componente y ruta comparten sincronización con las otras tres páginas.
El motivo pertenece a esta página; las fechas A y B no filtran este catálogo.
El modelo conserva 23 tablas y 21 relaciones físicas.
Añadí dos columnas de presentación y veinte medidas a trip_timing.
No modifiqué las tablas de Databricks.

## Comprobaciones

Concilié 181.060 viajes: 180.246 elegibles y 814 excluidos del perfil horario.
Los excluidos son 739 sin visitas, 61 con una visita y 14 plantillas.
Contrasté las cantidades de cero y una visita contra cobertura Gold.
La consulta de la tabla nativa devolvió los 814 viajes esperados.
Seleccionar Sin visitas mantiene el denominador de 181.060 y devuelve 739 casos.
2025 sin estas Gold conserva ausencia de evaluación; no genera ceros ficticios.
Las fechas A y B no cambian los resultados del catálogo.

La vista previa permite cinco componentes, cuatro rutas de ejemplo y motivos con o sin casos.
Su botón consulta la ficha del primer caso; la tabla nativa permite elegir cualquier fila.
El HTML de Power BI usa CSS sin JavaScript; los controles nativos realizan las interacciones del informe.
La vista previa usa JavaScript para elegir resultados DAX ya calculados.

Comprobé setenta contextos y sus combinaciones en 1440, 768 y 390 píxeles.
La adaptación de la vista previa no sustituye un diseño móvil nativo de Power BI.
Validé los esquemas PBIR de las cuatro páginas y sus visuales.
Las mediciones del motor no representan tiempos garantizados del informe completo.

## Cómo lo reviso en Desktop

Abro BI/GFTS_BI.pbip y consulto Revisión de información.
Evito sobrescribir las definiciones nuevas desde una sesión que conserve un diseño anterior.
Pruebo un componente sin casos, TransMiCable, un motivo y una fila de la tabla.
Compruebo que esa fila solo cambie su ficha.
Reviso también la navegación hacia Panorama, Programación y Red publicada.
El PBIX anterior conserva su diseño anterior.


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
