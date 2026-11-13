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
