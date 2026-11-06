# Mi Job Silver manual

La [plantilla](gtfs_bogota_silver_manual.template.json) está versionada para revisión. /Workspace/REPO_ROOT es un marcador: genero el JSON final con gtfs_silver/job_config.py y la ruta real del repositorio, fuera de Git.

Sigo la [guía de ejecución Silver](../../docs/silver_execution.md) para crear y probar el Job. Usa For each y el notebook 10, con agency de ambos snapshots, una sola ejecución concurrente y sin schedule. Solo agency tiene un procesador implementado.

La definición está preparada; el Job todavía no fue creado en Databricks. La validación local de configuración no reemplaza la creación y ejecución real en Free Edition.
