# General por componente: segunda versión

Retomé el boceto de General y las referencias visuales el 19 de noviembre de 2026.
La pregunta es: **¿qué oferta publica cada componente y qué casos requieren revisar el dato?**

[Abrir la vista previa interactiva](general_preview.html).

## Qué cambié

- Recuperé la selección visual de Troncal, Zonal (SITP), Alimentación, Dual y TransMiCable.
- Añadí una ficha que cambia su ilustración y descripción según el componente.
- Usé el rojo #DD212C y el amarillo #FFC928 como referencia visual del bus compartido.
- Conservé el azul y el verde en las ilustraciones zonal y alimentadora para reconocer sus identidades.
- Organicé los indicadores a la izquierda de la ficha.
- Dibujé un anillo de cobertura, barras por agencia y barras proporcionales en las rutas para revisar.
- Conservé la navegación izquierda y los filtros superiores de snapshot, componente y ruta.

Elegí esta selección para **General**, como planteaba el boceto.
Programación explicará días y ventanas; Red publicada explicará ubicaciones; Calidad ofrecerá el detalle técnico.
Esas tres páginas todavía están en preparación.
No incorporé los fixtures DEMO del boceto al reporte real.

## Componente y modelo

Añadí `report_component` en agency y su columna oculta de orden.
Usé una correspondencia explícita de nombres publicados, sin reutilizar agency_id entre snapshots.
Agrupé Urbana, Complementaria y Especial bajo Zonal (SITP).
Conservé Alimentación y Dual como grupos separados.
La clasificación sirve para presentación analítica; no representa operadores ni contratos.
Los nombres desconocidos quedan Sin clasificar.
Las relaciones existentes transmiten el filtro a rutas, viajes, frecuencias y cobertura Gold.
No añadí relaciones ni dupliqué tablas de hechos.

El [informe del modelo](../../../docs/power_bi_model_review_2026_11_19.md) explica las decisiones y comprobaciones.
Las [medidas HTML](../../medidas/general/README.md) conservan los cálculos numéricos existentes.

## Archivos y funcionamiento

- `general.css`: estilos compartidos con nueve visuales HTML.
- `general_preview.html`: vista previa independiente, con controles equivalentes.
- `general_preview_data.json`: 31 contextos consultados con DAX, sin cifras inventadas.
- `assets/`: seis ilustraciones SVG propias y su procedencia.
- `model_review_checks.json`: resultados de las comprobaciones del modelo.
- `decisiones_diseno.md`: composición, paleta y límites.

JavaScript solo elige resultados DAX ya consultados en la vista previa.
No consulta Databricks ni recalcula el modelo.
La vista previa ofrece tres rutas de ejemplo; el selector nativo usa el catálogo completo.
Power BI recalcula las medidas con el contexto real.
No trasladé JavaScript al visual seguro.

Los controles superiores y la navegación son nativos.
Configuré las fichas HTML con Context y `crossFilter` para que Power BI reconozca el componente seleccionado.
Conservé ese contexto también en las barras de agencias.
La interacción efectiva de los visuales personalizados dentro de Desktop requiere reabrir y comprobar el PBIP.
La [guía oficial de HTML Content](https://html-content.com/docs/pbir-guide) documenta su contrato PBIR.
Su [guía de interacción](https://html-content.com/docs/interactivity) explica la necesidad del contexto por fila.

## Datos y límites

En 2026 comprobé 1.045 rutas y 181.060 viajes declarados.
TransMiCable tiene 1 ruta y 14 viajes declarados en este snapshot.
Zonal reúne 725 rutas y 106.023 viajes declarados.
Las cinco agrupaciones concilian con los totales del sistema.
El dato sigue representando oferta publicada, no buses físicos ni viajes ejecutados.

Para 2025 conservé el catálogo y señalé la ausencia de evaluación Gold.
El anillo no presenta esa ausencia como cero.
Las ilustraciones no representan flota, geometría real ni una cantidad de vehículos.
El esquema conjunto no es un mapa geográfico.

## Comprobar dentro de Power BI

1. Conservo los archivos actuales del proyecto PBIP.
2. Cierro la sesión anterior sin sobrescribir las definiciones externas con una versión anterior.
3. Abro `BI/GFTS_BI.pbip` y entro en General.
4. Cambio el componente en el filtro nativo y compruebo ficha, indicadores y cobertura.
5. Pruebo la selección mediante una ficha HTML y una barra de agencia.
6. Si la selección cruzada necesita limpieza, uso la deselección del visual y el filtro nativo.
7. Pruebo 2025 y confirmo la ausencia de Gold.

El PBIX anterior no incorpora estas modificaciones del PBIP.
La adaptación móvil pertenece a la vista previa; la página PBIR conserva 1.440 × 900 píxeles.
