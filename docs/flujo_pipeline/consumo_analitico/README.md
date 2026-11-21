# Mi flujo de consumo analítico

[Abro el diagrama interactivo](consumo_analitico.html).

**Actualización:** 20 de noviembre de 2026.
La [fuente editable](consumo_analitico.dataflow.json) fija el commit 5c23d4e327fb9d90f407dbfc12678623106e4ad6.
Esta vista explica el consumo local implementado; no afirma una publicación en Power BI Service.

## Cómo lo leo

1. Silver proporciona entidades estáticas validadas.
2. Las preguntas de negocio orientan reglas, grano y denominadores.
3. Los publicadores Gold producen cobertura, programación diaria, ruta–ubicación y extremos horarios.
4. Las cuatro tablas Gold de 2026 ya alimentan el modelo local de Power BI.
5. Las medidas DAX responden al contexto de filtros del reporte.
6. Panorama sirve de entrada y se conecta con Programación, Red publicada y Revisión.

El flujo de consumo local ya está implementado; el cierre integral de actualización sigue pendiente.
Las vistas previas actuales utilizan resultados DAX precalculados y sirven para revisar el diseño; no consultan datos en vivo.
No convierto automáticamente el boceto en un archivo PBIX.

## Herramientas de asistencia

El MCP oficial fue probado con un modelo local abierto, en solo lectura y con licencia aceptada.
La conexión actual permitió leer metadata y comprobar las cuatro medidas del menú en el modelo GTFS abierto.
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


## Alcance del estado actualizado

Las referencias de código prueban la implementación comprometida en Git, no una publicación ni un clic.
Las confirmaciones de desarrollo y las definiciones PBIP locales todavía sin commit se explican en el [estado general](../../project_status.md).
El menú nativo ya funciona; la revisión integral, la actualización completa y Service mantienen sus pendientes propios.
