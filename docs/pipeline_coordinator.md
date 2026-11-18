# Mi Job principal: gtfs_bogota_pipeline

**Estado:** plantillas y renderizador implementados y comprobados localmente.
Todavía no creé ni ejecuté el coordinador en Databricks.
La primera configuración prepara un piloto manual con el snapshot existente 2026-09-29.
No habilité horarios ni añadí entidades Silver.

## Archivos

| Archivo | Para qué lo uso |
| --- | --- |
| databricks/jobs/gtfs_bogota_pipeline.template.json | Definición portable del Job para CLI/API. Contiene raíz marcador e IDs cero. |
| databricks/jobs/gtfs_bogota_pipeline.template.yaml | Representación equivalente resources.jobs para edición YAML y bundles. |
| databricks/jobs/render_pipeline.py | Sustituye raíz e IDs localmente. No autentica, crea ni ejecuta Jobs. |
| tests/test_pipeline_job_config.py | Comprueba referencias, separación de identidad, ramas de aceptación y generación local. |

Los archivos YAML usan sintaxis JSON válida dentro de YAML 1.2.
Así conservo una representación equivalente sin instalar otro serializador.
El archivo JSON contiene JobSettings directamente.
El YAML añade el contenedor resources.jobs.gtfs_bogota_pipeline.
No uso el contenedor YAML como cuerpo JSON de jobs/create.
Las plantillas portables requieren renderizado antes de desplegarlas: job_id=0 no identifica mis Jobs reales.

## Flujo y condiciones

```text
plan_bronze / notebook 06
      ↓
has_bronze_work / planned_count > 0
      ├── true → ingest_bronze / For each serial → Run Job Bronze
      └── false → Bronze queda excluido
                          ↓
publish_silver / Run Job Silver
```

| Tarea | Responsabilidad | Entrada y condición | Efecto |
| --- | --- | --- | --- |
| plan_bronze | Actualizar catálogo y descubrir pendientes. | Notebook 06, selección y límites explícitos; emit_task_values=true. | Metadata del catálogo y lista ingestion_work_items; no descarga ZIP. |
| has_bronze_work | Separar trabajo de ausencia de novedades. | Task value planned_count mayor que cero. | Condición del Workflow; sin tablas ni cómputo Spark. |
| ingest_bronze | Llamar al Job Bronze por cada versión. | Rama true y lista del plan; concurrencia uno. | El Job hijo descarga, carga y valida mediante sus cinco tareas. |
| publish_silver | Ejecutar el Job Silver con plan_silver. | Depende del plan, la condición y el For each; run_if=NONE_FAILED. | El Job hijo determina pendientes y publica solo lo necesario. |

La dependencia de Silver incluye tareas previas que sí ejecutaron.
Así la exclusión de Bronze por falta de trabajo no excluye toda la rama Silver.
NONE_FAILED permite continuar con ramas excluidas y bloquea fallos previos.
El piloto debe comprobar ese comportamiento en el motor real.
No dependo del resultado particular de un For each con una lista vacía.
Si falla descubrimiento o alguna ingesta, no promociono automáticamente mediante el Job Silver de este coordinador.
Los otros Jobs conservan su recuperación manual independiente.

El historial nativo del Job principal será el resumen de ejecución de esta primera versión.
No añadí una tabla nueva de cierre global ni prometo una transacción conjunta entre capas.
Conservo las auditorías Bronze y Silver existentes.

## Parámetros y separación de responsabilidades

Uso prefijos bronze_ y silver_ para separar las opciones de ambos planificadores.
No declaro feed_version, snapshot_sha256 ni requested_feed_version como parámetros generales del padre.
Así no sustituyo accidentalmente la identidad de cada iteración mediante la precedencia de parámetros generales.

Cada llamada Bronze recibe requested_feed_version desde input.feed_version.
También recibe repo_root, catálogo, schema, Volumes y coordinator_run_id con el ID de la corrida principal.
El cierre de notebook 07 puede conservar ese vínculo.
Raw sigue calculando el hash del ZIP y entregándolo dentro de su propio Job.
La validación del Job Bronze debe usar require_task_values=true y bloquear fallos de calidad.

Silver recibe su rango, cupo de snapshots, configuración del entorno, mode=publish y verify_history=true.
Su propia tarea plan_silver consulta evidencia persistida y genera sus listas.
No intento acceder desde el padre a task values internos de los Jobs hijos.
No añado otro For each alrededor del Job Silver.

## Defaults del piloto inicial

| Parámetro | Valor |
| --- | --- |
| repo_root | Raíz real del repositorio en Workspace, resuelta fuera de Git. |
| catalog / schema | workspace / gtfs_bogota, defaults de mi entorno actual. |
| raw_volume / staging_volume | raw_gtfs / staging_gtfs. |
| max_metadata_rows | 5000. |
| bronze_selection_mode | explicit_version. |
| bronze_explicit_version | 2026-09-29. |
| bronze_start_date / bronze_end_date | Vacíos. |
| bronze_max_versions | 1. |
| bronze_reprocess_completed | false. |
| silver_feed_version_from / silver_feed_version_to | 2026-09-29 / 2026-09-29. |
| silver_max_snapshots | 20. |

Estos defaults prueban coordinación sin solicitar deliberadamente un feed nuevo.
Si los cierres y destinos permanecen consistentes, espero NO_WORK en ambos planificadores.
Un cambio del portal o de las auditorías puede cambiar ese resultado; reviso sus razones antes de reparar.
El estado real del piloto todavía no está comprobado.

