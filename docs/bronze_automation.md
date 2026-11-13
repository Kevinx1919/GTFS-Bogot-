# Mi preparación de Bronze para automatización

**Estado:** cierre de notebook 07 comprobado en Workspace para ambos snapshots.
Los cambios de descarga y carga de notebooks 02–05 mantienen su prueba de despliegue pendiente.
**Fecha:** 12 de noviembre de 2026.
Este incremento prepara el pendiente 8b. Todavía no instala el planificador ni el Job principal.

## Qué cambia

Uso los mismos notebooks 02, 03, 04, 05 y 07 del Job Bronze.
Comparto su lógica en databricks/gtfs_bronze.
Mantengo Bronze append-only y las columnas fuente como string.
No cambio tablas Silver ni elimino auditorías antiguas.

| Archivo | Responsabilidad |
| --- | --- |
| gtfs_bronze/contracts.py | Identidad, decisión de reutilización, controles esperados y contrato del cierre. No necesita Spark. |
| gtfs_bronze/runtime.py | Integridad de archivos, reintentos HTTP, cargas Delta y persistencia idempotente de auditoría. |
| gtfs_bronze/__init__.py | Declara el paquete Python. |

Los notebooks siguen siendo las entradas del Job.
Necesitan el repositorio completo sincronizado, igual que notebook 10 de Silver.
Repo_root indica la raíz del repositorio en Workspace, nunca una ruta de Windows.
Si el directorio actual permite localizar el repositorio, puedo dejar repo_root vacío.

## Integridad y carga

Notebook 02 calcula el hash del payload descargado.
El cargador verifica ese hash antes de reutilizar un ZIP Raw existente.
Un ZIP distinto o incompleto detiene la corrida; no lo sobrescribe.
Los reintentos HTTP cubren errores de red, timeout, 429, 500, 502, 503 y 504.
El límite inicial es tres intentos con esperas acotadas de uno y dos segundos.
Un 404 detiene la descarga sin repetirla.

Notebook 03 comprueba el hash del ZIP Raw antes de extraer.
Compara cada TXT reutilizado contra el miembro correspondiente del ZIP.
Un nombre o tamaño coincidente no basta para demostrar integridad.
Una copia Staging inconsistente detiene la corrida y requiere reconstrucción explícita de esa copia derivada.
Un fallo durante una escritura inicial puede dejar un archivo parcial.
El siguiente intento lo detecta; no promete reparación automática ni atomicidad del sistema de archivos.

El cargador compartido compara el conteo fuente con las filas Bronze del hash.
Comprueba también la versión de procedencia.

| Situación | Decisión |
| --- | --- |
| Fuente con filas y sin evidencia cargada | Append Delta y lectura posterior de confirmación. |
| Mismo hash, misma versión y mismo conteo | Reutilización sin insertar otra copia. |
| Conteo diferente para un hash existente | Bloqueo visible; no añadir todo el archivo otra vez. |
| Mismo hash con versión nula o diferente | Bloqueo de identidad; mantener el histórico. |
| Misma versión con otro hash | Snapshot separado. |
| Archivo publicado sin filas | Bloqueo bajo el contrato actual. |

Conservo temporalmente la política de un hash asociado a una sola versión en cada tabla.
Es compatible con los lectores actuales de Silver, que también seleccionan por hash.
No habilito alias de versión sin revisar juntos todos los lectores y contratos.

Las escrituras nuevas usan txnAppId y txnVersion como protección adicional de reintentos Delta.
No uso su retención como sustituto del conteo y la procedencia.
Mantengo un solo escritor por snapshot y tabla.
El límite de un Job no bloquea ejecuciones manuales independientes.
No presento este diseño como un bloqueo distribuido entre Jobs.

Retiro persist obligatorio de las cargas compartidas.
Show_diagnostics=false evita perfiles, muestras ordenadas e historiales adicionales.
La compuerta 07 conserva sus validaciones obligatorias.
El conteo fuente de 07 es deliberado: comprueba la carga contra Staging de forma independiente.
No prometo una reducción de tiempo sin medir el Job en Workspace.

