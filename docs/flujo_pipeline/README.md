# Mi documentación visual del proyecto GTFS

Uso esta carpeta para explicar el proyecto mediante diagramas interactivos y páginas de lectura. Mantengo los contratos de datos y el runbook como referencias de las reglas y los procedimientos; los mapas enlazarán esas fuentes en lugar de repetir todo su contenido.

## Qué puedo explorar

| Documento | Pregunta que responde | Alcance |
| --- | --- | --- |
| [Mapa del lakehouse](mapa_lakehouse/README.md) | ¿Dónde están los datos y cómo avanzan entre capas? | Raw, Staging, Bronze y Silver actuales; Gold y Power BI identificados como futuros. |
| [Recorrido del Job Silver](job_silver/README.md) | ¿Qué ocurre al pulsar Run now y qué pasa ante un error? | Agency y routes, parámetros por snapshot, validación, publicación, auditoría y recuperación. |
| [Modelo GTFS](modelo_gtfs/README.md) | ¿Cómo se relacionan las entidades y cómo preservo cada snapshot? | Empiezo con agency y routes; ampliaré las vistas al incorporar las demás entidades. |

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

La herramienta está instalada y los cinco HTML de los tres documentos están generados, con fuentes JSON, controles automáticos y revisión de capturas en ambos temas. Conservo esta documentación en el repositorio; no publiqué un sitio web. Las comprobaciones de los diagramas no son ejecuciones del pipeline en Databricks.

Para evitar un problema de reemplazo de archivos de control en OneDrive genero en una carpeta temporal fuera de la sincronización y publico copias byte a byte de los HTML comprobados. Conservo en el proyecto un resumen público de verificación; los controles de entrega y recuperación locales quedan excluidos de Git.

Referencias: [Archify](https://github.com/tt-a1i/archify), [skill](https://github.com/tt-a1i/archify/blob/a4065941f12be7967436261d9934784e381d423c/archify/SKILL.md), [guía operativa Silver](../silver_execution.md) y [contratos](../contracts).
