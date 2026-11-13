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
El Job Bronze creado en la interfaz se llama gtfs_bogota_bronze_manual. Su exportación portable sigue pendiente.
El coordinador sigue propuesto. Plan_silver ya tiene una plantilla optativa implementada localmente.

El cierre de [preparación Bronze v2](../../docs/bronze_automation.md) ya está comprobado en Workspace para ambas versiones.
Los cargadores 02–05 conservan su prueba de despliegue pendiente. El Job principal sigue pendiente.

## Variante optativa con planificador

La [plantilla planificada](gtfs_bogota_silver_planned.template.json) añade plan_silver y conserva los diez ciclos seriales.
La genero con --selection-mode auto; el modo por defecto y la plantilla manual siguen disponibles.
Notebook 11 tiene vista previa sin escrituras con emit_task_values=false.
La [guía](../../docs/silver_planner.md) describe su comprobación antes de cambiar el Job desplegado.
La variante está probada localmente, pero todavía no está validada en Workspace.
