# Mi selección automática de trabajo Silver

**Estado:** recuperación y vista previa comprobadas; piloto NO_WORK del Job terminado con éxito en Workspace.
La prueba del Job con trabajo nuevo sigue pendiente.
**Fecha:** 13 de noviembre de 2026.
Este incremento implementa el pendiente 8b.
Todavía no conecta el descubrimiento de versiones ni el Job principal.

## Qué problema resuelvo

Antes copiaba versiones y hashes a cada For each.
Ahora notebook 11 calcula qué entidades necesitan trabajo.
Es como revisar pedidos entregados antes de preparar otra vez todos los paquetes.
El planificador distingue entregas completas, pendientes y bloqueadas.
Notebook 10 sigue validando y publicando cada entidad.

```text
Cierres Bronze + auditoría Silver + comprobación del destino
                         |
                    plan_silver / notebook 11
                         |
                  listas por entidad
                         |
             diez For each existentes / notebook 10
```

El planificador no descarga ZIP, transforma datos ni publica Silver.
La vista previa tampoco escribe auditorías ni tablas de control.
Solo la entrega al Job publica task values.
Las tareas ejecutoras sí conservan sus escrituras normales de publicación y auditoría.

## Archivos

| Archivo | Responsabilidad |
| --- | --- |
| gtfs_silver/planner.py | Decidir pendientes, dependencias, bloqueos y lotes mediante funciones sin Spark. |
| gtfs_silver/planner_runtime.py | Leer versiones Delta fijadas, comprobar destinos y entregar listas. |
| config/silver_planner.json | Declarar el rango de feeds y horizonte de service_dates. |
| notebooks/silver/11_plan_silver.ipynb | Ejecutar una vista previa o entregar el plan al Job. |
| jobs/gtfs_bogota_silver_planned.template.json | Variante optativa del Job con una tarea inicial y diez ciclos. |
| gtfs_silver/job_config.py | Generar la variante manual existente o la variante planificada. |
| gtfs_silver/pipeline.py | Comprobar el contexto del plan y registrar intentos antes de preparar datos. |
| notebooks/silver/10_publish_gtfs_entity.ipynb | Recibir los parámetros nuevos con defaults vacíos para conservar compatibilidad. |

No cambié el registro de contratos habilitados ni sus reglas de negocio.
La plantilla manual existente conserva sus diez tareas y listas fijas.
La selección automática no activa un horario; el lanzamiento del Job sigue siendo manual.

## Cómo decide

Primero selecciono el STARTED más reciente de cada pareja versión/hash.
Después busco su CLOSED, nunca un cierre exitoso más antiguo.
Exijo bronze_snapshot_v2, validación completa y ausencia de fallos bloqueantes.
Compruebo también la coherencia del inventario y la identidad del entorno.
Un intento incompleto, contradictorio o ambiguo bloquea su snapshot.
Mantengo las advertencias para los contratos Silver; no apruebo automáticamente esquemas incompatibles.

Después selecciono el intento Silver más reciente por entidad, versión y hash.
No filtro primero por SUCCEEDED ni por la regla actual.
Así no oculto fallos recientes o publicaciones que necesitan actualizar reglas.

Para considerar completa una publicación, compruebo:

- Estado SUCCEEDED, escritura confirmada, cero rechazos y métricas coherentes.
- Regla vigente y destino esperado.
- Conteo del snapshot igual al registrado en la auditoría.
- Un único silver_run_id en el destino, coincidente con esa auditoría.
- Una única silver_rule_version coincidente, sin procedencia técnica vacía.
- Ventana exacta en service_dates.
- Dependencias completas y sin publicaciones posteriores que invaliden el resultado conocido.

Una dependencia incluida antes en el mismo plan también habilita trabajo dependiente.
Si cambia una regla anterior o debo reprocesar una dependencia, incluyo sus dependientes.
No exijo que todas las tablas ya estén publicadas para planificar un feed nuevo.

La comparación temporal de dependencias es conservadora y usa los timestamps de auditoría disponibles.
Mantengo un solo escritor y evito ejecuciones manuales independientes durante el Job.
No implementé un bloqueo distribuido entre Jobs.
Los procesadores vuelven a validar sus dependencias reales antes de publicar.

## Estados de las decisiones

