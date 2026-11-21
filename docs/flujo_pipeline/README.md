# Mi documentación visual del proyecto GTFS

**Actualización:** 20 de noviembre de 2026.
Uso Archify para explicar responsabilidades y recorridos; los contratos y el runbook conservan las reglas completas.
Los HTML funcionan como documentación interactiva local, no como dashboards conectados a los datos.

## Qué puedo explorar

| Documento | Pregunta | Estado de esta revisión |
| --- | --- | --- |
| [Mapa del lakehouse](mapa_lakehouse/mapa_lakehouse.html) | ¿Dónde están los archivos y cómo llego a Power BI? | Actualizado con cuatro Gold y consumo local. |
| [Recorrido del Job Silver](job_silver/recorrido_job.html) | ¿Qué ejecuta el planificador y en qué orden? | Mantengo el flujo validado; no cambiaron sus responsabilidades. |
| [Una iteración Silver](job_silver/iteracion_snapshot.html) | ¿Qué ocurre si la entidad pasa, se rechaza o falla? | Mantengo el flujo validado de auditoría, cuarentena y publicación. |
| [Modelo Silver](modelo_gtfs/modelo_silver.html) | ¿Cómo preservo claves y referencias por snapshot? | Diez tablas físicas y dos catálogos lógicos; sin cambios de esquema. |
| [Panorama GTFS](modelo_gtfs/panorama_gtfs.html) | ¿Qué está implementado y qué queda fuera? | Actualizado con Gold, Power BI y pendientes del cierre. |
| [Consumo analítico](consumo_analitico/consumo_analitico.html) | ¿Qué calculan Gold, DAX y los visuales? | Actualizado con cuatro paneles, menú nativo y filtros. |

El [estado general](../project_status.md) es el punto de entrada para cifras y pendientes vigentes.
El [plan de cierre](../power_bi_cierre_v1.md) distingue revisión de navegación y aceptación integral.

## Qué cambió en el consumo

Publiqué e importé trip_coverage, route_service_day, route_stop y trip_timing para 2026.
El reporte contiene Panorama de oferta, Programación, Red publicada y Revisión de información.
Panorama cumple también la función de entrada.
El menú usa botones nativos con texto propio y resalta la página actual en rojo suave.
Retiré Laboratorio y los accesos a páginas de prueba del menú principal.
El HTML del lateral no dibuja etiquetas de navegación duplicadas.
La revisión del informe confirmó que la navegación funciona.

Las tarjetas de vehículos filtran únicamente Panorama.
Los desplegables sincronizan componente y ruta entre las cuatro páginas.
No confundo el componente de presentación con un operador contractual ni con una clave histórica estable.
No presento programación publicada como operación observada.

## Qué conserva cada carpeta

Guardo la fuente JSON, el HTML generado, una explicación y un resumen público de verificación.
La herramienta está instalada como skill local de Codex; no necesito credenciales de Databricks para generar estos diagramas.
El lector abre los HTML con un navegador y puede explorar las vistas disponibles.
No publiqué un sitio web ni incorporé estas animaciones al motor del pipeline.

## Código, estado de desarrollo y comprobaciones

Los tres diagramas revisados fijan referencias de código al commit 5c23d4e327fb9d90f407dbfc12678623106e4ad6.
Las confirmaciones de publicación y navegación son evidencia de desarrollo registrada en la documentación.
No atribuyo las definiciones PBIP locales todavía sin commit a ese commit del código.
El ERD y los dos workflows Silver mantienen su revisión 6c4490fd2846d8afeb70ee08f02d4680d535b76e porque su contenido no cambió.

Genero los tres HTML nuevos fuera de OneDrive y copio los bytes comprobados al proyecto.
Los resúmenes públicos identifican archivos, hashes y controles de esta revisión.
Los recibos completos y las rutas del entorno quedan fuera de Git.
Los tres HTML que no cambiaron conservan su evidencia anterior; no les atribuyo una prueba nueva.
Las comprobaciones de Archify no ejecutan Jobs ni certifican filtros de Power BI.

## Qué sigue pendiente

La revisión integral de filtros y rendimiento, el recorrido completo de actualización y la entrega del portafolio siguen abiertos.
El coordinador termina en Silver; Gold y Power BI conservan pasos manuales.
El feed nuevo, Power BI Service y las fuentes observadas siguen fuera de lo comprobado.

[Archify](https://github.com/tt-a1i/archify) · [Contratos](../contracts) · [Ejecución Silver](../silver_execution.md) · [Guía del menú](../power_bi_navigation_images.md).
