# Mi Job Silver manual

La [plantilla](gtfs_bogota_silver_manual.template.json) está versionada para revisión. /Workspace/REPO_ROOT es un marcador: genero el JSON final con gtfs_silver/job_config.py y la ruta real del repositorio, fuera de Git.

Sigo la [guía de ejecución Silver](../../docs/silver_execution.md) para crear y probar el Job. Usa For each y el notebook 10, con agency de ambos snapshots y una segunda etapa routes dependiente de su éxito. Ambas usan el mismo notebook 10, concurrencia 1 y sin schedule.

El Job ya tiene diez entidades Silver con despliegue funcional confirmado en Databricks.
Puedo pegar listas JSON en Inputs o definirlas mediante parámetros generales del Job.
Las listas dinámicas siguen pendientes del planificador 8b.

## Estado actual: ampliación a stop_times

La plantilla conserva nueve tareas y añade publish_stop_times como décima tarea serial.
El procesador está implementado y stop_times ya tiene despliegue funcional confirmado en Databricks.
La [guía de stop_times](../../docs/silver_execution.md#despliegue-de-stop_times_v1) contiene el parámetro general y las comprobaciones.
Frequencies aporta contexto cuando su archivo está publicado. No multiplico visitas por cada ventana.
Los parámetros por snapshot siguen siendo manuales hasta implementar el planificador 8b.

## Orquestación propuesta

El [análisis del planificador y Job principal](../../docs/orchestration_plan.md) describe el siguiente incremento.
El Job Bronze creado en la interfaz se llama gtfs_bogota_bronze_manual. Su [plantilla portable](gtfs_bogota_bronze_manual.template.json) conserva la exportación revisada.
El coordinador sigue propuesto. Plan_silver ya tiene una plantilla optativa implementada localmente.

El cierre de [preparación Bronze v2](../../docs/bronze_automation.md) ya está comprobado en Workspace para ambas versiones.
Los cargadores 02–05 conservan su prueba de despliegue pendiente. El Job principal sigue pendiente.

## Variante optativa con planificador

La [plantilla planificada](gtfs_bogota_silver_planned.template.json) añade plan_silver y conserva los diez ciclos seriales.
La genero con --selection-mode auto; el modo por defecto y la plantilla manual siguen disponibles.
Notebook 11 tiene vista previa sin escrituras con emit_task_values=false.
La [guía](../../docs/silver_planner.md) describe su comprobación antes de cambiar el Job desplegado.
Notebook 11 ya tiene vista previa comprobada en Workspace: diecinueve COMPLETE, un OUT_OF_SCOPE y dos RESOLVED.
El Job conectado al planificador ya completó un piloto NO_WORK en Workspace: once tareas SUCCEEDED.
La prueba con listas no vacías y trabajo nuevo sigue pendiente.

## Job Bronze exportado

Conservé las cinco tareas del Job existente y sus parámetros originales.
La [revisión](../../docs/bronze_job_configuration.md) explica qué confirmé y qué falta para automatizar la ingesta.
`/Workspace/REPO_ROOT` reemplaza la raíz personal del repositorio.
La versión fija sigue siendo 2025-10-28; esta plantilla todavía no incorpora descubrimiento ni llama a Silver.
No añadí parámetros, reintentos o entornos que la exportación no declara.
La siguiente variante recibirá configuración explícita y mantendrá el hash calculado por Raw.

Notebook 06 ya reconoce ambos snapshots existentes en Workspace; su [entrega de listas al Workflow](../../docs/bronze_discovery.md) sigue pendiente.
La plantilla fiel del Job Bronze conserva sus cinco tareas y todavía no incluye descubrimiento.

## Variante Bronze parametrizada

La [plantilla parametrizada](gtfs_bogota_bronze_parameterized.template.json) añade requested_feed_version al Job existente.
Conserva las cinco tareas, sus rutas portables y las referencias de identidad desde Raw.
Exige task values en Raw y validación; no incluye descubrimiento ni llama a Silver todavía.
La [guía](../../docs/bronze_job_configuration.md#variante-parametrizada-preparación-local) explica cómo actualizar el Job existente.
La salida del flujo 2025 ya confirma validación completa y conteos reconciliados.
La salida de la comprobación 2026 ya está contrastada con su auditoría mediante Genie: validación completa y elegible, con cinco advertencias conocidas.
No reexporté la configuración modificada ni comprobé cada parámetro efectivo del Job.
El siguiente incremento prepara el coordinador y la entrega de listas de descubrimiento.

## Job principal preparado localmente

La [plantilla JSON](gtfs_bogota_pipeline.template.json) y su [representación YAML](gtfs_bogota_pipeline.template.yaml) definen el coordinador manual.
Los IDs cero y /Workspace/REPO_ROOT son marcadores; genero los archivos del entorno con render_pipeline.py.
El renderizador no autentica, crea ni ejecuta Jobs.
La [guía del coordinador](../../docs/pipeline_coordinator.md) explica carga desde CLI/API o edición YAML de la interfaz.
Conservo cuatro tareas: descubrimiento, condición de trabajo, For each con Run Job Bronze y Run Job Silver.
La condición excluye Bronze cuando no hay versiones pendientes; NONE_FAILED permite continuar hacia Silver si no hubo fallos.
El piloto inicial queda acotado al snapshot existente 2026-09-29, sin horario automático.
El coordinador todavía no está creado ni comprobado en Workspace.
