# Mi revisión del modelo y de General por componente

**Fecha:** 19 de noviembre de 2026.
**Herramienta:** power-bi-model-design-review, aplicada al modelo local GFTS_BI mediante MCP.
**Alcance:** arquitectura, propagación de filtros, clasificación de componentes y consumo de cobertura Gold.

## Resultado

Conservé diecinueve tablas y diecisiete relaciones.
Doce tablas pertenecen al modelo de negocio; siete son objetos automáticos de fechas.
Todas las relaciones existentes conservan dirección única y cardinalidad muchos a uno.
El almacenamiento sigue en Import.
No identifiqué bloqueos en las claves, relaciones y conciliaciones comprobadas.
Esta revisión no sustituye una prueba de rendimiento o de actualización completa.

## Cambio que necesitaba el diseño

La selección visual necesitaba un campo semántico para transmitir el filtro.
Añadí `report_component` y la columna oculta `report_component_order` en agency.
Ambas columnas usan los nombres fuente de forma explícita.
El orden no depende de la columna que ordena, para evitar dependencias circulares.
Conservé las claves compuestas por snapshot y los IDs originales.
No cambié tablas Bronze, Silver ni Gold en Databricks.

| Nombres publicados, sin distinguir mayúsculas | Agrupación analítica |
| --- | --- |
| Transmilenio-Troncal | Troncal |
| Zonal-Urbano; Zonal-Complementario; Zonal-Especial; TRANSMILENIO-URBANA; TRANSMILENIO-COMPLEMENTARIA; TRANSMILENIO-ESPECIAL | Zonal (SITP) |
| Transmilenio-Alimentadores; TRANSMILENIO-ALIMENTADORA | Alimentación |
| Transmilenio-Dual | Dual |
| TransMiCable; CABLE | TransMiCable |
| Cualquier otro nombre | Sin clasificar |

Esta clasificación es de presentación analítica.
No representa empresas, contratos ni una delimitación oficial de componentes.
SITP nombra el sistema integrado; uso Zonal (SITP) para evitar presentarlo como excluyente del cable.
Conservo Dual separado para no esconder una decisión de agrupación.
Un nuevo nombre requiere revisión y queda visible como Sin clasificar.

## Flujo del filtro

El componente filtra agency, después routes, trips, frequencies y gold_gtfs_trip_coverage.
La dimensión snapshot conserva versión y hash en ese recorrido.
No añadí caminos paralelos desde Gold hacia agency o snapshot.
No conecté agency directamente con stops.
La página no presenta ubicaciones por componente hasta disponer de un puente de negocio compatible.
El calendario tampoco convierte automáticamente viajes del catálogo en salidas activas por fecha.

## Comprobaciones del modelo

Comprobé ambos snapshots y las siete agencias de cada uno.
No encontré nombres sin clasificar en esas catorce filas.
No encontré claves agency_key ni trip_key Gold duplicadas.
No encontré claves huérfanas routes→agency, trips→routes o cobertura→trips.
Concilié la suma de rutas y viajes por componente con el total del sistema.
Las diferencias fueron cero.
En las comprobaciones COUNTROWS, un resultado nulo representa un conjunto vacío.
Conservé la salida original en [model_review_checks.json](../BI/imagenes/general/model_review_checks.json).

| Componente | Rutas 2026 | Viajes declarados 2026 |
| --- | ---: | ---: |
| Troncal | 113 | 40.599 |
| Zonal (SITP) | 725 | 106.023 |
| Alimentación | 175 | 29.454 |
| Dual | 31 | 4.970 |
| TransMiCable | 1 | 14 |
| Total | 1.045 | 181.060 |

Para 2025, Troncal y Dual no tienen rutas relacionadas en el catálogo importado.
No rellené esas ausencias con datos de 2026.
La cobertura Gold sigue disponible únicamente para 2026.

## Recomendaciones priorizadas

**Resuelto ahora:** clasificación explícita, orden de presentación, conservación del contexto histórico y selección por componente.
Las fichas HTML incluyen Context por componente; los indicadores reutilizan medidas numéricas.
Conservé descripciones y carpetas de medidas.

**Siguiente validación:** abrir el PBIP y comprobar el renderizado y la selección cruzada del visual instalado.
Validé PBIR y las interacciones de la vista previa independiente.
Esa prueba no demuestra automáticamente el comportamiento del host Power BI.

**Mejora posterior:** revisar las seis tablas automáticas de fechas cuando estabilice los filtros temporales.
No las eliminé durante un rediseño visual.
El modelo conserva una dimensión de fecha explícita.

**Crecimiento posterior:** evaluar claves sustitutas enteras y agregaciones si aumentan los snapshots y el volumen importado.
No cambié claves de texto por una suposición de rendimiento.
El recorrido agency→routes→trips es un copo de nieve justificado por los catálogos fuente actuales.
Podré simplificarlo cuando termine los productos Gold de consumo.

No medí memoria, concurrencia ni tiempos de actualización completa.
No realicé una auditoría de permisos o RLS.
Los datos analizados son el catálogo público del proyecto, sin una necesidad de seguridad por usuario definida.

## Archivos y recuperación

Guardé las definiciones oficiales del modelo en TMDL y las nueve medidas HTML en archivos DAX.
La [vista previa](../BI/imagenes/general/general_preview.html) contiene 31 estados DAX.
Conservé una copia de las definiciones anteriores en una carpeta temporal antes de editar.
El PBIX anterior permanece separado del PBIP actualizado.
