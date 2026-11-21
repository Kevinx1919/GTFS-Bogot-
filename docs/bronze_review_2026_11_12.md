# Mi revisión de Bronze antes de automatizar

**Fecha:** 12 de noviembre de 2026, zona America/Bogota.
**Estado:** diagnóstico de lectura; refinamientos todavía sin implementar.
**Código revisado:** HEAD 2e0d109 y notebooks locales 01–07.
No he comprobado igualdad de contenido entre estos archivos y los notebooks actuales de Workspace.

## Qué confirmé con Genie

Consulté las tablas system.lakeflow y las auditorías de workspace.gtfs_bogota.
Recuperé resultados estructurados completos antes de interpretar las cifras.
La metadata confirma el Job gtfs_bogota_bronze_manual y sus cinco tareas.
El historial confirma el paralelo entre referencias y operativas.

```text
raw_gtfs → staging_y_rutas
                    ├── bronze_referencias ─┐
                    └── bronze_operativos ──┴→ validar_bronze
```

La asociación con notebooks 02, 03, 04, 05 y 07 procede del diseño registrado durante el desarrollo.
Las tablas consultadas no devolvieron rutas de notebooks.
Los mapas task_parameters de las cinco tareas estaban vacíos en la última ejecución examinada.
No puedo certificar sus rutas, revisiones de código o parámetros desde esos mapas.

Las cinco ejecuciones más recientes contienen cuatro éxitos y una cancelación.
La última terminó con SUCCEEDED.
Ocurrió el 6 de noviembre de 2026, entre 22:36:51 y 22:39:35, hora de Bogotá.
Sus timestamps UTC son 2026-11-07T03:36:51.194Z y 2026-11-07T03:39:35.949Z.
La diferencia es 164,755 segundos, aproximadamente 2 minutos y 45 segundos.
No uso run_duration_seconds=0 como duración real.
La documentación limita esos campos de duración a ciertos Jobs antiguos de una tarea.
Esta ejecución aislada no demuestra el costo de cargar un feed nuevo.

El último estado histórico consultado devuelve trigger_type nulo y trigger_json vacío para Bronze y Silver.
También devuelve timeout_seconds=0 para ambos Jobs.
Esto no sustituye una exportación completa de su configuración actual.
Aún necesito esa exportación para versionar rutas, reintentos, entornos y parámetros reales.

## Qué confirmé en las auditorías

| Evidencia | Resultado | Interpretación |
| --- | --- | --- |
| Última validación del snapshot 2025-10-28 | 58 registros; cero fallos bloqueantes; cero advertencias. | Los controles guardados no bloquean ese snapshot. |
| Última validación del snapshot 2026-09-29 | 58 registros; cero fallos bloqueantes; cinco advertencias. | Las advertencias corresponden a cambios de esquema. |
| Encabezados observados | Once archivos para cada pareja versión/hash conocida. | No equivale, por sí solo, a una carga completa. |
| Catálogo de versiones | 161 elementos, 161 versiones y 161 URLs marcadas como ZIP directo. | Catálogo descubierto, no inventario de snapshots ya cargados. |
| Rango del catálogo | 2020-01-24 hasta 2026-09-29. | Describe el catálogo almacenado. |
| Última catalogación registrada | 2026-10-29T04:07:20.189Z. | No demuestra que el portal siga igual hoy. |

Las advertencias de 2026 afectan agency, routes, stops, trips y stop_times.
No las convierto automáticamente en errores de datos.
La ausencia de fare_rules en 2026 y feed_info en 2025 está registrada como no aplicable.

La consulta de duplicación encontró dos corridas antiguas con 57 copias adicionales cada una.
Corresponden a quality_run_id af02d0e4-976a-49ba-8670-9594b81901b4 y 766a2717-fbaa-4987-980d-6b7fbce9d340.
Los campos comparados no presentan variantes diferentes.
Las otras siete corridas consultadas no presentan esos grupos duplicados.
Esto describe duplicación de checks en la auditoría, no duplicación de filas de negocio Bronze.

El código permite volver a insertar checks al repetir el bloque final con el mismo quality_run_id.
Ese mecanismo podría explicar los duplicados; no he reconstruido la ejecución histórica para demostrar su causa.
No elimino registros históricos como parte de este diagnóstico.

Contaré advertencias mediante status='WARN'.
Severity='WARNING' también aparece en controles que terminan con PASS.
Por eso, contar severity='WARN' y status='FAIL' produce una conclusión incorrecta.

## Qué hace cada notebook y qué refinaré

| Notebook | Responsabilidad actual | Hallazgo | Siguiente ajuste |
| --- | --- | --- | --- |
| 01 | Probar conectividad y conservar mensajes GTFS-Realtime de vehículos. | El bloque final usa result sin definirlo; response puede quedar en None. | Corregir en el flujo Realtime separado. No bloquear el GTFS estático. |
| 02 | Elegir el ZIP, descargarlo y conservar Raw con hash y manifiesto. | Una llamada HTTP sin reintentos propios; reutilización por existencia del archivo. | Parametrizar y endurecer reintentos, integridad y entrega de parámetros al Job. |
| 03 | Extraer TXT a Staging y cargar routes en Bronze. | Reutiliza archivos por nombre; considera cargado un hash cuando encuentra alguna fila. | Verificar integridad y estado de carga; alinear la identidad del snapshot. |
| 04 | Cargar entidades de referencia y registrar procedencia. | Repite lógica de carga y consulta el hash para omitir cargas. | Compartir un cargador y conservar resultados por entidad. |
| 05 | Cargar shapes y stop_times en Bronze. | Repite el patrón de carga y varios conteos diagnósticos. | Compartir el cargador y medir acciones Spark redundantes. |
| 06 | Descubrir versiones y proponer una selección de ingesta. | Considera completa una versión si encuentra rutas; falla cuando no encuentra pendientes. | Consultar preparación completa, entregar un lote acotado y admitir ausencia de trabajo. |
| 07 | Validar el snapshot y guardar checks de calidad. | Falta un cierre persistido, versionado y explícito de la corrida completa. | Añadir el contrato de preparación y hacer idempotente la escritura de auditoría. |

