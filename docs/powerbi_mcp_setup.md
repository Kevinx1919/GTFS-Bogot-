# Mi conexión entre Codex y Power BI

> **Estado vigente — 20 de noviembre de 2026:** las cuatro Gold de 2026 están publicadas e importadas y los cuatro paneles están implementados. La navegación nativa funciona; la revisión integral y la actualización completa siguen pendientes. [Estado actual](project_status.md).

## Registro de diseño e implementación

Conservo a continuación las decisiones y comprobaciones de cada etapa. Los pendientes de esas fechas describen su momento; el estado vigente anterior los sustituye.

**Fecha de comprobación:** 17 de noviembre de 2026.
**Estado:** licencia aceptada y conexión al modelo local probada en solo lectura.
**Actualización documental:** 18 de noviembre de 2026.

## Cómo reparto los cálculos

Gold prepara datos de negocio reutilizables y conserva reglas, identidad y procedencia.
Power BI calcula medidas DAX según el contexto de filtros del reporte.
No necesito materializar cada combinación de filtros como una tabla Gold.

| Responsabilidad | Ejemplo del proyecto |
| --- | --- |
| Gold en Databricks | Clasificar cada viaje declarado según su cantidad de visitas y su contexto de frecuencia. |
| Gold en Databricks | Construir programación por ruta y fecha, con criterios y reconciliación definidos. |
| Modelo de Power BI | Relacionar dimensiones y hechos mediante claves compatibles, incluyendo snapshot. |
| Medidas DAX | Contar viajes declarados del componente seleccionado y calcular su porcentaje sin visitas. |
| Visuales de Power BI | Mostrar tarjetas, mapas, tablas, filtros e imágenes con los resultados. |

Por ejemplo, Gold puede conservar una fila por viaje declarado con coverage_status y visit_count.
Power BI puede contar las filas sin_visitas dentro de la ruta y el snapshot seleccionados.
El porcentaje divide ese conteo entre todos los viajes declarados del mismo contexto.
El denominador elimina solo el filtro de cobertura cuando corresponde; conserva ruta, componente y snapshot.
Un denominador cero produce ausencia analítica, no un porcentaje inventado.
El contrato del indicador fijará ese comportamiento antes de implementar la medida definitiva.