## Mi comprobante de preparación

Creo audit_gtfs_bronze_snapshot_runs al ejecutar el nuevo notebook 07.
Su grano es una fila por quality_run_id y event_type.
Cada validación completa produce dos eventos append-only:

```text
STARTED / RUNNING
        |
        +-- todos los controles terminan --> CLOSED / PASSED, WARNING o FAILED
        |
        +-- error inesperado o interrupción --> queda STARTED sin CLOSED
```

El cierre solo aparece después de persistir todos los checks.
No hay una transacción conjunta entre ambas tablas.
Si falla la escritura del cierre, los checks pueden existir sin un snapshot preparado.
Un intento incompleto nunca equivale a éxito.
El planificador deberá seleccionar primero el intento más reciente del snapshot y buscar después su cierre.
No podrá buscar simplemente cualquier cierre exitoso antiguo.

| Campo | Significado |
| --- | --- |
| quality_run_id | Identidad de esta evaluación. |
| event_type | STARTED o CLOSED. |
| source_feed_version / source_sha256 | Identidad de la fuente evaluada. |
| rule_version | bronze_snapshot_v2. |
| started_at_utc / completed_at_utc | Inicio y cierre UTC; el inicio conserva cierre nulo. |
| status | RUNNING, PASSED, WARNING o FAILED. |
| validation_completed | Todos los bloques y controles esperados terminaron. |
| ready_for_silver | La evaluación completa no tiene fallos bloqueantes. |
| total_checks / blocking_failures / warning_count | Conteos del resultado canónico. |
| warning_policy | silver_contracts_v1: Silver aplica después sus contratos. |
| entity_inventory_json | Presencia, conteos, columnas y versión Delta por entidad. |
| result_sha256 | Huella del resultado lógico, sin UUID ni timestamps variables. |
| coordinator_run_id | Identidad opcional del futuro coordinador. |

Ready_for_silver habilita la validación Silver; no aprueba automáticamente una publicación.
WARNING mantiene el comportamiento existente del Job Bronze.
Las advertencias siguen visibles y los contratos Silver rechazan campos o valores incompatibles.
No convierto esta señal en autorización para aceptar cualquier esquema nuevo.

Notebook 07 fija versiones Delta de las tablas leídas.
También reconcilia el conteo de cada archivo publicado con su entidad Bronze.
No exige archivos opcionales ausentes ni inventa filas.
El conteo exacto y la procedencia no son una comparación completa de todos los valores fuente.
La integridad de Raw y Staging corresponde al notebook 03 del flujo.
Una modificación posterior de tablas o archivos exige revalidación; el cierre describe las entradas registradas.

## Idempotencia de la auditoría

La clave del check es quality_run_id, check_name, entity_name y severity.
Repetir el bloque final con el mismo resultado no añade otra copia.
Cambiar el resultado bajo la misma clave provoca un error.
Para una nueva evaluación ejecuto desde el bloque 1 y obtengo otro quality_run_id.
No reutilizo una corrida anterior para ocultar cambios.

Los bloques 4, 5 y 6 invalidan sus resultados dependientes en memoria.
Así evito cerrar una mezcla de controles anteriores y nuevos.
El cierre exige el conjunto exacto de controles y las doce entidades del contrato.
No depende de un número fijo de filas de auditoría.
Las copias históricas antiguas permanecen visibles; este incremento no las elimina.

## Cómo comprobarlo en Databricks

1. Sincronizo el repositorio completo con los módulos y notebooks actualizados.
2. Compruebo las rutas reales del Job; la exportación JSON completa sigue pendiente.
3. Configuro repo_root si la detección automática no encuentra el repositorio.
4. Ejecuto notebook 07 completo con la versión y hash existentes de 2025.
5. Compruebo el resumen y los eventos STARTED y CLOSED de su quality_run_id.
6. Repito solo el bloque final y compruebo que no aumenten sus checks.
7. Ejecuto notebook 07 completo con la versión y hash existentes de 2026.
8. Compruebo las advertencias y el cierre, antes de avanzar al planificador.

