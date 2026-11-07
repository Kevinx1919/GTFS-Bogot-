# Mi mapa del lakehouse

[Abro el mapa interactivo del lakehouse](mapa_lakehouse.html).

## Qué me ayuda a entender

Sigo el dato desde el ZIP publicado hasta las tablas Silver. Distingo los lugares donde guardo archivos de los procesos que los leen y de las tablas que producen:

| Zona | Qué conservo | Cómo la reconozco |
| --- | --- | --- |
| Raw | ZIP original y manifiestos de captura | Archivos en el Volume `raw_gtfs`. |
| Staging | TXT extraídos del ZIP | Archivos en el Volume `staging_gtfs`. |
| Bronze | Filas fuente y columnas de procedencia | Tablas Delta `bronze_gtfs_*`. |
| Silver | Filas validadas y tipadas de agency y routes | Tablas Delta `silver_gtfs_*`. |
| Gold y Power BI | Indicadores y consumo analítico por construir | Etapas marcadas como futuras. |

Mantengo Bronze y Silver dentro de `workspace.gtfs_bogota`. La capa depende de su responsabilidad y sus reglas; compartir schema no las convierte en una sola capa. Es como tener documentos recibidos y documentos revisados en el mismo archivo, con una clasificación clara. Esta comparación es explicativa.

## Un detalle del recorrido

El pipeline Silver recibe las filas de Bronze y lee el encabezado del TXT del mismo snapshot en Staging. El encabezado me permite distinguir una columna ausente en el archivo de una columna publicada con valores nulos. Por eso el mapa incluye las dos entradas: `Snapshot` y `Encabezado TXT`.

Solo publico Silver si la validación permite hacerlo. La auditoría y la cuarentena se resumen en las notas del mapa; abro el [recorrido del Job](../job_silver/README.md) para ver sus estados y errores. Uso Genie como ayuda de exploración de lectura; las reglas y escrituras pertenecen al pipeline versionado.

## Cómo lo exploro

Puedo seleccionar elementos para consultar sus referencias, usar las vistas de archivos, tablas y futuro, y acercar el recorrido que necesite. Los enlaces al código apuntan a una revisión fija, de modo que puedo comparar una explicación con el código que la respalda.

El flujo se limita al GTFS estático. Gold, su agregación y Power BI son un objetivo de diseño; no representan salidas implementadas. Tampoco interpreto estos datos como evidencia de puntualidad, demanda u operación real.

## Fuente y comprobación

La fuente editable es [mapa_lakehouse.dataflow.json](mapa_lakehouse.dataflow.json). El mapa está respaldado por el código del commit `598bc0de6b65b25ffa2ef13b628ab0966fd41dcd`.

Comprobé estructura, referencias y funcionamiento del HTML en navegador. Revisé capturas en claro y oscuro a 1440×900 y 2048×1320, incluida la conexión del encabezado que rodea el flujo principal. El [resumen público de verificación](verificacion.json) conserva el alcance y los hashes. Estas comprobaciones son de documentación; no ejecutan la ingesta ni consultan Databricks.

Genero fuera de OneDrive y copio el HTML comprobado sin cambiar sus bytes. Los recibos de Archify y capturas detalladas permanecen en el entorno local, fuera de Git; el resumen identifica la copia final.