Las [opciones de cálculo de Microsoft](https://learn.microsoft.com/en-us/power-bi/transform-model/desktop-calculations-options) explican las medidas dependientes de filtros.
El HTML usa fixtures de diseño; no ejecuta medidas DAX ni consume tablas Gold reales.
La [ficha de cobertura](contracts/trip_coverage.md) describe el procesador local existente y su publicación pendiente.

## Qué permite este MCP

Revisé el [repositorio oficial de Microsoft](https://github.com/microsoft/powerbi-modeling-mcp).
El servidor se presenta actualmente como Power BI Authoring MCP Server.
Permite trabajar con modelos de Power BI Desktop, modelos de Fabric y archivos PBIP/TMDL compatibles.
Puede consultar metadata, validar DAX y gestionar medidas, tablas, columnas y relaciones cuando el modo permite escritura.
No modifica páginas del reporte ni la distribución visual de sus elementos.
No convierte automáticamente el HTML en un PBIX.

Para esta comprobación uso Power BI Desktop local.
No necesito incorporar una clave de OpenAI al servidor para conectarlo con Codex.
Una conexión local al modelo de Desktop no sustituye las credenciales de sus fuentes de datos.
La conexión a Databricks y los permisos de cada fuente tendrán su configuración independiente.

## Qué encontré y qué reparé

Había una entrada powerbi-modeling-mcp en la configuración personal de Codex.
Apuntaba a una extensión 0.4.0 cuyo ejecutable ya no existía.
Encontré instalada la extensión oficial analysis-services.powerbi-modeling-mcp, versión 1.0.1 para Windows x64.
Su ejecutable existe y respondió correctamente a --help.
No necesité descargar ni instalar otra copia.

Actualicé solo el comando de ese servidor y añadí --start y --readonly.
Conservé los otros servidores y ajustes.
Guardé una copia local de config.toml antes del cambio y validé la sintaxis TOML.
No guardo esa configuración personal ni su copia en Git.

La [configuración MCP de Codex](https://developers.openai.com/codex/mcp/) admite servidores locales por stdio.
El siguiente ejemplo es una plantilla; sustituyo la ruta por el ejecutable instalado:

```toml
[mcp_servers.powerbi-modeling-mcp]
command = 'RUTA_ABSOLUTA_DE_LA_EXTENSION\server\powerbi-modeling-mcp.exe'
args = ["--start", "--readonly"]
startup_timeout_sec = 30
```

No codifico rutas personales en módulos reutilizables del proyecto.
Una actualización de la extensión puede cambiar la ruta y exigir revisar el registro nuevamente.

## Qué comprobé realmente

- Codex CLI reconoce la entrada reparada como habilitada y por stdio.
- El servidor inicializa como powerbi-authoring-local, versión 1.0.1.
- La respuesta tools/list anuncia 22 herramientas.
- Power BI Desktop y su motor local están ejecutándose.
- La aceptación explícita de la licencia quedó registrada mediante accept_eula.
- Un proceso nuevo detectó una instancia local sin volver a solicitar la aceptación.
- Connect estableció una conexión local de solo lectura; ListConnections confirmó su presencia.
- Cerré únicamente la conexión de diagnóstico mediante Disconnect al terminar.

Distingo el arranque del servidor de la conexión al modelo.
La conexión al modelo quedó probada y después cerrada al terminar el diagnóstico.
No inspeccioné tablas, medidas ni datos del modelo durante esta comprobación.
No publiqué modelos, inicié actualizaciones de datos ni modifiqué relaciones.

## Licencia: aceptación explícita completada

El [README oficial](https://github.com/microsoft/powerbi-modeling-mcp#accept-the-eula) exige aceptación explícita de la licencia.
La herramienta accept_eula también prohíbe que un agente la ejecute automáticamente.
Revisé la [licencia oficial](https://go.microsoft.com/fwlink/?LinkId=2381247) y autoricé explícitamente su aceptación.
La herramienta confirmó la aceptación y todas las herramientas quedaron disponibles para el modo configurado.
No necesité añadir --accepteula ni una variable equivalente a la configuración.
La aceptación quedó persistida y la comprobé desde un proceso nuevo.
Conservo documentado el bloqueo inicial y su resolución.

## Uso después de la prueba de conexión

1. Mantengo Power BI Desktop abierto con el archivo que quiero revisar.
2. La licencia ya está aceptada; no repito esa operación durante cada conexión.
3. Reinicio Codex si la sesión actual no incorpora el servidor reparado.
4. Pido detectar las instancias locales de Power BI Desktop.
5. Selecciono el archivo objetivo si hay más de uno abierto.
6. Conecto en solo lectura y compruebo metadata mínima del modelo.
7. Registro el resultado antes de considerar completada la conexión.

Codex no necesita reinstalarse por un cambio de ruta del MCP.
Si el informe GTFS todavía no existe, la conexión no crea sus tablas ni sustituye Gold.
Mantendré separada cualquier prueba con un informe ajeno al proyecto.

## Escritura y diseño del reporte

El modo --readonly actual permite empezar por inspección y consultas compatibles.
Para crear medidas o relaciones necesito revisar una habilitación posterior de escritura y el alcance autorizado.
La versión instalada anuncia escritura predeterminada y una opción --require-confirmation.
No asumo que el comportamiento de confirmación sea idéntico en todas las versiones.
Conservo el modo de lectura para esta conexión inicial.

El diseño de páginas seguirá el [plan visual](power_bi_navigation_images.md).
El MCP de modelado y el diseño del reporte son capacidades distintas.
No habilité publicación ni cambios sobre modelos por instalar o reparar la conexión.

## Alcance del cierre de esta comprobación

El ejecutable instalado respondió con versión 1.0.1 y anunció 22 herramientas.
Codex CLI reconoce la ruta reparada y los argumentos --start y --readonly.
La prueba usó el protocolo MCP por stdio contra el ejecutable configurado.
La sesión actual todavía no muestra esas herramientas como herramientas nativas del chat.
Reiniciar Codex permite cargar el registro reparado en una sesión nueva.
No cierro Power BI Desktop ni su archivo para ese reinicio.

La prueba confirmó una conexión al modelo abierto y su enumeración posterior.
Después cerré la conexión de diagnóstico; no mantengo un cliente oculto conectado.
No consulté datos de tablas ni ejecuté DAX durante esta prueba.
El modelo utilizado no demuestra que exista un reporte GTFS ni un modelo Gold publicado.
No creé ni publiqué archivos PBIX/PBIP.

## Diferencia con la habilidad Power BI del navegador

La habilidad power-bi:power-bi utiliza el servicio Power BI desde un navegador local compatible.
El MCP configurado conecta herramientas con el modelo semántico de Desktop o destinos compatibles.
Son mecanismos distintos y pueden complementarse.

| Trabajo | MCP local configurado | Habilidad del navegador |
| --- | --- | --- |
| Inspeccionar el modelo abierto en Desktop | Conexión probada en lectura. | Fuera del alcance de esa habilidad. |
| Crear medidas y relaciones | Requiere habilitar escritura y autorizar el cambio concreto. | Depende del editor web disponible y los permisos del modelo. |
| Crear gráficos y ajustar páginas | Fuera del alcance del MCP de modelado. | Puede operar el editor web cuando la cuenta lo permite. |
| Publicar o compartir | La conexión inicial no autoriza esas acciones. | Requiere un pedido que cubra destino, audiencia y efecto. |

La [edición de modelos en el servicio](https://learn.microsoft.com/en-us/power-bi/transform-model/service-edit-data-models) permite crear medidas con los permisos necesarios.
No comprobé todavía esa cuenta web ni su entorno de edición.
No atribuyo al plugin una conexión web verificada por haber probado el MCP local.
El modo de lectura del MCP no modifica los permisos de la cuenta web.