La comprobación del cierre no requiere descargar otra vez los ZIP ni ejecutar todos los cargadores.
Sí requiere releer los TXT Staging y las entidades Bronze para reconciliar los conteos.
Para probar también integridad y reutilización de las cargas, ejecuto 03, luego 04/05, y finalmente 07.
Uso snapshots existentes y un único escritor.
Las cargas completas deben mostrar reutilización y conservar sus conteos.
Notebook 02 queda preparado para la siguiente descarga; su prueba HTTP local usa dobles.

Para actualizar parámetros del Job existente:

| Ámbito | Parámetro | Valor o procedencia |
| --- | --- | --- |
| General | repo_root | Raíz real del repositorio en Workspace. |
| General | catalog / schema | workspace / gtfs_bogota en mi entorno actual. |
| General | raw_volume / staging_volume | raw_gtfs / staging_gtfs. |
| General | show_diagnostics | false. |
| General | require_task_values | true para exigir entrega de valores dentro del Job. |
| Raw | feed_version | Versión solicitada. |
| Tareas 03, 04, 05 y 07 | feed_version | {{tasks.raw_gtfs.values.feed_version}} |
| Tareas 03, 04, 05 y 07 | snapshot_sha256 | {{tasks.raw_gtfs.values.snapshot_sha256}} |

No creo un hash fijo general que sustituya el hash calculado por Raw.
El modo interactivo usa require_task_values=false.
Si el Job usa true, un error al publicar task values detiene la tarea.
El notebook 03 ya no aprovisiona el volumen durante cada ingesta.
El volumen debe existir previamente.

Para ver el intento más reciente de cada snapshot:

```sql
with latest_attempt as (
  select quality_run_id, source_feed_version, source_sha256, rule_version, started_at_utc,
         row_number() over (
           partition by source_feed_version, source_sha256
           order by started_at_utc desc, quality_run_id desc
         ) as position
  from workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_runs
  where event_type = 'STARTED'
)
select a.source_feed_version, a.source_sha256, a.quality_run_id, a.rule_version,
       coalesce(c.status, 'INCOMPLETE') as status,
       coalesce(c.ready_for_silver, false) as ready_for_silver,
       c.total_checks, c.blocking_failures, c.warning_count
from latest_attempt a
left join workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_runs c
  on a.quality_run_id = c.quality_run_id and c.event_type = 'CLOSED'
where a.position = 1;
```

Esta consulta nueva es una guía local; todavía no tiene ejecución documentada en Workspace.
El planificador comprobará además regla vigente, dependencias y estado del destino.

## Cierre comprobado en Workspace — 13 de noviembre de 2026

Ejecuté notebook 07 completo para ambos snapshots con bronze_snapshot_v2.
Obtuve estos resultados después de la persistencia del cierre:

| Snapshot | Resultado | Fallos bloqueantes | Advertencias | Validación completa | Elegible para validar Silver |
| --- | --- | --- | --- | --- | --- |
| 2025-10-28 | PASSED | 0 | 0 | true | true |
| 2026-09-29 | WARNING | 0 | 5 | true | true |

Ambas salidas identifican workspace.gtfs_bogota.audit_gtfs_bronze_snapshot_runs como destino del cierre.
En 2026 comprobé también el detalle de source_row_count_matches:

| Entidad | Conteo Bronze reconciliado con Staging |
| --- | ---: |
| agency | 7 |
| calendar | 7 |
| calendar_dates | 133 |
| fare_attributes | 1 |
| feed_info | 1 |
| frequencies | 14 |
| routes | 1.045 |
| shapes | 926.501 |
| stop_times | 9.408.893 |
| stops | 8.314 |
| trips | 181.060 |

