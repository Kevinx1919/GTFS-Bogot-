# Mi plan de automatización: selección Silver y Job principal

**Estado:** cierre Bronze v2 comprobado en Workspace para 2025 y 2026.
La prueba de despliegue de los cargadores 02–05 sigue pendiente.
Vista previa del planificador comprobada en Workspace, sin bloqueos después de la recuperación.
El piloto NO_WORK del Job terminó SUCCEEDED; el camino con trabajo nuevo y el Job principal siguen pendientes.
La [guía Bronze v2](bronze_automation.md) describe el incremento actual.
**Fecha:** 12 de noviembre de 2026.
Este diseño desarrolla el pendiente 8b del [plan Silver](silver_design.md#automatización-pendiente-selección-de-snapshots-silver).

## Qué problema resuelvo con cada pieza

El planificador decide qué trabajo está pendiente.
El Job principal coordina cuándo ejecutarlo.
Necesito ambas piezas para recibir una versión nueva y promoverla automáticamente hasta Silver.
El alcance inicial son snapshots compatibles del GTFS estático de Bogotá, localizados en el catálogo oficial.
No prometo procesar automáticamente otro formato, otra ciudad o cambios de esquema incompatibles.
GTFS-Realtime y demanda mantienen sus propios contratos y cadencias.

## Qué tengo hoy

Tengo diez entidades Silver publicadas y el Job gtfs_bogota_silver_manual versionado mediante una plantilla.
Conservé una plantilla manual con listas fijas y conecté el Job desplegado a plan_silver.
El piloto NO_WORK ya está comprobado; falta el camino con trabajo nuevo.
Notebook 10 y los módulos Python ya reciben entidad, versión y hash.
No necesito reconstruir sus transformaciones para generar listas dinámicas.

Creé gtfs_bogota_bronze_manual directamente en la interfaz de Databricks.
Contrasté las dependencias mediante Genie en system.lakeflow.
La exportación del Job confirma también las rutas y los parámetros de sus cinco notebooks.
El [diagnóstico Bronze](bronze_review_2026_11_12.md) precisa evidencia y límites.
La topología es:

```text
raw_gtfs                 → notebook 02
    ↓
staging_y_rutas          → notebook 03
    ├── bronze_referencias → notebook 04
    └── bronze_operativos  → notebook 05
              ↓ ambas
validar_bronze           → notebook 07
```

Contrasté el JSON exportado y guardé una [plantilla portable](bronze_job_configuration.md).
Conservé el grafo y sustituí únicamente la raíz personal del repositorio.
Notebook 06 ya tiene selección local basada en cierres completos, límites y resultado NO_WORK.
Todavía no pertenece al Job desplegado; falta comprobarlo en Workspace.
Conservaré el paralelo entre referencias y operativas mientras respete los límites de concurrencia.

## Hallazgos que afectan la automatización

| Evidencia del código | Consecuencia | Cambio propuesto |
| --- | --- | --- |
| Notebook 06 considera cargada una versión cuando encuentra filas en bronze_gtfs_routes. | Una ingesta incompleta de otras entidades puede quedar fuera de la selección. | Consultar preparación completa del snapshot, además de controlar reintentos y recuperación. |
| Notebook 06 selecciona una sola versión por defecto. | Puede dejar otras versiones pendientes. | Usar lotes acotados y explícitos; no elegir siempre solamente la última. |
| Los modos explicit_version y backfill_range parten del conjunto que ya excluyó versiones con rutas. | Una recuperación explícita puede quedar vacía. | Separar selección de pendientes y reprocesamiento autorizado. |
| Notebook 06 lanza un error cuando no encuentra versiones pendientes. | Un día sin novedades aparece como fallo. | Registrar un resultado sin trabajo y continuar evaluando pendientes Silver. |
| Notebook 06 muestra un DataFrame, pero no entrega todavía una lista al Workflow. | El catálogo descubierto no coordina la ingesta automáticamente. | Publicar un plan acotado con task values dentro del Job correspondiente. |
| Notebook 02 calcula el hash después de descargar y publica versión, hash y ruta mediante task values. | El hash auténtico no existe antes de recibir el ZIP. | Propagar el hash calculado, sin reutilizar el último hash conocido. |
| Notebook 07 guarda checks y task values; no tiene una tabla resumen explícita de cierre por corrida. | Un planificador necesita distinguir una corrida completa de evidencia incompleta. | Persistir un resumen terminal auditable, con identidad y versión de reglas. |
| Varias comprobaciones de ya cargado en Bronze usan solo hash. Otros lectores también filtran por hash y comprueban versión. | La política actual requiere revisar el caso del mismo contenido publicado con otra versión. | Auditar la identidad versión/hash en conjunto; no cambiar un filtro aislado ni ocultar errores de procedencia. |

No modificaré Raw para resolver estas situaciones.
No asumiré que una versión aparece una sola vez ni que una fecha garantiza contenido idéntico.
Una modificación del ZIP bajo la misma versión produce otro hash y conserva su propia evidencia.
Para detectar esa modificación necesito volver a descargar o aplicar una política explícita de reconsulta.
La fecha de modificación del portal puede orientar esa decisión; no sustituye el hash del contenido.

## Pieza 1: planificador de Silver

Implementé localmente la tarea inicial plan_silver y una variante optativa del Job Silver.
La [guía del planificador](silver_planner.md) conserva decisiones, límites y pasos de comprobación.
La lógica Python comparará evidencia Bronze completa con audit_gtfs_silver_runs y disponibilidad del destino.
El registro silver_entities.json seguirá definiendo contratos y dependencias.

Cada trabajo conservará entidad, versión, hash y regla esperada.
Service_dates añadirá su horizonte explícito.
La fecha del feed no decidirá automáticamente el horizonte de esa derivación.
Mantendré la política inicial de service_dates 2026 hasta configurar otra ventana deliberadamente.

El planificador separará trabajo pendiente, completado, bloqueado y opcional no publicado.
Una dependencia completada o incluida antes en el plan puede habilitar su entidad dependiente.
No exigiré que todas las dependencias ya estén publicadas al construir el plan inicial.
Los procesadores volverán a comprobarlas antes de publicar.
No usaré el éxito de una corrida anterior para esconder un fallo posterior pendiente de revisión.
También revisaré dependencias reprocesadas o reglas nuevas antes de omitir trabajo antiguo.

Omitiré una entidad completada solo con auditoría satisfactoria, regla vigente y destino disponible para ese snapshot.
La disponibilidad del nombre de una tabla no demuestra integridad de todo su contenido.
Si detecto incoherencia o no puedo comprobar el estado requerido, registraré diagnóstico y exigiré recuperación explícita.
Usaré metadata como base; reservaré comprobaciones acotadas del destino para los casos necesarios.
No perfilaré millones de visitas para construir cada lista de trabajo.

Los For each recibirán listas desde valores de plan_silver.
Por ejemplo, la referencia propuesta para rutas será {{tasks.plan_silver.values.routes_work_items}}.
No será necesario editar manualmente fechas y hashes por cada nueva versión compatible.
Mantendré límites de tamaño, lotes reanudables y trabajos restantes pendientes para otra ejecución.

## Evidencia de preparación Bronze

Implementé localmente audit_gtfs_bronze_snapshot_runs como auditoría operativa, no como entidad analítica.
La [guía del contrato](bronze_automation.md) define eventos STARTED/CLOSED, conteos y grano.
Conserva corrida, versión, hash, inicio/fin UTC, reglas Bronze y resultado terminal.
Relaciona el resultado con inventario de entidades, observaciones y checks persistidos.
Incluye el identificador del coordinador cuando corresponda.
El cierre de notebook 07 está comprobado para ambos snapshots; las pruebas de los cargadores siguen pendientes.

Solo una evaluación completa y sin fallos bloqueantes habilitará el intento Silver.
Una advertencia Bronze no aprobará automáticamente un contrato Silver incompatible.
Las reglas Silver mantendrán la última decisión sobre tipado y publicación.
No confundiré cuarentena con aprobación ni una fila de rutas con todo el snapshot listo.
Para los snapshots existentes ejecutaré una reconciliación controlada de conteos contra Staging.
No basta una comprobación de metadata para certificar el nuevo contrato.
No volveré a descargar automáticamente los históricos solo para crear ese resumen.

## Pieza 2: Job principal

Recomiendo crear un coordinador, con nombre propuesto gtfs_bogota_pipeline.
Reutilizará los Jobs Bronze y Silver mediante tareas Run Job.
El Job principal será el punto normal de ejecución.
Los Jobs especializados conservarán su utilidad para pruebas, recuperación y reprocesamiento controlado.

```text
Job principal propuesto
  1. Descubrir catálogo y construir plan de ingesta.
  2. Ejecutar gtfs_bogota_bronze_manual para las versiones seleccionadas.
  3. Evaluar el cierre de ingesta y su compuerta de calidad.
  4. Ejecutar gtfs_bogota_silver_manual con su plan_silver dinámico.
  5. Registrar el resumen global de trabajo y resultados.
```

Si hay varias versiones, las procesaré de forma serial en un lote acotado.
Un For each admite una tarea interna; no una cadena arbitraria de cinco notebooks.
Por eso puede llamar al Job Bronze existente por versión, conservando su cadena interna.
La configuración concreta respetará los límites de anidamiento y concurrencia de Free Edition.
No crearé dependencias circulares ni cadenas de Jobs innecesarias.

Un día sin ingestas nuevas todavía puede tener trabajo Silver pendiente.
La compuerta del coordinador distinguirá ausencia de trabajo, fallo de ingesta y datos listos.
Probaré el comportamiento real de listas vacías y tareas omitidas antes de fijar run_if.
Un fallo bloqueante de ingesta impedirá la promoción automática dependiente.
Un éxito parcial entre snapshots conservará sus estados; no habrá un rollback conjunto de todas las tablas.
Los trabajos válidos pendientes podrán recuperarse mediante el Job especializado.

Task values conectará tareas dentro de cada Job.
No asumiré que un Job hijo comparte sus task values con el padre o con otro hijo.
Entre Jobs usaré parámetros explícitos y evidencia persistida compartida.
El Job Silver leerá el inventario preparado; no dependerá de copiar el hash desde una pantalla.
Tampoco pasaré un snapshot_sha256 general fijo que sustituya el hash calculado por Raw.

Los Jobs especializados conservarán max_concurrent_runs=1.
El coordinador tendrá una sola corrida activa y empezará con iteraciones seriales.
Revisaré disparadores existentes para evitar ejecuciones independientes que compitan con la orquestación.
No afirmaré que el límite del padre bloquea por sí solo todos los lanzamientos manuales de sus hijos.

## Comparo las formas de unir los Jobs

| Diseño | Ventaja | Costo o límite |
| --- | --- | --- |
| Principal que llama a Bronze y Silver | Reutiliza responsabilidades, conserva recuperación separada y reduce cambios iniciales. | Necesita parámetros claros y evidencia persistida entre Jobs. |
| Un único Job con todas las tareas | Muestra todo en un grafo y facilita referencias entre tareas del mismo Job. | Reorganiza el flujo completo y complica el procesamiento de varias versiones con subflujos. |

Elijo la primera opción para el siguiente incremento.
La segunda sigue siendo viable si después necesito una vista operativa completamente plana.
No necesito fusionar notebooks ni duplicar las transformaciones.

## Orden de implementación

1. Completado: contrasté la exportación real del Job Bronze y guardé una plantilla sin la raíz personal del repositorio.
2. Cierre bronze_snapshot_v2 comprobado: 2025 PASSED y 2026 WARNING con cinco advertencias, ambos sin fallos bloqueantes. La lectura independiente de eventos será parte de la comprobación del planificador.
3. Probar en Workspace los cambios de integridad y carga común de notebooks 02–05 antes de habilitar ingesta automática. No requiere posponer la implementación de plan_silver sobre los cierres existentes.
4. Vista previa de plan_silver comprobada en Workspace: diecinueve COMPLETE, un OUT_OF_SCOPE y dos RESOLVED; sin bloqueos ni pendientes.
5. Variante conectada y piloto NO_WORK comprobado en Workspace. Falta una corrida con trabajo nuevo.
6. Implementado localmente: adaptar notebook 06 con cierres completos, selección explícita y NO_WORK. Falta comprobarlo en Workspace.
7. Crear la plantilla del Job principal y pasar parámetros explícitos a los Jobs existentes.
8. Ejecutar un piloto manual y comprobar recuperación, auditoría, histórico y ausencia de duplicados.
9. Habilitar programación según la cadencia de publicación, después de aprobar el piloto.

Las dos primeras piezas seguirán funcionando por separado durante la transición.
No activo una programación automática como parte de esta propuesta.


## Casos mínimos de aceptación

| Caso | Resultado esperado |
| --- | --- |
| Nueva versión compatible | Ingesta completa, calidad Bronze y solo las entidades Silver aplicables. |
| Todo completado bajo reglas vigentes | Sin escrituras analíticas innecesarias; resultado sin trabajo. |
| Sin novedades Raw pero con Silver pendiente | Procesamiento de Silver sin descargar otra vez el histórico. |
| Rutas presentes pero otras entidades Bronze incompletas | Recuperación pendiente; nunca considerar completo todo el snapshot por rutas. |
| Falla una entidad Silver | Reintento controlado; conservar publicaciones anteriores y trabajo restante. |
| Cambia un contrato | Selección explícita del reprocesamiento y revisión de dependientes. |
| Falta un archivo opcional | Registrar ausencia válida sin inventar filas. |
| Mismo nombre de versión con otro hash | Conservar evidencia y estado separados. |
| Mismo hash con otra versión | Aplicar una política coherente en lectores, cargas y auditoría; probarla antes de habilitarla. |
| Nuevo esquema incompatible | Bloqueo visible del contrato; sin aprobación automática mediante IA. |
| Listas vacías o demasiado grandes | Salida sin novedades o lote acotado y reanudable; sin pérdida de trabajo. |
| Límite de concurrencia o reinicio | Cola y recuperación verificadas; sin escritores simultáneos sobre el mismo ámbito. |

## Fuentes

El código de notebooks 02–07 respalda los hallazgos de ingesta y Bronze.
Job_config.py y silver_entities.json respaldan la configuración actual de Silver.
Las dependencias del Job Bronze están contrastadas mediante metadata histórica de Genie.
La [revisión de la exportación](bronze_job_configuration.md) confirma rutas, parámetros y campos incluidos en el JSON.

- [Run Job](https://docs.databricks.com/aws/en/jobs/tasks/run-job): llamada a Jobs existentes y parámetros.
- [Task values](https://docs.databricks.com/aws/en/jobs/task-values): valores entre tareas del mismo Job y límite de tamaño.
- [For each](https://docs.databricks.com/aws/en/jobs/tasks/for-each): tarea interna única y listas de entrada.
- [Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations): límites de cómputo y tareas concurrentes.

## Incremento local completado: preparación Bronze v2

Implementé el cierre de notebook 07 y el cargador compartido de notebooks 03–05.
Notebook 02 añade reintentos temporales y verificación del ZIP reutilizado.
El [detalle de despliegue](bronze_automation.md) distingue implementación local y prueba real pendiente.
Las observaciones iniciales de este documento describen el código anterior y motivan estos cambios.
Los STARTED/CLOSED registran intentos completos o incompletos sin modificar evidencia histórica.
Mantengo un solo escritor; no hay bloqueo distribuido entre Jobs.
Los avisos pasan a Silver bajo la política existente; sus contratos siguen siendo obligatorios.
La exportación del Job Bronze ya está revisada y su plantilla portable está versionable; no modifiqué el despliegue.

El 13 de noviembre comprobé notebook 07 en Workspace con ambas versiones.
La [evidencia de cierre](bronze_automation.md#cierre-comprobado-en-workspace--13-de-noviembre-de-2026) precisa los resultados y su alcance.

El 13 de noviembre implementé plan_silver, notebook 11 y la variante optativa del Job.
Pasaron 112 pruebas unitarias y cuatro integraciones nativas del planificador.
Primero comprobaré la vista previa; la ingesta automática y el Job principal permanecen pendientes.

## Primer ensayo del planificador y recuperación pendiente

La vista previa en Workspace encontró intentos sin cierre que bloquean la promoción automática.
El [diagnóstico y recuperación](planner_recovery.md) conserva la evidencia verificada con Genie.
La recuperación explícita está implementada y probada localmente; aún no está aplicada en Workspace.
Antes de conectar el Job, revisaré sus propuestas y volveré a ejecutar notebook 11.
No eliminaré auditorías ni forzaré estados satisfactorios.

El 13 de noviembre apliqué ambas resoluciones y comprobé nuevamente notebook 11 en Workspace.
Los bloqueos originales desaparecieron sin republicar las entidades completadas.
El siguiente incremento es comprobar task values y ciclos vacíos en la variante del Job.
Las guardas de ingesta 02–05 y el descubrimiento dinámico siguen pendientes antes del coordinador automático.

El piloto NO_WORK terminó con éxito: once tareas SUCCEEDED y aproximadamente 2 minutos y 3 segundos.
Contrasté el historial mediante Genie; el [registro del piloto](silver_planner.md) conserva alcance y límites.
El siguiente incremento prepara descubrimiento e ingesta; todavía no habilita programación automática.

## Incremento local: descubrimiento Bronze

Implementé [descubrimiento acotado](bronze_discovery.md) en notebook 06.
Conservé el esquema de control y las observaciones históricas.
El plan reutiliza cierres y resoluciones; ya no considera completas las versiones solamente por sus rutas.
Los lotes entregan versiones sin hash; Raw conserva la responsabilidad de calcularlo.
La variante parametrizada del Job Bronze y el coordinador siguen pendientes.
Mi siguiente comprobación usa una versión existente en modo explícito, sin reprocesamiento ni emisión de task values.
