# Mi recuperación de intentos sin cierre

**Fecha:** 13 de noviembre de 2026.
**Estado:** ambas resoluciones aplicadas en Workspace; nueva vista previa del planificador sin bloqueos.
No modifiqué estados mediante Genie ni ejecuté escrituras remotas desde el agente.

## Qué encontré

El planificador mostró catorce decisiones COMPLETE, cinco bloqueos de entidades de 2025 y un bloqueo Bronze adicional.
Service_dates de 2025 permaneció OUT_OF_SCOPE, según la ventana acordada.
Las diez entidades del snapshot correcto de 2026 aparecieron COMPLETE.

Genie confirmó dos situaciones:

| Situación | Evidencia |
| --- | --- |
| Agency 2025 | El último intento e822a733-ed4c-4f17-93e7-c02fddae82bf quedó RUNNING, sin cierre ni error registrado. |
| Publicación conservada | Silver mantiene siete filas de agency_v1, asociadas al SUCCEEDED 7f01ccfa-0f93-4f9e-93bb-fbfc1478cbe4. |
| Identidad Bronze incompatible | El intento 096d0f14-5165-43d1-9c8c-c7b0ee041221 combina 2026-09-29 con el hash de 2025. Solo tiene STARTED. |
| Procedencia comprobada | Bronze agency y once encabezados observados asocian ese hash a 2025-10-28. |
| Checks del intento incompatible | Cero registros en la auditoría de calidad para ese quality_run_id. |
| Parejas correctas | Los cierres reales de 2025 y 2026 terminaron PASSED y WARNING, respectivamente. |

RUNNING en la auditoría no demuestra que un proceso siga ejecutándose.
Confirmé que las ejecuciones ya terminaron o fueron detenidas.
No conozco el origen exacto del cruce de parámetros; no lo atribuyo automáticamente a los widgets.
Tampoco afirmo que el intento RUNNING nunca ejecutó un commit histórico.
Compruebo que el destino actual conserva la publicación anterior identificada.

Cambiar RUNNING a FAILED no desbloquea este diseño: ambos estados impiden reutilizar un éxito antiguo.
No necesito republicar agency y sus dependientes solamente para resolver un registro abandonado.
Necesito una decisión administrativa explícita respaldada por el destino conservado.

## Qué añado

El notebook manual 18_recover_pipeline_attempts prepara o aplica esas decisiones.
La lógica está en gtfs_silver/planner_recovery.py.
La nueva tabla audit_gtfs_attempt_resolutions conserva una fila por capa, entidad, snapshot e intento resuelto.
Su grano no representa datos de transporte.

La decisión registra identificador, motivo, operador, fecha UTC, estado observado y evidencia de referencia.
INVALID_IDENTITY corresponde al intento Bronze con identidad incompatible.
ABANDONED corresponde al intento Silver sin cierre que conserva otra publicación exitosa verificada.
No cambio el estado original ni elimino sus registros.
El planificador muestra RESOLVED cuando aplica una decisión explícita vigente.

Es como conservar una solicitud inconclusa y añadir una nota firmada que explica su resolución.
La nota no convierte la solicitud original en un éxito.

## Condiciones que vuelvo a comprobar

Para Bronze exijo que el intento siga siendo el último STARTED sin CLOSED de esa pareja.
También exijo un cierre válido que vincule el hash a otra versión.
Debe existir una pareja correcta, inequívoca y validada para la versión solicitada.
No permite descartar cualquier ingesta incompleta.

Para Silver exijo el último RUNNING, sin cierre ni escritura confirmada en su auditoría.
El destino debe coincidir con una publicación anterior única y exitosa.
Compruebo su conteo, silver_run_id y silver_rule_version.
Las comprobaciones técnicas no sustituyen una comparación de todos los valores de negocio.
Mantengo el requisito de destinos modificados mediante el publicador gobernado.

Si el intento cambia de estado o aparece un CLOSED, la resolución deja de excluirlo.
El planificador vuelve a evaluarlo y puede bloquearlo.
Antes de aplicar deben haber terminado o detenido las ejecuciones.
El notebook no detiene procesos ni implementa un bloqueo distribuido.

## Pasos para los dos casos comprobados

Primero sincronizo el repositorio completo después de publicar los cambios.
Si la sesión importó módulos anteriores, reinicio Python y ejecuto desde el bloque 1.
Abro notebooks/silver/18_recover_pipeline_attempts.