| Estado | Significado |
| --- | --- |
| COMPLETE | Auditoría y destino coinciden bajo la regla vigente. |
| PENDING | Falta una publicación, cambió su regla o necesita una dependencia reprocesada. |
| BLOCKED | Hay evidencia incompleta, fallo reciente, destino inconsistente o dependencia no disponible. |
| NOT_APPLICABLE | La fuente no publicó un archivo opcional. |
| OUT_OF_SCOPE | La derivación queda fuera del rango de feeds configurado. |
| DEFERRED | El snapshot excede el lote actual y conserva trabajo pendiente para otra corrida. |

El resumen devuelve READY, NO_WORK o BLOCKED.
NO_WORK produce diez listas vacías; no es un error.
BLOCKED impide entregar listas al Job, aunque otras decisiones estén sanas.
La vista previa conserva todas las razones para investigar.

Una tabla perdida o un intento FAILED/REJECTED/RUNNING requiere recuperación explícita.
No lo convierto silenciosamente en una publicación nueva.
Puedo reparar una tarea fallida con su plan vigente cuando la evidencia Bronze no cambió.
Si cambió, necesito un plan actualizado y resolver primero los bloqueos registrados.
Las entradas manuales existentes siguen disponibles para recuperación controlada.

## Horizonte de service_dates

El archivo de configuración declara feeds entre 2026-01-01 y 2026-12-31.
La ventana de análisis permanece entre 2026-01-01 y 2026-12-31.
No deduzco el horizonte automáticamente del año del feed.
Es una política explícita que permite nuevas versiones compatibles dentro del rango aprobado.
Los feeds de 2025 quedan OUT_OF_SCOPE solamente para esta derivación.
Las demás entidades de 2025 siguen siendo elegibles.
Un feed de 2027 necesitará una política deliberada para derivar service_dates.
Cambiar una ventana existente requiere migración explícita; el publicador tampoco la sustituye silenciosamente.

## Qué contiene cada trabajo

Cada elemento conserva entidad, versión, hash y expected_rule_version.
También incluye bronze_quality_run_id, bronze_result_sha256 y bronze_delta_version.
Las entidades fuente leen la versión Delta fijada en el cierre validado.
Una carga posterior de otra versión no cambia esa entrada.
Service_dates conserva sus fechas explícitas y lee sus dependencias Silver después de publicarlas.

Antes de preparar datos, notebook 10 vuelve a comprobar el cierre y la regla del plan.
Un plan obsoleto falla con una indicación para generar otro.
La tarea planificada registra RUNNING antes de preparar datos.
Si falla la preparación, registra FAILED; una interrupción conserva RUNNING.
Así el siguiente plan no reutiliza un éxito antiguo para ocultar ese intento.
Los ceros de esos intentos previos no representan un perfil ejecutado.
Las ejecuciones manuales sin contexto del plan conservan su comportamiento previo.
Las tareas planificadas requieren mode=publish; la vista previa corresponde a notebook 11.

## Costo y límites

No releo Bronze ni los TXT para construir el plan.
Leo auditorías y versiones de tablas fijadas.
Compruebo los destinos mediante una agregación distribuida por entidad y snapshots seleccionados.
Solo recupero agregados pequeños; no descargo filas de negocio al driver.
Esas agregaciones pueden leer millones de filas técnicas en tablas grandes.
No prometo costo constante ni una consulta exclusivamente de metadata.
Mediré el costo real antes de introducir una caché de comprobaciones o un manifiesto adicional.

Los conteos y metadatos técnicos no equivalen a comparar todos los valores de negocio.
Una alteración externa que conserve esas métricas podría escapar a esta comprobación.
El contrato operativo requiere que los destinos cambien mediante el publicador gobernado.
Las restauraciones y modificaciones externas necesitan reconciliación explícita.

