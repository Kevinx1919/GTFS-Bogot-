# Mi descubrimiento de pendientes Bronze

**Estado:** implementación local; falta comprobar notebook 06 en Workspace.
No modifiqué el Job desplegado ni habilité programación.

## Qué resuelve

Notebook 06 consulta el catálogo oficial y prepara versiones para ingesta.
No descarga ZIP, extrae TXT ni publica tablas Bronze o Silver.
Sí actualiza las tablas de control y observaciones del catálogo.
La vista previa del plan no significa una ejecución sin escrituras de metadata.

Antes consideraba cargada una versión cuando encontraba rutas.
Ahora compruebo el cierre completo `bronze_snapshot_v2` que también usa el planificador Silver.
Es como revisar el recibo completo de una entrega, en lugar de comprobar una sola caja.

```text
Catálogo oficial
      ↓
Metadata de control y observaciones
      ↓
Últimos intentos Bronze y resoluciones vigentes
      ↓
Decisiones: COMPLETE / PENDING / BLOCKED / DEFERRED
      ↓
Lista acotada de versiones, todavía sin hash
      ↓ futuro coordinador
Job Bronze: 02 → 03 → 04/05 → 07
```

## Cómo decido

| Evidencia | Decisión |
| --- | --- |
| Cierre completo, coherente y elegible, con reglas vigentes | `COMPLETE`; no vuelvo a descargar. |
| Versión sin cierre ni evidencia de cargas | `PENDING`; Raw calculará su hash. |
| Nuevo intento sin cierre después de un éxito | `BLOCKED`; no rescato el éxito anterior para esconderlo. |
| Cierre fallido, inventario inválido o identidad incoherente | `BLOCKED`; reviso la evidencia. |
| Filas Bronze u observaciones de esquema, sin cierre vigente | `BLOCKED`; reviso o completo notebook 07 antes de planificar. |
| Dos URLs distintas con la misma fecha máxima de modificación | `BLOCKED`; no elijo una arbitrariamente. |
| Ítem sin ZIP directo válido | `BLOCKED`; no intento descargar su página como un archivo. |
| Metadata del portal posterior al cierre válido | `PENDING`; vuelvo a comprobar el ZIP mediante Raw. |
| Versión completada y reprocesamiento explícito habilitado | `PENDING`; mantengo las guardas de identidad e idempotencia. |
| Pendiente fuera del cupo de esta ejecución | `DEFERRED`; permanece visible para el siguiente lote. |

Reutilizo las resoluciones de notebook 18 antes de elegir el último intento.
Una resolución pierde su exclusión cuando cambia el intento observado o aparece su cierre.
No borro intentos ni marco un fallo como satisfactorio.
El reprocesamiento explícito tampoco omite estos controles.

## Parámetros

| Campo | Valor inicial | Uso |
| --- | --- | --- |
| `repo_root` | vacío | Localizar el repositorio completo en Workspace. |
| `catalog` | `workspace` | Catálogo de mi entorno actual. |
| `schema` | `gtfs_bogota` | Schema de control, auditoría y Bronze. |
| `selection_mode` | `latest_uningested` | Elegir la política del lote. |
| `explicit_version` | vacío | Versión exacta para selección explícita. |
| `start_date`, `end_date` | vacíos | Rango inclusivo; configuro ambos juntos. |
| `max_versions` | `1` | Cupo entre 1 y 20 versiones. |
| `max_metadata_rows` | `5000` | Límite de catálogo y lecturas; entre 1 y 10000. |
| `reprocess_completed` | `false` | Solicitar de nuevo versiones completadas en modo explícito o backfill. |
| `emit_task_values` | `false` | Entregar listas al Job cuando estoy listo para comprobarlo. |

Los valores de catálogo y schema son defaults de mi entorno, no nombres obligatorios del sistema.
La configuración pública del proveedor vive en `databricks/config/static_gtfs_catalog.json`.
No incluye credenciales ni rutas personales.

`latest_uningested` selecciona solamente la versión pendiente más reciente.
Puedo acotar su búsqueda con inicio y fin.
`backfill_range` selecciona pendientes del rango, desde la versión más antigua, hasta alcanzar el cupo.
`explicit_version` permite revisar una versión aunque ya tenga rutas o un cierre completo.
Una versión explícita inexistente produce un error; no la confundo con ausencia de novedades.

