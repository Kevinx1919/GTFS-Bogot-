# Mi Job Silver manual

La [plantilla](gtfs_bogota_silver_manual.template.json) está versionada para revisión. /Workspace/REPO_ROOT es un marcador: genero el JSON final con gtfs_silver/job_config.py y la ruta real del repositorio, fuera de Git.

Sigo la [guía de ejecución Silver](../../docs/silver_execution.md) para crear y probar el Job. Usa For each y el notebook 10, con agency de ambos snapshots y una segunda etapa routes dependiente de su éxito. Ambas usan el mismo notebook 10, concurrencia 1 y sin schedule.

El Job de agency ya fue creado y ejecutado con éxito en Databricks. La definición ampliada a routes está preparada; debo actualizar el Job existente y comprobar la nueva etapa en Free Edition. Puedo pegar las listas JSON directamente en Inputs si no uso parámetros generales del Job.

## Estado actual: ampliación a stop_times

La plantilla conserva nueve tareas y añade publish_stop_times como décima tarea serial.
El procesador está implementado y stop_times ya tiene despliegue funcional confirmado en Databricks.
La [guía de stop_times](../../docs/silver_execution.md#despliegue-de-stop_times_v1) contiene el parámetro general y las comprobaciones.
Frequencies aporta contexto cuando su archivo está publicado. No multiplico visitas por cada ventana.
Los parámetros por snapshot siguen siendo manuales hasta implementar el planificador 8b.
