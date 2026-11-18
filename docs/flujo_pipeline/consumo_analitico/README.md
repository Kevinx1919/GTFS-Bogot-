# Mi flujo de consumo analítico

[Abro el diagrama interactivo](consumo_analitico.html).

**Actualización:** 18 de noviembre de 2026.
La [fuente editable](consumo_analitico.dataflow.json) fija el commit 6c4490fd2846d8afeb70ee08f02d4680d535b76e.
Esta vista explica responsabilidades y estados; no representa un reporte ya publicado.

## Cómo lo leo

1. Silver proporciona entidades estáticas validadas.
2. Las preguntas de negocio orientan reglas, grano y denominadores.
3. El procesador Gold de cobertura tiene implementación local y pruebas; su publicación sigue pendiente.
4. Las futuras tablas Gold alimentarán el modelo de Power BI.
5. Las medidas DAX responderán al contexto de filtros del reporte.
6. Inicio y cuatro páginas analíticas utilizan preguntas candidatas documentadas.

El flujo de datos hacia Power BI permanece propuesto.
El boceto HTML usa fixtures explícitamente ilustrativos y sirve para revisar navegación y distribución.
No convierto automáticamente el boceto en un archivo PBIX.

## Herramientas de asistencia

El MCP oficial fue probado con un modelo local abierto, en solo lectura y con licencia aceptada.
Eso no demuestra que exista un modelo GTFS ni una conexión a las futuras tablas Gold.
La habilidad Power BI del navegador puede trabajar el editor web según permisos y controles disponibles.
Todavía no comprobé esa cuenta web.
Ninguna de las dos herramientas sustituye las transformaciones del pipeline Databricks.

## Preguntas y fuentes

- [Historias de negocio](../../power_bi_user_stories.md).
- [Plan de cierre Gold](../../gold_plan.md).
- [Contrato de cobertura](../../contracts/trip_coverage.md).
- [Navegación, componentes e imágenes](../../power_bi_navigation_images.md).
- [Reparto Gold/DAX y conexión MCP](../../powerbi_mcp_setup.md).

El [resumen público de verificación](verificacion.json) registra la comprobación automatizada y los hashes.
Los controles del diagrama no ejecutan Jobs ni consultan modelos.