Fare_rules no está publicado en este snapshot; su ausencia aparece como NOT_APPLICABLE.
Las cinco advertencias de esquema afectan agency, routes, stop_times, stops y trips.
Los controles de referencias mostrados terminan en PASS con cero claves huérfanas.
Severity=WARNING no representa una advertencia efectiva cuando status=PASS.
El contador usa status=WARN.

Conservo el alcance de esta comprobación:

- Confirma la ejecución completa del nuevo notebook 07 y su resumen de cierre en Workspace.
- El detalle de reconciliación corresponde a 2026; para 2025 conservo el resumen final.
- No incluye una consulta independiente de los eventos STARTED/CLOSED ni sus quality_run_id.
- No confirma todavía la repetición aislada del bloque final sin nuevas filas.
- No comprueba los cambios de descarga, extracción y carga de notebooks 02–05.

La prueba del cierre permite iniciar el planificador 8b.
No necesito ejecutar otra vez una validación correcta solo para repetir estas salidas.
La consulta directa de auditoría puede formar parte de la comprobación de lectura del planificador.

## Verificación local y alcance

Pasaron 97 pruebas unitarias del proyecto y tres pruebas de integración Bronze con Spark/Delta reales.
La selección unitaria excluyó explícitamente 85 casos nativos.
Ejecuté por separado los tres casos nativos que cubren este incremento.
No presento las otras pruebas nativas de Silver como ejecutadas completamente.

Las pruebas de integración cubren carga repetida, histórico, identidad, carga parcial, cierre idempotente y contradicciones.
También ejecutan notebook 07 completo con archivos pequeños de fixture.
Las pruebas de archivos detectan corrupción Raw y cambios Staging del mismo tamaño.
Los reintentos HTTP usan un cliente simulado y no consumen la API real.
Comprobé sintaxis, ausencia de outputs y git diff --check.

Usé apache/spark:4.0.1-python3 y JARs Delta 4.0.0 ya disponibles.
El contenedor no tuvo red y montó el repositorio en modo de solo lectura.
Sus archivos y dependencias quedaron fuera de OneDrive.
El intento ampliado en Windows falló al preparar Spark por incompatibilidad Java/Hadoop, antes de ejecutar esos casos.
Detuve deliberadamente la ampliación nativa Linux sobre entidades Silver sin cambios.
La verificación final se limita a las 97 pruebas unitarias y las tres integraciones Bronze aprobadas.
Estas pruebas locales no sustituyen la comprobación de Workspace descrita en la sección anterior.

Comando unitario para Raw/Bronze sin Spark:

```powershell
py -B -m unittest discover -s tests -p "test_bronze*.py" -v
```

Sin el entorno Spark, ese comando omite tres casos explícitamente.
Para ejecutarlos en Linux preparo PySpark/Java y los JARs locales fuera del repositorio.
Configuro GTFS_DELTA_TEST_JARS y PYSPARK_SUBMIT_ARGS con ambos JARs.
Entonces ejecuto:

```text
python3 -B -m unittest test_bronze_runtime.BronzeDeltaTests -v
```

Necesito incluir tests y las dependencias en PYTHONPATH, como describe la guía de pruebas de Silver.

## Qué sigue

El cierre ya está comprobado para ambos snapshots; el siguiente incremento es implementar plan_silver.
Ese planificador leerá los intentos, sus cierres y la auditoría Silver.
Sustituirá las listas fijas por pendientes calculados.
Después adaptaré notebook 06 y crearé el Job principal.
Notebook 01 mantiene sus correcciones Realtime pendientes en otro incremento.
No cambio Archify ni habilito horarios automáticos durante esta transición.

## Referencias

- [Plan de orquestación](orchestration_plan.md).
- [Revisión previa](bronze_review_2026_11_12.md).
- [Opciones Spark de Databricks](https://docs.databricks.com/aws/en/spark/api-options): txnAppId y txnVersion.
- [Caché serverless](https://docs.databricks.com/aws/en/compute/serverless/dataframe-cache): requisitos dependientes de versión del entorno.