Para repetir un snapshot completo uso `reprocess_completed=true` con versión explícita o backfill.
Mantengo ese valor deshabilitado durante la selección automática normal.
No ejecuto backfill de todo el catálogo sin elegir deliberadamente su rango.

## Salidas

El plan devuelve `READY`, `NO_WORK` o `BLOCKED`.
Un bloqueo dentro del alcance impide entregar todo el lote al Job.
Conservo sus decisiones para revisarlas antes de corregir la evidencia.
Un fallo HTTP o un catálogo vacío inesperado produce error, no `NO_WORK`.

Con `emit_task_values=true` publico:

| Clave | Contenido |
| --- | --- |
| `ingestion_work_items` | Lista JSON de objetos con `feed_version`. |
| `ingestion_plan_status` | `READY` o `NO_WORK`. |
| `planned_count` | Tamaño de la lista entregada. |
| `deferred_count` | Pendientes fuera del cupo. |

Ejemplo de trabajo:

```json
[{"feed_version": "2026-09-29"}]
```

No añado un hash supuesto.
Raw calcula el SHA-256 del ZIP recibido y entrega su identidad a las tareas siguientes.
`NO_WORK` entrega una lista vacía válida.
La serialización queda por debajo de 45000 bytes.

## Costos y límites

Las lecturas fijan versiones Delta y acotan los registros recogidos en el driver.
No trunco silenciosamente un catálogo ni una auditoría que superen el límite.
Para versiones sin intentos vigentes, reviso procedencia en observaciones de esquema y tablas Bronze existentes.
Proyecto solamente la versión fuente y busco valores distintos del alcance pendiente.
Estas consultas pueden leer archivos grandes; no prometo costo exclusivo de metadata.
Evito esos recorridos para versiones que ya tienen un intento de validación evaluable.

El cierre certifica la evaluación registrada; no vuelvo a contar todas las entidades para planificar.
Mantengo archivos y tablas gobernados y un solo escritor durante la comprobación.
No ofrezco una transacción conjunta entre tablas ni un bloqueo distribuido.

El control conserva ítems históricos del portal; no elimino automáticamente los que dejan de aparecer.
Un cambio de metadata motiva una reconsulta, pero no demuestra cambios del ZIP.
Un cambio silencioso del ZIP sin metadata nueva exige una reconsulta explícita.
Los cargadores siguen bloqueando el mismo hash asociado a otra versión.

La consulta HTTP reintenta errores temporales mediante el helper Bronze existente.
Rechazo paginación repetida, límites excedidos y respuestas parciales.
Consolido ítems idénticos y rechazo metadata contradictoria para el mismo identificador del portal.

## Mi primera comprobación en Databricks

1. Sincronizo el repositorio completo después del próximo commit y push.
2. Abro notebook 06 y ejecuto el primer bloque para mostrar sus widgets.
3. Configuro `selection_mode=explicit_version` y `explicit_version=2026-09-29`.
4. Dejo vacíos `start_date` y `end_date`.
5. Mantengo `reprocess_completed=false` y `emit_task_values=false`.
6. Configuro catálogo, schema y raíz del repositorio según mi entorno.
7. Ejecuto Run all para releer parámetros y construir un plan nuevo.
8. Reviso el resultado y la decisión de esa versión.

Espero `COMPLETE` y `NO_WORK` si el cierre válido no cambió y el portal no publicó metadata posterior.
Si aparece otro estado, reviso su razón antes de conectar el Job.
Repito la comprobación explícita con 2025-10-28.
Todavía no sustituyo los Inputs del Job Silver: este plan corresponde a ingesta Bronze.
Después comprobaré la entrega de task values y una ingesta controlada con trabajo.
El coordinador sigue pendiente hasta verificar este incremento.

## Comprobación local

Pasaron 128 pruebas unitarias y tres integraciones seleccionadas con Spark/Delta reales.
Las integraciones comprueban bootstrap, procedencia sin cierre, último intento incompleto y límites de metadata.
También ejecutan los seis bloques de notebook 06 con una respuesta HTTP sintética.
Comprueban dos corridas: control sin duplicar el ítem y una observación adicional por corrida.
La segunda corrida entrega task values; la primera mantiene deshabilitada esa entrega.
La imagen offline no incluía requests; corregí el doble HTTP de la prueba sin instalar paquetes.
No consulté el portal real ni ejecuté el notebook en Databricks durante estas pruebas.