| Campo | Primera ejecución |
| --- | --- |
| repo_root | Raíz real del repositorio en Workspace. |
| catalog | workspace |
| schema | gtfs_bogota |
| mode | preview |
| confirm_executions_stopped | false; preview no escribe. |
| resolutions_json | El JSON siguiente. |

```json
[
  {
    "layer": "bronze",
    "entity": "*",
    "feed_version": "2026-09-29",
    "sha256": "07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952",
    "attempt_run_id": "096d0f14-5165-43d1-9c8c-c7b0ee041221",
    "reason": "Sin ejecuciones activas. Pareja incompatible; hash y version correctos verificados mediante cierres independientes."
  },
  {
    "layer": "silver",
    "entity": "agency",
    "feed_version": "2025-10-28",
    "sha256": "07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952",
    "attempt_run_id": "e822a733-ed4c-4f17-93e7-c02fddae82bf",
    "reason": "Sin ejecuciones activas. Intento sin cierre; destino anterior SUCCEEDED conservado y verificado."
  }
]
```

Ejecuto Run all en preview y reviso ambas evidencias.
Después uso mode=apply y confirm_executions_stopped=true, manteniendo los demás valores.
Run all vuelve a comprobar ambos casos antes de escribir sus decisiones.
Las resoluciones no forman una transacción conjunta.
Si una escritura falla, conservo las ya aplicadas y reviso la pendiente.
Repetir la misma resolución es idempotente; no añade otra copia.

Finalmente ejecuto notebook 11 con emit_task_values=false.
Compruebo las decisiones RESOLVED y que los bloqueos anteriores desaparezcan.
Puede aparecer trabajo PENDING si existen dependencias republicadas; reviso sus motivos.
No fuerzo NO_WORK ni oculto un bloqueo nuevo.

## Evidencia reproducible

Conservé las seis consultas verificadas en notebook 08 raíz, bloques 5–10.
Las respuestas Genie verificadas son ef6a1c4902ef474da60878e1703002ba y 197529dbee2c4a0e9c82e37becc6afb5.
La conversación es 55615e73c08642daa30188c261d0627e.
No consulté shapes ni stop_times para este diagnóstico.
La vista previa no escribe y la aplicación solo inserta resoluciones operativas.
Raw, Staging, Bronze, Silver y los registros originales permanecen conservados.

## Verificación local

Pasaron 113 pruebas unitarias del proyecto.
Pasaron veinte pruebas seleccionadas en Docker: dieciséis unitarias y cuatro integraciones con Spark/Delta reales.
Las integraciones incluyen vista previa completa de notebook 18, persistencia idempotente y conservación del destino anterior.
También comprueban que un CLOSED o un cambio de estado invalide la exclusión.
Usé la imagen y JARs existentes, sin red y con el repositorio montado en modo de solo lectura.
Los temporales quedaron fuera de OneDrive.
La aplicación en Workspace y la nueva vista previa quedaron comprobadas después de estas pruebas locales.

## Recuperación comprobada en Workspace — 13 de noviembre de 2026

Notebook 18 devolvió persisted=true para las dos resoluciones.
INVALID_IDENTITY quedó registrada con resolución 9c7ecf28e44631cf8f6182b08f4296fd36e21a234324a08a7fff51a81ee1689d.
ABANDONED quedó registrada con resolución f62e1ff09705cb77f6492e9e19771948c97478e4e78e16cdf5ff8042bd0de9e2.
La evidencia conservó el cierre correcto de 2026 y las siete filas anteriores de agency_v1.

Después ejecuté notebook 11 nuevamente en vista previa.
Su tabla mostró veintidós decisiones:

| Estado | Cantidad | Alcance |
| --- | ---: | --- |
| COMPLETE | 19 | Nueve publicaciones de 2025 y diez de 2026. |
| OUT_OF_SCOPE | 1 | Service_dates de 2025, fuera del rango configurado. |
| RESOLVED | 2 | Los dos intentos identificados durante el diagnóstico. |
| BLOCKED | 0 | Desaparecieron los bloqueos de identidad y dependencia. |
| PENDING | 0 | No hay trabajo por programar dentro de este plan. |
| DEFERRED | 0 | No hay trabajo aplazado en esta salida. |

La tabla es coherente con NO_WORK bajo las reglas del planificador.
No adjunté un nuevo JSON del resumen ni una consulta SQL independiente de las resoluciones.
La salida demuestra que el planificador leyó y aplicó ambas decisiones en Workspace.
No republicó entidades para resolver los bloqueos.
Falta comprobar la variante del Job con task values y ciclos vacíos.