## Cómo genero archivos para mi entorno

Desde la raíz del repositorio ejecuto el renderizador local.
Sustituyo los marcadores entre ángulos antes de ejecutar:

```powershell
py -B databricks/jobs/render_pipeline.py `
  --repo-root "<RAIZ_REAL_EN_WORKSPACE>" `
  --bronze-job-id <ID_JOB_BRONZE> `
  --silver-job-id <ID_JOB_SILVER> `
  --output "$env:TEMP\gtfs_bogota_pipeline.json" `
  --yaml-output "$env:TEMP\gtfs_bogota_pipeline.yaml"
```

Los IDs deben pertenecer a Jobs existentes y distintos del mismo Workspace.
Si notebook 06 conserva extensión .ipynb en su ruta real, uso --discovery-notebook-path con esa ruta exacta.
Compruebo la ruta desde el selector de notebooks antes del primer Run now.
La versión de entorno serverless inicial es 4; puedo reemplazarla con --environment-version si mi Workspace exige otra.
No instalo pyspark, delta-spark ni validadores Silver en el entorno del descubrimiento.
Ese notebook usa las bibliotecas Spark/Delta del entorno administrado y las lecturas compartidas del repositorio.

## Cómo lo cargo en Databricks

La configuración es del Job completo; no es una lista Inputs de un For each.
JSON se consume mediante CLI, SDK o REST API.
El editor View as code permite ver JSON y editar la configuración YAML.
No presupongo un botón universal para subir un JSON directamente desde la interfaz.

Para trabajar desde la interfaz:

1. Creo un Job nuevo llamado gtfs_bogota_pipeline, sin ejecutarlo.
2. Abro el menú junto a Run now y selecciono View as code.
3. Selecciono YAML y, si está disponible, Edit.
4. Uso el archivo YAML resuelto, con IDs reales y la raíz configurada.
5. Conservo la clave del recurso que use el editor si difiere de gtfs_bogota_pipeline.
6. Si el editor muestra solo los campos del Job, uso el contenido del recurso, sin su contenedor resources.jobs.
7. Reviso el grafo de cuatro tareas, el selector de notebook 06 y los Jobs elegidos en ambas llamadas.
8. Guardo antes de iniciar el piloto.

Si mi interfaz no ofrece edición YAML, utilizo CLI/API o reproduzco las cuatro tareas según esta guía.
No instalo ni autentico una CLI automáticamente desde el renderizador.

Con una CLI ya instalada y autenticada puedo crear el Job desde el JSON resuelto:

```powershell
databricks jobs create --json "@$env:TEMP\gtfs_bogota_pipeline.json"
```

No ejecuto ese comando si ya creé el mismo coordinador mediante la interfaz.
No uso reset ni sustituyo la configuración de los Jobs hijos con la del padre.
La CLI/API comprueba la configuración contra el Workspace; la comprobación local no reemplaza ese paso.

## Comprobación antes de Run now

El Job Bronze debe tener el parámetro general requested_feed_version conectado a Raw.
El Job Silver debe tener plan_silver y los Inputs dinámicos ya comprobados en el piloto anterior.
Compruebo que no haya ejecuciones independientes sobre el mismo ámbito.
Reviso triggers de los hijos para evitar lanzamientos automáticos que compitan con el coordinador.
Mantengo una corrida principal y una iteración Bronze simultáneas.
Esos límites no bloquean todos los lanzamientos manuales externos.
Free Edition mantiene límites por cuenta; verificaré su comportamiento real durante el piloto.

## Qué resultado espero

| Caso | Resultado esperado |
| --- | --- |
| No hay versiones Bronze pendientes | Condición false, ingest_bronze excluido y Job Silver ejecutado. |
| Hay una o varias versiones compatibles | Iteraciones Bronze seriales y luego Job Silver. |
| Fallo de descubrimiento o calidad Bronze | Promoción Silver del coordinador bloqueada. |
| Silver no tiene pendientes | Su plan devuelve NO_WORK y sus ciclos terminan sin republicación. |
| Una entidad Silver falla | El Job hijo y el coordinador reflejan el fallo; conservo auditorías y publicaciones previas. |

Primero probaré el camino NO_WORK y observaré la llamada real al hijo Silver.
Después probaré la rama Bronze con trabajo explícito controlado y una versión nueva compatible.
Un reprocesamiento del mismo snapshot prueba esa rama, pero no equivale a ingerir un feed nuevo.
No habilito programación antes de comprobar ambos caminos y su recuperación.

## Alcance de la comprobación local

Pasaron 133 pruebas unitarias, incluidas cinco del contrato del coordinador.
Las pruebas validan el contrato de referencias, los IDs, la separación de parámetros y la estructura del grafo.
Modelan los casos de aceptación de NONE_FAILED según la documentación.
No afirman haber ejecutado el motor Lakeflow ni los Jobs reales.
No desplegué, activé horarios ni modifiqué los Jobs existentes.

## Fuentes

- [Configuración mediante JSON y edición YAML](https://docs.databricks.com/aws/en/jobs/automate).
- [Run Job y parámetros del Job hijo](https://docs.databricks.com/aws/en/jobs/tasks/run-job).
- [For each y referencias por iteración](https://docs.databricks.com/aws/en/jobs/tasks/for-each).
- [Condiciones y dependencias](https://docs.databricks.com/aws/en/jobs/run-if).
- [If/else](https://docs.databricks.com/aws/en/jobs/tasks/if-else).
- [Límites Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
