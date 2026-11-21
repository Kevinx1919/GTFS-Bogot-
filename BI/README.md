# Mi informe Power BI de oferta planificada

**Entrega:** v1 local funcional, noviembre de 2026.
El archivo de entrada es [GFTS_BI.pbip](GFTS_BI.pbip).
Las páginas finales son Panorama, Programación, Red publicada y Revisión de información.
El menú nativo ya funciona y distingue la página actual.
El [estado general](../docs/project_status.md) conserva los resultados y las comprobaciones pendientes.

## Abrir una copia nueva

1. Utilizo Power BI Desktop compatible con PBIP y PBIR.
2. Copio GFTS_BI.SemanticModel/definition/expressions.tmdl.example a expressions.tmdl en la misma carpeta.
3. Sustituyo los dos ejemplos por el hostname y la ruta HTTP de mi SQL Warehouse de Databricks.
4. Abro GFTS_BI.pbip, configuro mis credenciales de origen y actualizo las tablas importadas.
5. Compruebo el snapshot disponible y pruebo el menú con Ctrl + clic en Desktop.

Expressions.tmdl contiene solo parámetros locales de conexión y permanece ignorado por Git.
Mi copia de desarrollo ya conserva los valores que utilizaba; no necesito copiarlos otra vez.
Las credenciales pertenecen a la configuración de Power BI, no a los archivos TMDL versionados.
Los nombres de catálogo y schema del modelo corresponden al entorno del proyecto; los adapto si despliego en otro entorno.
No distribuyo datos importados, cachés ni el PBIX anterior.

## Qué contiene la entrega

- [Modelo](modelado/README.md): tablas, identidad, relaciones y filtros.
- [Medidas](medidas/README.md): cálculos numéricos y presentación HTML separados.
- [Recursos y vistas previas](imagenes/README.md): CSS, SVG y resultados DAX precalculados.
- [Consumo](consumo/README.md): campos de negocio e identidad conservada.
- [Navegación y componentes](../docs/power_bi_navigation_images.md): alcance de cada control.
- [Actualización manual](../docs/power_bi_actualizacion_manual.md): recorrido documentado, todavía sin prueba integral registrada.

Las tarjetas ilustradas filtran Panorama; los desplegables sincronizan componente y ruta entre páginas.
Gold prepara hechos y DAX calcula bajo filtros. HTML Content presenta resultados; no ejecuta el JavaScript de las vistas previas.
El reporte describe oferta publicada, sin atribuir operación observada al GTFS estático.


## Comprobaciones de esta entrega

El MCP oficial cargó el modelo local y una copia preparada desde la plantilla pública: 23 tablas, 101 medidas y 21 relaciones.
Pasaron 22 pruebas de contratos Bronze y configuración del Job, sin descargas ni ejecución de Spark.
Comprobé las cuatro páginas, 16 destinos nativos, enlaces del README y hashes de los seis diagramas.
En 58 archivos PBIR utilicé su esquema publicado; otros once tienen la envoltura 2.14 de Desktop, cuyo esquema público devolvió 404.
Para esos once comprobé estructura compatible, JSON y referencias, sin afirmar una validación contra el esquema 2.14 no disponible.
Esta comprobación no sustituye la revisión integral de filtros ni una actualización completa con datos.