Max_snapshots limita a veinte snapshots con trabajo por corrida, no a veinte filas arbitrarias del catálogo.
Los snapshots ya completos no consumen ese presupuesto.
La siguiente corrida vuelve a calcular pendientes y puede recoger los aplazados.
Max_metadata_rows limita a cinco mil registros por lectura acotada.
Si excedo ese límite, detengo el plan y pido acotar el rango; no lo trunco silenciosamente.
Cada lista tiene un límite preventivo de 45.000 bytes.
Databricks permite task values de hasta 48 KiB según su [documentación](https://docs.databricks.com/aws/en/jobs/task-values).

## Primera comprobación en Workspace

1. Sincronizo el repositorio completo después de publicar los cambios en Git.
2. Abro notebooks/silver/11_plan_silver.
3. Configuro repo_root con la raíz del repositorio en Workspace.
4. Conservo catalog=workspace y schema=gtfs_bogota en mi entorno actual.
5. Dejo feed_version_from y feed_version_to vacíos para revisar todos los cierres existentes.
6. Conservo max_snapshots=20 y max_metadata_rows=5000.
7. Mantengo emit_task_values=false.
8. Ejecuto Run all y reviso el resumen y las decisiones.

No necesito volver a ejecutar notebook 07 si su cierre sigue vigente.
NO_WORK es esperable cuando las publicaciones y dependencias coinciden.
PENDING también puede ser correcto si una dependencia se republicó después de su entidad dependiente.
No convierto ese resultado en un fallo sin revisar la razón concreta.
Esta primera comprobación no cambia el Job desplegado ni publica datos.

## Conectar el Job después de revisar la vista previa

La variante optativa añade plan_silver antes de publish_snapshots.
Conserva los diez ciclos seriales, su notebook 10 y concurrencia uno.
El generador usa --selection-mode auto; el modo por defecto sigue siendo manual.

```text
python -m gtfs_silver.job_config --repo-root /Workspace/REPO_ROOT --selection-mode auto --output /ruta/local/job.json
```

Configuro PYTHONPATH con databricks para usar ese comando fuera de Workspace.
REPO_ROOT es un marcador; el archivo generado para mi entorno permanece fuera de Git.
No uso el JSON como actualización remota hasta revisar las diferencias del Job existente.

| Ciclo | Inputs |
| --- | --- |
| publish_snapshots / agency | {{tasks.plan_silver.values.work_items}} |
| publish_routes | {{tasks.plan_silver.values.routes_work_items}} |
| publish_stops | {{tasks.plan_silver.values.stops_work_items}} |
| publish_calendar | {{tasks.plan_silver.values.calendar_work_items}} |
| publish_calendar_dates | {{tasks.plan_silver.values.calendar_dates_work_items}} |
| publish_service_dates | {{tasks.plan_silver.values.service_dates_work_items}} |
| publish_shape_points | {{tasks.plan_silver.values.shape_points_work_items}} |
| publish_trips | {{tasks.plan_silver.values.trips_work_items}} |
| publish_frequencies | {{tasks.plan_silver.values.frequencies_work_items}} |
| publish_stop_times | {{tasks.plan_silver.values.stop_times_work_items}} |

Las tareas internas reciben los campos del elemento mediante {{input.campo}}.
La plantilla incluye los campos nuevos y las fechas de service_dates.
La tarea inicial usa emit_task_values=true.
No necesito parámetros generales work_items cuando las listas vienen del planificador.
Evito parámetros generales feed_version o snapshot_sha256 que sustituyan los valores de cada iteración.
Antes de publicar con la variante, pruebo listas vacías y fallos en Free Edition.
Su comportamiento real en el Workflow sigue pendiente de comprobación.
No habilito un horario automático en este incremento.

## Verificación local

Pasaron 112 pruebas unitarias del proyecto.
Cuatro integraciones del planificador pasaron con Spark 4.0.1 y Delta 4.0.0 en Docker sin red.
El repositorio estuvo montado en modo de solo lectura y los temporales quedaron fuera de OneDrive.
Las integraciones comprueban lectura congelada de Bronze, conteos técnicos, fallo de preparación y cierre obsoleto.
También ejecutan notebook 11 completo en vista previa con tablas pequeñas de fixture.
La corrección final de una colisión de identificadores de fixture se comprobó en la suite unitaria.
No ejecuté toda la suite nativa Silver; limité las integraciones a los componentes modificados.
La vista previa de notebook 11 ya está comprobada en Workspace.
El piloto del camino NO_WORK ya terminó correctamente dentro del Job.
La prueba del Job con listas no vacías sigue pendiente.

Si la sesión ya importó módulos anteriores, reinicio Python después del Pull y ejecuto desde el bloque 1.
No necesito instalar ni reiniciar paquetes dentro de cada iteración del Job.

## Qué sigue después

La vista previa y el piloto NO_WORK del Job ya están comprobados en Workspace.
Luego adapto notebook 06 para descubrimiento y selección de ingesta.
La prueba pendiente de las guardas Bronze 02–05 permanece antes de habilitar ingesta automática.
La exportación completa del Job Bronze sigue pendiente.
El Job principal y Archify no cambian durante este incremento.

## Recuperación explícita de intentos abandonados

El primer ensayo en Workspace detectó un RUNNING antiguo de agency y una pareja Bronze incompatible sin cierre.
La [guía de recuperación](planner_recovery.md) documenta las verificaciones realizadas mediante Genie.
Notebook 18 prepara y aplica resoluciones operativas sin modificar los registros originales.
El planificador incorpora únicamente las decisiones explícitas que siguen coincidiendo con el intento observado.
Muestra RESOLVED y vuelve a evaluar la evidencia si el intento cambia o termina.
No equivale a ignorar automáticamente todos los RUNNING ni a declarar exitoso un intento fallido.

## Cierre de la vista previa en Workspace — 13 de noviembre de 2026

Después de aplicar las dos resoluciones obtuve diecinueve COMPLETE, un OUT_OF_SCOPE y dos RESOLVED.
No quedaron decisiones BLOCKED, PENDING ni DEFERRED en esa salida.
Service_dates de 2025 permanece fuera del horizonte acordado.
El resultado es coherente con NO_WORK; no necesito volver a publicar tablas completadas.
El [detalle de recuperación](planner_recovery.md) conserva evidencia y alcance.

Conecté plan_silver con los diez ciclos y comprobé una corrida NO_WORK del Workflow.
No habilité un horario automático; todavía falta una prueba con trabajo nuevo.

## Piloto del Job sin pendientes — 13 de noviembre de 2026

Ejecuté gtfs_bogota_silver_manual después de conectar el planificador con los diez ciclos.
La captura de Workspace mostró Succeeded.
Contrasté su historial mediante Genie en las tablas system.lakeflow.
Los resultados estructurados confirmaron SUCCEEDED para el Job y sus once tareas.

| Medición | Resultado |
| --- | --- |
| Inicio UTC | 2026-11-13T21:09:57.123Z |
| Fin UTC | 2026-11-13T21:12:00.382Z |
| Ventana en Bogotá | 13 de noviembre, 16:09:57 a 16:12:00. |
| Duración observada del Job | 123,259 segundos; aproximadamente 2 minutos y 3 segundos. |
| Duración observada de plan_silver | 102,584 segundos; aproximadamente 1 minuto y 43 segundos. |
| Tareas del Job | plan_silver y diez contenedores publish_*, todos SUCCEEDED. |

La tabla del plan mostró diecinueve COMPLETE, un OUT_OF_SCOPE y dos RESOLVED.
No mostró BLOCKED, PENDING ni DEFERRED.
El motor corresponde a NO_WORK y genera listas vacías bajo ese resultado.
Esta evidencia permite cerrar el piloto del camino sin pendientes.

Conservo estos límites:

- COUNT(DISTINCT run_id)=1 representa una ejecución de cada tarea registrada, no una iteración del ciclo.
- La consulta de esa corrida no devolvió claves process_* ni publish_iteration en el ámbito consultado.
- No convierto esa ausencia, por sí sola, en prueba universal de cero iteraciones.
- La muestra de parámetros consultada no expone el array For each resuelto ni un contador de iteraciones.
- No atribuyo ausencia de parámetros a todas las tareas desde esa única muestra.
- No ejecuté un escaneo independiente para demostrar ausencia de escrituras analíticas durante esta corrida.
- Esta duración describe un piloto sin pendientes, no el tiempo de cargar un feed nuevo.

La conversación Genie de verificación es edec728c7025452686e59a6eed8dc7bd.
La respuesta verificada es 0c747150192c4326b29d859e9e285d27.
No consulté tablas de negocio para contrastar el historial del Job.
La prueba con trabajo nuevo, el descubrimiento dinámico y el coordinador permanecen pendientes.

Después de confirmar que todos los Inputs usan tasks.plan_silver.values, puedo retirar los parámetros generales *_work_items antiguos.
No cambio los task values generados por el planificador ni los parámetros de las tareas internas.