Notebook 01 no forma parte del Job estático.
Notebook 06 tampoco forma parte del Job Bronze actual.

## Por qué priorizo el cierre de Bronze

Encontrar rutas no demuestra que shapes, stop_times y referencias hayan terminado.
Es como recibir una caja de un pedido y marcar todo el pedido como entregado.
El planificador necesita un comprobante del pedido completo.

Propondré audit_gtfs_bronze_snapshot_runs como registro terminal.
El nombre y su esquema definitivo todavía están pendientes de implementación.
Cada corrida tendrá versión, hash, identificador, versión de reglas y fechas UTC.
El registro resumirá archivos esperados, archivos presentes, cargas por entidad y resultados de calidad.
Solo una corrida completa podrá declarar el snapshot preparado.
La política de advertencias distinguirá cambios compatibles y situaciones que necesitan revisión.
Un fallo o una escritura interrumpida nunca equivaldrá a preparación completa.

Conservaré los checks detallados para explicar cada decisión.
Evitaré nuevas copias al reintentar la persistencia del mismo resultado.
Un nuevo intento de validación conservará su propia identidad.
No usaré un número fijo de checks como prueba de completitud.

## Identidad e integridad que revisaré juntas

Varios cargadores y lectores actuales filtran únicamente por hash.
Notebook 07 comprueba después que la versión de procedencia corresponda a la solicitada.
Cambiar solamente un filtro del cargador puede romper esa coherencia.

Probaré estos casos antes de cambiar la política:

- Misma versión y mismo hash: reintento sin duplicados.
- Misma versión y otro hash: nuevo contenido conservado separadamente.
- Otro nombre de versión y mismo hash: política coherente entre Raw, Bronze, lectores y auditoría.
- Carga parcial: recuperación explícita sin declarar completitud por una fila existente.

También revisaré archivos que existen después de una escritura interrumpida.
La reutilización actual basada en existencia deja ese riesgo abierto.
Es un riesgo deducido del código; no he observado archivos corruptos en Databricks.

## Orden del siguiente incremento

1. Obtener la exportación real del Job Bronze y preparar su plantilla portable.
2. Definir el contrato de cierre del notebook 07 y las pruebas de recuperación.
3. Alinear identidad, integridad y resultados de carga en notebooks 02–05.
4. Implementar plan_silver, pendiente 8b, sobre evidencia Bronze preparada.
5. Adaptar notebook 06 para selección dinámica y ausencia normal de novedades.
6. Coordinar los Jobs mediante el Job principal.
7. Probar un piloto y sus fallos antes de programarlo.

Puedo definir el contrato mientras obtengo la exportación.
No necesito reescribir todas las transformaciones ni recargar históricos para empezar.
La extracción de lógica común mantendrá notebooks como entradas legibles y módulos Python como funciones comprobables.
Mediré los conteos antes de prometer mejoras de rendimiento.
No quitaré controles necesarios para reducir tiempo.

## Qué puedo hacer con cada herramienta

| Herramienta | Trabajo comprobado o disponible | Límite actual |
| --- | --- | --- |
| Genie | Consultar metadata del Job, dependencias, ejecuciones, catálogo y auditorías mediante SQL. | No devuelve aquí el código de notebooks ni el JSON completo del Job. |
| Archivos locales | Revisar y editar notebooks, módulos, contratos, pruebas y plantillas versionadas. | No demuestra que Workspace ejecute la misma revisión. |
| Pruebas locales | Simular errores y comprobar decisiones de carga sin consumir la API real. | No certifica el entorno Serverless ni una ejecución real del Job. |
| Exportación del Job | Permitiría contrastar rutas, parámetros, reintentos y entornos. | Sigue pendiente; el conector Genie no ofrece esa operación. |

No interpreto los mapas vacíos como prueba de ausencia de parámetros en la configuración real.
Tampoco interpreto esta limitación del conector como falta de permisos Jobs API.
Para comprobar esa API necesitaría otra vía de acceso; no la he probado en esta revisión.

## Comprobaciones realizadas

Los 16 tests existentes de Raw y Bronze pasaron con fixtures y dobles.
No usaron Spark real ni llamadas HTTP.
También comprobé sintaxis de los bloques Python revisados.
Reproduje los dos fallos del notebook 01 sin llamadas HTTP ni escrituras.
No ejecuté los notebooks completos en Databricks.

Conservé cuatro consultas finales en [mi notebook de diagnóstico](../databricks/notebooks/08_review_bronze_automation.ipynb).
Cada consulta tiene resultados completos verificados mediante Genie.
El notebook completo todavía no tiene una ejecución documentada.
No forma parte del Job de producción y no guarda outputs en Git.

El [plan de orquestación](orchestration_plan.md) conserva el diseño del planificador y del Job principal.
Esta revisión añade evidencia real y prioridades; no despliega los refinamientos.

## Fuentes

La documentación de [tablas de sistema Lakeflow](https://docs.databricks.com/aws/en/admin/system-tables/jobs) explica su historia y sus campos.
Los resultados corresponden a la conversación Genie 611b8d8f6a624e9cbf75bcfcf1bb7975.
Las respuestas verificadas son 6e529870824944c8a7c5b55b4e90f20b y d086e5dfab9d4f25ab703b7a4e1bb5b9.
