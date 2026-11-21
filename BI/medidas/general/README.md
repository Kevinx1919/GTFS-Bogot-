# Medidas de presentación de General

Preparé la primera página del reporte el 19 de noviembre de 2026.
Guardé nueve medidas HTML en `Presentación HTML/General`, dentro de `gold_gtfs_trip_coverage`.
Conservé las medidas numéricas como fuente de los cálculos.
El HTML presenta esos resultados; no reemplaza las reglas de negocio Gold.

| Archivo | Función |
| --- | --- |
| [01_encabezado_html.dax](01_encabezado_html.dax) | Identifica el snapshot, la agencia y el hallazgo actual. |
| [02_navegacion_html.dax](02_navegacion_html.dax) | Presenta la identidad y las secciones previstas. |
| [03_indicadores_html.dax](03_indicadores_html.dax) | Presenta rutas, viajes declarados y plantillas por frecuencia. |
| [04_agencia_fila_html.dax](04_agencia_fila_html.dax) | Dibuja una barra por agencia con su cantidad de viajes. |
| [05_cobertura_html.dax](05_cobertura_html.dax) | Presenta las tres categorías de cobertura de visitas. |
| [06_rutas_revision_html.dax](06_rutas_revision_html.dax) | Ordena tres rutas por viajes sin visitas publicadas. |
| [07_contexto_html.dax](07_contexto_html.dax) | Explica la identidad del snapshot y los límites del análisis. |

## Contexto de filtros

Usé filtros nativos de snapshot, agencia y ruta.
Las relaciones del modelo transmiten esos filtros a las medidas numéricas.
Configuré `samplingContext` con la clave de agencia, su nombre y su versión para las barras HTML.
Activé el cruce de filtros del visual HTML Content Secure.
La comprobación de ese gesto dentro de Desktop sigue pendiente de abrir el PBIP.

Las barras comparan viajes declarados; no representan buses disponibles ni viajes ejecutados.
La escala conserva el máximo visible y los valores cero.
Los porcentajes conservan su denominador dentro del contexto seleccionado.
No uní agencias históricas por su ID sin incluir el snapshot.
Conservé los nombres de agencia publicados; la agrupación por componente todavía requiere aprobación.

## Ausencias y alcance

Gold contiene la evaluación publicada para 2026.
Para 2025 mostré rutas y viajes del catálogo Silver.
Mostré un guion y una explicación cuando falta evaluación Gold.
No convertí esa ausencia en cero.
Varias visitas publicadas no certifican que un recorrido esté completo.
Un viaje sin visitas tampoco demuestra una cancelación real.

## Comprobaciones

Ejecuté las nueve medidas con ambos snapshots y sus siete agencias.
Añadí contextos de componentes y rutas para obtener 31 estados DAX reales.
Comprobé 1.045 rutas, 181.060 viajes, 739 viajes sin visitas y 61 viajes con una visita para 2026.
Comprobé 14 viajes declarados de TransMiCable.
Conservé las definiciones en TMDL y los archivos DAX para revisión.

## Rediseño por componente

Añadí [08_componente_ficha_html.dax](08_componente_ficha_html.dax) para las fichas ilustradas con Context por componente.
Añadí [09_transporte_html.dax](09_transporte_html.dax) para la ilustración y explicación del componente seleccionado.
Los indicadores ahora presentan rutas, viajes y plantillas por frecuencia.
El anillo reúne las categorías de cobertura; su denominador queda visible.
Las rutas para revisar incorporan una barra proporcional al porcentaje de casos.
Conservé las medidas numéricas de cobertura y las ausencias de 2025.
La columna [report_component](../../modelado/report_component.dax) transmite la selección a las relaciones existentes.
