# Mi configuración real del Job Bronze

**Fecha de revisión:** 13 de noviembre de 2026.
**Estado:** exportación revisada y plantilla portable guardada; sin cambios en el Job desplegado.

Conservé la configuración exportada desde View as code.
Sustituí únicamente la raíz personal por `/Workspace/REPO_ROOT`.
La [plantilla](../databricks/jobs/gtfs_bogota_bronze_manual.template.json) representa el Job existente, no el coordinador futuro.
No necesito compartir tokens para obtener esta configuración.

## Qué confirmé

```text
raw_gtfs / 02
      ↓
staging_y_rutas / 03
      ├── bronze_operativos / 05
      └── bronze_referencias / 04
                    ↓ ambas
validar_bronze / 07
```

Raw recibe `feed_version=2025-10-28` como valor fijo.
Las otras cuatro tareas reciben versión y hash desde los task values de Raw.
El hash se calcula después de descargar el ZIP; no necesito escribirlo en este Job.
La validación espera el éxito de referencias y operativos.
Todas las tareas usan `ALL_SUCCESS`.

Conservé una corrida concurrente, cola habilitada y `PERFORMANCE_OPTIMIZED`.
Los tiempos máximos son cero: no hay un timeout configurado en estos campos.
La exportación no declara reintentos explícitos ni parámetros generales del Job.
Tampoco incluye schedule, trigger, definición de cómputo, environments o librerías.
No deduzco su configuración efectiva de cómputo a partir de esos campos ausentes.

## Qué todavía falta

La versión fija impide seleccionar otra versión desde un parámetro general del Job.
Notebook 06 todavía no pertenece al grafo.
El cierre de 07 puede alimentar el planificador Silver, pero este Job no llama a Silver.
La exportación confirma configuración; no demuestra una nueva prueba de ejecución de notebooks 02–05.

Antes del coordinador prepararé una variante con parámetros explícitos:

| Parámetro | Uso previsto |
| --- | --- |
| `repo_root` | Localizar el repositorio completo en Workspace. |
| `catalog`, `schema` | Elegir las tablas del entorno. |
| `raw_volume`, `staging_volume` | Elegir las zonas de archivos. |
| `feed_version` | Recibir la versión seleccionada por descubrimiento. |
| `coordinator_run_id` | Vincular el cierre de 07 con el coordinador. |

Activaré `require_task_values=true` en Raw y validación dentro de esa variante.
Mantendré las referencias de versión y hash desde Raw para las tareas posteriores.
No añadiré un hash fijo como parámetro general.
La plantilla fiel conserva los parámetros originales hasta implementar y comprobar esa variante.

## Mi siguiente incremento

1. Implementé localmente notebook 06 para distinguir pendientes, completados y bloqueos mediante evidencia Bronze completa.
2. Separé la selección automática del reprocesamiento explícito.
3. Añadí entrega optativa de un lote acotado mediante task values.
4. La ausencia de novedades produce `NO_WORK`; falta comprobarlo en Workspace.
5. Probaré notebooks 02–05 y el flujo con trabajo antes de habilitar el coordinador.

No consideraré completo un snapshot solamente porque existen filas en rutas.
No excluiré automáticamente una versión con intentos incompletos sin revisar su evidencia.
No usaré una comparación del portal como sustituto del hash real del ZIP.
El [plan de orquestación](orchestration_plan.md) conserva el diseño del coordinador y sus pruebas pendientes.

## Cómo reutilizo la plantilla

Reemplazo `/Workspace/REPO_ROOT` por la raíz real del repositorio, fuera de Git.
Conservo los nombres de notebooks sin extensión, como aparecen en esta exportación.
Verifico las rutas reales antes de crear o actualizar cualquier Job.
No importo esta plantilla como un Job adicional sin revisar el riesgo de escritores simultáneos.
La comprobación local valida JSON, dependencias y referencias; no sustituye una validación en Databricks.

La [guía de descubrimiento](bronze_discovery.md) contiene los campos para mi primera comprobación.

## Variante parametrizada: preparación local

La [variante parametrizada](../databricks/jobs/gtfs_bogota_bronze_parameterized.template.json) conserva las cinco tareas y el paralelo existente.
Añade solamente `requested_feed_version` como parámetro general, con default 2025-10-28.
Raw traduce ese parámetro a su widget `feed_version`.
Las otras cuatro tareas siguen recibiendo versión y hash desde los task values de Raw.
Exijo la entrega de task values en Raw y validación mediante `require_task_values=true`.
No añado descubrimiento, un For each ni una llamada a Silver en este incremento.
La plantilla original conserva la exportación anterior para comparación.
No desplegué esta variante desde el agente.

Elegí un nombre distinto para la versión solicitada.
Un parámetro general llamado `feed_version` reemplazaría el valor del mismo nombre definido en las tareas.
Así conservo explícitamente la versión entregada por Raw para el resto de la cadena.
No creo un parámetro general `snapshot_sha256`.
La [documentación de parámetros](https://docs.databricks.com/aws/en/jobs/job-parameters) describe esa precedencia.

### Cambio manual del Job existente

1. Abro `gtfs_bogota_bronze_manual` y edito sus parámetros generales.
2. Añado `requested_feed_version`, inicialmente con 2025-10-28.
3. En `raw_gtfs`, reemplazo su valor fijo de `feed_version` por `{{job.parameters.requested_feed_version}}`.
4. En `raw_gtfs`, añado `require_task_values=true`.
5. En `validar_bronze`, añado `require_task_values=true` y conservo las referencias de versión y hash desde Raw.
6. Conservo los parámetros de versión y hash de las otras tres tareas.
7. Guardo y solicito una ejecución con `requested_feed_version=2026-09-29`.
8. Reviso el resultado de calidad y los indicadores de reutilización antes de continuar.

Si ya existe un parámetro general `feed_version` o `snapshot_sha256`, reviso su colisión antes de ejecutar.
La exportación de partida no contenía esos parámetros generales.
La configuración del entorno continúa usando los defaults comprobados del notebook o sus parámetros de tarea existentes.
Los parámetros generales de catálogo, Volumes y coordinador siguen previstos para la integración posterior.
No creo un segundo Job que pueda competir con el existente.
Sustituyo `/Workspace/REPO_ROOT` fuera de Git si utilizo la plantilla completa.

Para 2026 espero validación completa y elegibilidad para Silver, si las fuentes no cambiaron.
Las cinco advertencias de esquema conocidas son compatibles con esa elegibilidad.
Esta comprobación no equivale a procesar una versión nueva ni a comprobar el coordinador.

### Resultado de la comprobación 2026

El 14 de noviembre revisé la salida de la ejecución solicitada con 2026-09-29.
Su corrida de calidad es 6bccbeb8-4d57-4042-8ef7-5c81fa700bd3.
El cierre terminó WARNING con cero fallos, cinco advertencias, validación completa y elegibilidad para Silver.
Genie confirmó bronze_snapshot_v2 en STARTED y CLOSED y 69 controles reconciliados.
Las cinco advertencias corresponden a cambios de columnas ya conocidos frente a 2025.
La [evidencia](bronze_automation.md#comprobación-del-flujo-bronze-2026-y-contraste-mediante-genie) precisa el alcance.
No reexporté el Job modificado ni comprobé sus parámetros efectivos mediante Jobs API.
No afirmo que esta auditoría demuestre por sí sola cada ajuste de la interfaz.
El siguiente incremento prepara el Job principal y la entrega de listas desde descubrimiento.
