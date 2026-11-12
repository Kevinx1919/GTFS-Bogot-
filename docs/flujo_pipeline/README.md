# Mi documentación visual del proyecto GTFS

Uso esta carpeta para explicar el proyecto mediante diagramas interactivos y páginas de lectura. Mantengo los contratos de datos y el runbook como referencias de las reglas y los procedimientos; los mapas enlazarán esas fuentes en lugar de repetir todo su contenido.

## Qué puedo explorar

| Documento | Pregunta que responde | Alcance |
| --- | --- | --- |
| [Mapa del lakehouse](mapa_lakehouse/README.md) | ¿Dónde están los datos y cómo avanzan entre capas? | Raw, Staging, Bronze y Silver actuales; Gold y Power BI identificados como futuros. |
| [Recorrido del Job Silver](job_silver/README.md) | ¿Qué ocurre al pulsar Run now y qué pasa ante un error? | Nueve tareas, parámetros por snapshot, validación, publicación, auditoría y recuperación. |
| [Modelo GTFS](modelo_gtfs/README.md) | ¿Cómo se relacionan las entidades y cómo preservo cada snapshot? | Nueve tablas físicas y dos catálogos lógicos; stop_times continúa como siguiente contrato. |

Puedo empezar directamente por el [mapa del lakehouse](mapa_lakehouse/mapa_lakehouse.html), el [orden del Job](job_silver/recorrido_job.html), el [interior de una iteración](job_silver/iteracion_snapshot.html), el [modelo Silver actual](modelo_gtfs/modelo_silver.html) o el [panorama GTFS](modelo_gtfs/panorama_gtfs.html).

Es como tener un mapa de una estación: primero ubico las zonas y después abro el detalle del recorrido que necesito. Esta comparación explica el propósito; no es una observación de los datos.

## Instalación y requisitos

Instalé Archify **3.2.0** como skill local de Codex, fuera del repositorio, desde el commit [a4065941f12be7967436261d9934784e381d423c](https://github.com/tt-a1i/archify/tree/a4065941f12be7967436261d9934784e381d423c/archify). Usé el instalador de skills de Codex para conservar una revisión concreta. No instalé un servicio ni añadí dependencias a Databricks.

Comprobé Node.js 22.18.0, que cumple el requisito mínimo de Node 18, y la disponibilidad de Chrome y Edge. El comando doctor de Archify terminó correctamente: encontró plantillas, renderizadores, esquemas, validadores y referencias para los tipos soportados. Ese diagnóstico verifica la instalación; la comprobación de cada diagrama se registra por separado en su subcarpeta.

Para comprobar otra instalación puedo ejecutar:

```text
node <ruta-local-de-la-skill>/bin/archify.mjs doctor
```

La ruta de instalación pertenece a cada equipo y no la codifico dentro del proyecto. Archify se usa desde el equipo de documentación; los lectores abrirán el HTML generado en su navegador. No necesito credenciales de Databricks para generar documentación basada en el código y los contratos.

## Cómo guardaré cada documento

Cada subcarpeta contendrá la fuente editable, el HTML generado y una descripción breve. En un diagrama nativo la fuente será JSON; para una página explicativa podrá ser Markdown de Archify. Guardaré la evidencia pública necesaria de validación sin rutas personales, credenciales ni datos de ejecución privados; los registros locales detallados permanecerán fuera de Git.

Antes de generar fijo el commit del código que voy a explicar. Si hay cambios sin commit, los distingo de la evidencia del commit y no los presento como parte de esa revisión. Los diagramas deben separar implementado, comprobado en ejecución y pendiente.

Ya creé los tres documentos: el mapa del lakehouse, el recorrido del Job Silver con dos vistas y el modelo GTFS con el ERD actual y su panorama de crecimiento. Conservo español y explicaciones breves. Cuando cambie una responsabilidad o relación del pipeline, revisaré el mapa afectado junto con el cambio de código.

## Estado de esta preparación

La herramienta está instalada. Actualicé los cinco HTML con sus fuentes JSON y controles automáticos de navegador. No atribuyo las capturas anteriores a esta revisión nueva. Conservo esta documentación en el repositorio; no publiqué un sitio web. Las comprobaciones de los diagramas no son ejecuciones del pipeline en Databricks.

Para evitar un problema de reemplazo de archivos de control en OneDrive genero en una carpeta temporal fuera de la sincronización y publico copias byte a byte de los HTML comprobados. Conservo en el proyecto un resumen público de verificación; los controles de entrega y recuperación locales quedan excluidos de Git.

Referencias: [Archify](https://github.com/tt-a1i/archify), [skill](https://github.com/tt-a1i/archify/blob/a4065941f12be7967436261d9934784e381d423c/archify/SKILL.md), [guía operativa Silver](../silver_execution.md) y [contratos](../contracts).


## Estado actualizado tras frequencies_v1

Actualicé las cinco vistas el 12 de noviembre de 2026.
Las nueve entidades tienen despliegue funcional confirmado durante el desarrollo.
El modelo conserva todas sus 135 columnas físicas. Distingue dos catálogos lógicos que no son tablas persistidas.
El recorrido muestra las nueve tareas y separa dependencias operativas de relaciones entre tablas.
El mapa distingue ocho entidades fuente y service_dates derivada, limitada a 2026.

Los enlaces de evidencia fijan el código de 34e3769e1d6eaebca950161f4f47f0bf38f7bc40.
El cierre de ejecución y esta actualización documental son cambios posteriores todavía locales.
Actualicé guías Markdown, fuentes JSON, HTML y resúmenes; no modifiqué el pipeline ni ejecuté Jobs.
El siguiente contrato es stop_times. Gold y el planificador automático permanecen pendientes.

Las cinco vistas pasaron comprobaciones automáticas de navegador.
Los resúmenes distinguen esos controles de una revisión visual de capturas, que no repetí para esta revisión.
El ERD denso utiliza el perfil standard para conservar todos los campos.
