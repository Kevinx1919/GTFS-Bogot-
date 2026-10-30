# Build in Public: construir un Lakehouse de movilidad para Bogotá

Este documento es la bitácora pública del proyecto. No busca contar una historia de "todo funcionó a la primera"; busca mostrar cómo se toman decisiones de ingeniería cuando los datos son incompletos, cambian o fallan.

El proyecto consume GTFS estático y GTFS-Realtime oficiales para construir métricas de operación de TransMilenio con Databricks, PySpark, Delta Lake y Power BI. Cada publicación debe distinguir con claridad entre una **hipótesis**, una **prueba** y un **resultado validado**.

## Compromiso de transparencia

- Compartir el problema, el contexto, la decisión tomada y su evidencia.
- Explicar por qué una solución aparentemente simple no era suficiente.
- Mostrar errores y correcciones sin publicar secretos, tokens, URLs privadas ni datos sensibles.
- No presentar prototipos como resultados de producción.
- Atribuir las fuentes oficiales de datos y respetar sus condiciones de uso.
- No hacer scraping de páginas HTML cuando existe una fuente oficial estructurada; en este proyecto se priorizan feeds GTFS y GTFS-Realtime.

## Retos que esperamos enfrentar

Cada reto se convertirá en una publicación cuando ocurra. La columna “evidencia” indica qué artefacto verificable debe acompañar la historia.

| Reto técnico | Por qué importa | Estrategia de resolución | Evidencia para compartir |
| --- | --- | --- | --- |
| Conectividad y disponibilidad de feeds | Un endpoint puede responder lento, fallar o no actualizarse. | Timeouts explícitos, reintentos con *backoff*, clasificación de errores y métricas de frescura. Nunca ocultar un fallo como si fuera ausencia de vehículos. | Código de manejo de errores, estado HTTP anonimizado, tasa de éxito y latencia. |
| Datos en Protobuf, no JSON | GTFS-Realtime llega como `.pb`; no se puede analizar directamente como un CSV. | Usar el esquema oficial para decodificar `VehiclePositions`, `TripUpdates` y `ServiceAlerts`; conservar primero el binario raw. | Diagrama raw → Bronze, ejemplo de esquema y prueba de decodificación. |
| Cambios de esquema o campos opcionales | Los feeds pueden omitir o añadir entidades/campos sin aviso. | Esquemas explícitos, campos opcionales controlados, validación de contrato y alertas de deriva. | Comparación de versiones, prueba que reproduce el cambio y decisión documentada. |
| GTFS estático y tiempo real no encajan siempre | Rutas, viajes o paradas pueden no encontrarse entre feeds o cambiar con una versión del static feed. | Versionar el GTFS estático, registrar hashes y fechas de vigencia; medir el porcentaje de correspondencia antes de hacer joins. | Tabla de cobertura de joins y diagrama de llaves. |
| Ejecución cada 5 minutos | Reintentos, retrasos o ejecuciones simultáneas pueden duplicar datos. | `run_id`, hash de contenido, claves idempotentes y control de concurrencia en Databricks Jobs. | Prueba de reejecución y auditoría de una corrida. |
| Almacenamiento raw y trazabilidad | Sin evidencia original no se puede auditar una transformación ni corregir una regla. | Guardar el archivo original inmutable en Unity Catalog Volume junto con un manifiesto: URL, UTC, hash, tamaño y estado HTTP. | Estructura de carpetas, contrato del manifiesto y consulta de linaje. |
| Calidad de coordenadas y timestamps | Coordenadas nulas, fuera de rango o timestamps viejos distorsionan métricas. | Reglas deterministas de validación y tabla de cuarentena con motivo de rechazo. | Métricas de calidad antes/después y ejemplos saneados. |
| Cálculo de velocidad operacional | Dos posiciones distantes pueden generar velocidades imposibles por saltos GPS o intervalos incorrectos. | Ordenar por vehículo y tiempo, calcular distancia/tiempo, filtrar saltos imposibles y reportar mediana/p90 por ruta e intervalo. | Caso de prueba con salto GPS y gráfico de la métrica resultante. |
| Diferencia entre velocidad y congestión | GTFS muestra operación del vehículo, no mide por sí solo el tráfico de toda Bogotá. | Nombrar la métrica “velocidad operacional”; limitar conclusiones a lo que los datos soportan. | Diccionario de métricas y ejemplo de interpretación correcta. |
| Detección de anomalías con poco historial | Sin línea base, un valor alto o bajo no es necesariamente anómalo. | Fase inicial de observación; después, baseline por ruta/franja con MAD o IQR y umbrales documentados. | Curva de madurez, historial mínimo y regla estadística publicada. |
| Costos y rendimiento de Databricks | Ejecutar pequeños trabajos frecuentemente puede generar costos y latencia innecesarios. | Medir duración, volumen y costo estimado; usar escrituras Delta incrementales y ajustar el cómputo según evidencia. | Tabla de observabilidad del Job y decisión de optimización. |
| Modelo semántico para Power BI | Un tablero rápido pero con métricas ambiguas pierde credibilidad. | Definir grano, zona horaria, filtros y fórmula de cada KPI antes de diseñar visuales. | Modelo estrella, diccionario de KPIs y captura del dashboard. |
| Agente con n8n/Ollama | Un LLM puede inventar conclusiones o tener más permisos de los necesarios. | El agente solo lee una vista Gold de anomalías aprobadas; usa plantillas con métricas y enlaces de evidencia; nunca escribe ni modifica reglas. | Diagrama de permisos, prompt sin secretos y evaluación de una respuesta. |
| Reproducibilidad y seguridad | Un proyecto no es profesional si depende de pasos manuales o credenciales copiadas. | Configuración por entorno, Databricks Secrets, `.env` ignorado, pruebas con fixtures y README ejecutable. | Lista de verificación de despliegue y CI verde. |

## Estructura de cada publicación

Usaré este formato para LinkedIn, GitHub Discussions o una entrada corta de blog:

```text
1. Contexto: qué parte del pipeline estaba construyendo.
2. Síntoma: qué falló o qué riesgo apareció.
3. Investigación: qué hipótesis comprobé y qué descarté.
4. Decisión: qué solución implementé y por qué.
5. Verificación: prueba, métrica o evidencia que confirma el resultado.
6. Aprendizaje: qué cambiaría y cuál es el siguiente experimento.
```

## Ejemplo de publicación inicial

> Empecé un Lakehouse de movilidad para Bogotá con GTFS-Realtime. El primer aprendizaje no fue escribir PySpark: fue decidir cómo conservar evidencia. Antes de decodificar posiciones de vehículos, cada respuesta se guardará como archivo raw junto con su timestamp UTC, hash y resultado HTTP. Así, si una métrica cambia, puedo rastrearla hasta el archivo que la originó. La siguiente etapa es validar conectividad desde Databricks y registrar el primer snapshot reproducible.

## Línea de tiempo

### Hito 01 — Descubrimiento de la fuente en tiempo real

**Pregunta inicial:** el portal de datos abiertos muestra GTFS estático actualizado, pero ¿dónde está la operación de la flota en tiempo real y cómo se consume?

**Hallazgo:** TransMilenio publica tres feeds GTFS-Realtime oficiales. No son tablas HTML ni archivos CSV: son respuestas HTTP binarias codificadas como Protocol Buffers (`.pb`).

| Feed | Endpoint oficial | Información esperada |
| --- | --- | --- |
| Vehicle Positions | `https://gis.transmilenio.gov.co/gtfs/vehiclepos.pb` | Vehículos, posiciones, timestamps y referencias operativas disponibles |
| Trip Updates | `https://gis.transmilenio.gov.co/gtfs/tripupdate.pb` | Predicciones, retrasos, cambios y posibles cancelaciones de viaje |
| Service Alerts | `https://gis.transmilenio.gov.co/gtfs/serviceAlerts.pb` | Alertas y afectaciones de servicio |

**Cómo se consumen:** un cliente hace una petición `GET`, conserva la respuesta binaria sin modificar y la decodifica como `FeedMessage` con `gtfs-realtime-bindings`. El header del feed contiene su versión y timestamp; ese timestamp no sustituye el momento UTC en que nuestro pipeline lo capturó.

```python
import requests
from google.transit import gtfs_realtime_pb2

response = requests.get(
    "https://gis.transmilenio.gov.co/gtfs/vehiclepos.pb",
    timeout=30,
)
response.raise_for_status()

feed = gtfs_realtime_pb2.FeedMessage()
feed.ParseFromString(response.content)
```

**Decisión de arquitectura:** no empezaremos por decodificar ni por visualizar. El primer notebook hará una prueba de conectividad y capturará evidencia raw: URL, `run_id`, timestamp UTC, código HTTP, tamaño y SHA-256. Solo una respuesta HTTP exitosa y válida se almacenará como snapshot inmutable en el Volume.

**Primer incidente real:** durante la exploración del 26 de octubre de 2026, los tres endpoints respondieron HTTP 500 desde el entorno de prueba. La respuesta correcta del pipeline no será inventar cero vehículos: registrará el fallo, aplicará reintentos con *backoff*, conservará la auditoría y evaluará la frescura del último snapshot exitoso.

**Límites que documentamos:** GTFS-Realtime permite medir operación de flota. La métrica derivada será velocidad operacional; no afirmaremos medir congestión de toda Bogotá sin una fuente independiente de tráfico.

**Fuentes:**

- [Endpoints GTFS de TransMilenio](https://gis.transmilenio.gov.co/gtfs/)
- [Especificación GTFS-Realtime](https://gtfs.org/documentation/realtime/reference/)
- [Bindings oficiales de Python](https://gtfs.org/documentation/realtime/language-bindings/python/)
- [Dataset GTFS estático de Bogotá](https://datosabiertos.bogota.gov.co/dataset/especificacion-gtfs-general-transport-feed-specification-sitp)

### Hito 02 — El primer incidente del proveedor: GTFS-Realtime indisponible

**Objetivo:** después de validar el Workspace, Unity Catalog y el Volume, intentamos almacenar el primer snapshot de `vehiclepos.pb`.

**Resultado observado:** el endpoint oficial devolvió HTTP 500 en tres intentos consecutivos. El notebook aplicó esperas de 1 y 2 segundos entre reintentos; no recibió bytes de un feed válido y, por diseño, no creó archivo raw ni hash de contenido.

```text
Intento 1 → HTTP 500 → espera 1 segundo
Intento 2 → HTTP 500 → espera 2 segundos
Intento 3 → HTTP 500 → ejecución finalizada sin escritura raw
```

**Problema adicional encontrado:** el primer reporte mostraba `final_http_status = null`. La causa fue una particularidad de la librería `requests`: una respuesta HTTP de error se evalúa como falsa en una condición. La expresión `response.status_code if response else None` confundía “recibí un HTTP 500” con “no recibí respuesta”.

**Corrección aplicada:** la condición se cambió a `response is not None`, que distingue correctamente un error de red de una respuesta HTTP fallida.

**Decisión de ingeniería:** el pipeline no reinterpreta HTTP 500 como cero vehículos ni persiste páginas de error como feeds. En producción registrará el intento en una tabla de auditoría y calculará la frescura desde el último snapshot exitoso. La captura de binarios raw solo se habilita si la respuesta es HTTP 200 y pasa la validación de formato.

**Cómo avanzamos sin bloquear el proyecto:** seguimos con el GTFS estático versionado. Esa fuente permite analizar la oferta planificada —rutas, paradas, viajes, calendarios y frecuencias— y comparar cambios entre versiones. El Realtime seguirá como dependencia externa observada, no como una suposición.

**Evidencia conservada:** `run_id`, fecha UTC, endpoint, tres códigos HTTP 500, número de intentos, cero bytes recibidos y ausencia de hash.

### Hito 03 — Del monitoreo de flota a la relación entre oferta y demanda

**Nuevo descubrimiento:** el ecosistema de datos abiertos de TransMilenio ofrece más que GTFS. Encontramos conjuntos de validaciones y salidas en CSV, ZIP y XLSX: validaciones diarias, validaciones mensuales históricas, salidas diarias del componente troncal y reportes mensuales por franja.

**Qué cambia en el problema:** el GTFS estático explica la oferta planificada —qué rutas, paradas, viajes y calendarios deberían operar—. Las validaciones y salidas aportan demanda observada agregada. Juntas permiten analizar cambios de demanda, cambios de oferta y un proxy de presión demanda-oferta planificada.

**Decisión de alcance:** el MVP deja de depender de GTFS-Realtime. Priorizamos primero el GTFS estático versionado y las validaciones mensuales; luego evaluaremos salidas y validaciones diarias por volumen, formato y granularidad. GTFS-Realtime permanece monitorizado y se añadirá cuando vuelva a entregar snapshots válidos.

**Límite analítico:** validaciones no equivalen a pasajeros por vehículo, ocupación, tiempo de espera ni matriz origen-destino. No afirmaremos esas métricas sin una fuente que las soporte. Cualquier cruce entre demanda y GTFS requerirá una llave o tabla de mapeo verificable entre estaciones/paradas, fecha y franja.

**Decisión de seguridad:** la presencia de un endpoint ArcGIS para generar tokens no obliga a autenticar los recursos públicos. Se solicitará token únicamente si una fuente específica responde 401/403 o se declara privada. Los tokens, de ser necesarios, vivirán en Databricks Secrets y nunca en el repositorio.

### Hito 04 — Automatizar el descubrimiento antes de automatizar la descarga

**Problema:** mantener una lista manual de URLs GTFS funciona para una prueba, pero deja de ser confiable cuando el proveedor publica nuevas versiones. Si una persona debe editar una fecha en el notebook para cada ejecución, el pipeline no es realmente incremental ni reproducible.

**Decisión:** el pipeline consultará primero el grupo público de GTFS en ArcGIS. Un notebook de descubrimiento registrará cada versión publicada, su identificador de portal, la URL candidata, sus fechas de publicación/modificación y una huella de metadata. Solo después se construirá un plan de ingesta para Raw, Staging y Bronze.

**Regla de automatización:** el Job tendrá tres modos: cargar la versión más reciente aún no ingerida, hacer un backfill por rango de fechas o reprocesar una versión explícita. El modo automático no seleccionará directamente “lo último” mientras descarga: primero persiste un plan para que un reintento sea reproducible.

**Qué verificaremos:** que el catálogo retorna versiones con el patrón `GTFS Estáticos AAAA-MM-DD`, que la URL es un ZIP directo antes de descargar y que una versión ya presente en Bronze no vuelva a entrar al plan.

**Corrección de integración:** el identificador del grupo GTFS pertenece a ArcGIS Online. La primera consulta al portal GIS operativo de TransMilenio respondió HTTP 400 con el mensaje de grupo inexistente o inaccesible. No era un problema de autenticación: se corrigió el host del catálogo a `www.arcgis.com` y se verificó que el grupo devuelve versiones publicadas y enlaces directos a ZIP.

### Hito 05 — La evolución de un feed no siempre es una columna nueva

**Resultado:** al comparar el snapshot GTFS de 2026 con el de 2025, apareció `feed_info.txt` y dejó de publicarse `fare_rules.txt`. El feed siguió siendo válido: ambos son archivos opcionales dentro del estándar GTFS.

**Decisión:** Raw y Staging preservan cada archivo publicado. Bronze carga `feed_info` cuando aparece, no genera filas artificiales cuando falta `fare_rules` y registra la ausencia como parte del contrato de esa versión. Solo la ausencia de un archivo requerido detiene la corrida.

### Hito 06 — El cambio silencioso de `route_desc`

**Resultado:** `routes.txt` pasó de 676 registros en el snapshot de 2025 a 1.045 registros en 2026. La comparación de esquemas mostró que `route_desc` estaba presente en 2025 y dejó de publicarse en 2026.

**Decisión:** se añadió una auditoría de deriva de esquema al notebook Bronze. El control compara solo columnas de negocio —no la trazabilidad técnica agregada por el pipeline— y reporta columnas omitidas o nuevas. La tabla Delta conserva `route_desc` por historia; las filas de 2026 quedan en `null` para ese campo, sin datos fabricados.

**Límite analítico:** la diferencia de 369 registros no se interpreta todavía como 369 rutas nuevas. Primero se compararán `route_id` y demás atributos en Silver para distinguir altas, bajas, variantes y cambios de codificación.

### Hito 07 — Cuando un error Delta es una alerta útil de contrato

**Resultado:** al cargar entidades de referencia de 2026, Delta detuvo la escritura por discrepancias de esquema. La auditoría mostró tres campos nuevos: `agency_fare_url`, `wheelchair_boarding` y `trip_headsign`. También confirmó que ninguna tabla había recibido filas parciales del nuevo snapshot.

**Decisión:** no se habilitó `autoMerge` global. La escritura Bronze utiliza `mergeSchema` de manera explícita y localizada, después de auditar las columnas nuevas. Así Delta incorpora campos publicados por el proveedor sin permitir evolución silenciosa en transformaciones posteriores.

### Hito 08 — Primer flujo Raw a Bronze ejecutado con éxito

**Fecha:** 29 de octubre de 2026. El primer Job manual de GTFS estático terminó con todas sus tareas en `Succeeded`. El objetivo era conservar versiones oficiales y tener una carga Bronze reproducible, con evidencia y controles de calidad.

**Cómo llegan los datos:** el notebook 06 consulta el catálogo público de ArcGIS para descubrir publicaciones. La descarga del GTFS estático es una petición HTTP a un ZIP publicado por la fuente; no es un feed en tiempo real. El notebook 02 conserva el ZIP original en Raw y un manifiesto con versión, URL, `run_id`, captura UTC, estado HTTP, tamaño y SHA-256. El notebook 03 extrae los archivos a Staging y carga rutas; los notebooks 04 y 05 cargan las demás entidades en tablas Delta Bronze. El notebook 07 evalúa el snapshot y registra los resultados de calidad y observación de esquemas.

**El Job construido:** `gtfs_bogota_bronze_manual` ejecutó `raw_gtfs → staging_y_rutas`, luego `bronze_referencias` y `bronze_operativos` en paralelo, y finalmente `validar_bronze`. La versión se pasó como parámetro y Raw comunicó la versión y el hash a las tareas posteriores mediante task values. La ejecución observada tardó 3 min 33 s y todas las tareas terminaron correctamente. El notebook 06 existe, pero todavía no forma parte de este Job.

**Evidencia de calidad:** se validaron los snapshots `2025-10-28` y `2026-09-29`. Al comparar sus encabezados, la evaluación de 2026 registró 49 reglas `PASS`, 3 `NOT_APPLICABLE` y 5 `WARN`, sin fallos bloqueantes. Las advertencias corresponden a cambios de columnas en `agency`, `routes`, `stops`, `trips` y `stop_times`; se conservan para revisión. La ausencia opcional de `fare_rules.txt` se registra sin inventar filas. El resultado `WARNING` es distinto del éxito técnico del Job: señala hallazgos que requieren interpretación.

**Idempotencia comprobada:** tras ejecutar el Job con el snapshot de 2026, una consulta confirmó que `bronze_gtfs_stop_times` conserva 9.408.893 filas para esa versión y hash, sin duplicar ese conteo. La auditoría conserva evaluaciones sucesivas; esta comprobación de una tabla no demuestra por sí sola todas las condiciones de concurrencia o recuperación.

**Resultado disponible:** snapshots de 2025 y 2026 en Raw, archivos extraídos en Staging, tabla s Bronze Delta y tablas de auditoría de calidad y esquemas. Las tablas mantienen procedencia del snapshot; Silver aún no está implementada. GTFS-Realtime devolvió HTTP 500 en las pruebas previas y sigue siendo una fuente pendiente.

**Antes de programar automáticamente:** conectar el descubrimiento al Job, tratar la ausencia de versiones nuevas como una salida normal, probar cargas parciales y reintentos, y hacer visibles las advertencias. El Job actual es manual y su configuración está en la interfaz de Databricks; todavía debe versionarse como configuración reproducible. El siguiente paso analítico es diseñar Silver según las preguntas de negocio y la granularidad de cada entidad.

### Hito 09 — Revisar el contrato de Bronze antes de diseñar Silver

**Fecha de inicio:** 29 de octubre de 2026. **Estado inicial:** observaciones de código verificadas; correcciones y prueba en Databricks pendientes. El PR #1 ya está fusionado y el trabajo continúa en `feature/silver-referencias`, creada desde `main` en `1bde977`.

**Qué encontramos:** el notebook 02 calcula `validation_passed`, pero no detiene la persistencia cuando falta un archivo esencial o la definición de calendario. Los notebooks 04 y 07 exigen simultáneamente `calendar.txt` y `calendar_dates.txt`; GTFS permite el patrón semanal, fechas explícitas o ambos. Además, el check de servicios del notebook 07 solo se ejecuta si están disponibles ambas tablas. La comprobación de versión de Bronze no cuenta los nulos como discrepancia y tampoco bloquea filas atribuidas a un archivo ausente en Staging. El notebook 00 todavía apunta al schema del proyecto anterior.

**Cómo lo vamos a corregir:** bloquear Raw antes de escribir cuando la estructura no sea válida; admitir al menos un archivo de calendario en la carga y en la auditoría; validar `trips.service_id` con las fuentes de calendario realmente disponibles; tratar una versión nula o distinta y filas sin archivo fuente como fallos de procedencia; exigir los encabezados semanales cuando se publique `calendar.txt`; y corregir el destino de la prueba de entorno. Se actualizará el runbook y se añadirán pruebas locales con ZIP pequeños y dobles de prueba, sin consultar fuentes reales.

**Límite de este cambio:** Bronze seguirá conservando los campos fuente como texto y sin borrar registros. Los tipos analíticos, la deduplicación y la cuarentena de negocio se implementarán en Silver. Concurrencia, recuperación integral, persistencia del plan de descubrimiento y configuración versionada del Job siguen pendientes para la etapa de automatización; no se presentan como resueltos.

**Verificación prevista:** pruebas locales de aceptación y rechazo, sintaxis de los notebooks y revisión del diff. Después se ejecutará la auditoría 07 en Databricks para los dos snapshots existentes. Una prueba local no demuestra escrituras Delta, rendimiento ni concurrencia. No se borrarán ni recargarán las tablas históricas como parte de esta corrección.

**Resultado local:** se aplicaron las correcciones a los notebooks 00, 02, 04 y 07, manteniendo sus rutas y los esquemas de las tablas Bronze. La suite `py -B -m unittest discover -s tests -v` pasó 16 pruebas, con subcasos para las tres combinaciones de calendario. Se comprobó rechazo antes de escribir, reintento Raw sin sobrescribir el ZIP ni el manifiesto de la misma corrida, calendarios, encabezados semanales, servicios huérfanos y procedencia. Los ZIP son sintéticos; se ejecuta el código real de los bloques con dobles de Spark, no el motor Spark/Delta.

**Error durante las pruebas:** el primer pase tuvo dos fallos por la captura de constantes del doble local de expresiones. Se corrigió el soporte de pruebas y se añadió un caso de snapshot completo válido para comprobar que no se generen fallos de presencia incorrectos. El siguiente pase terminó sin fallos. Esto no se presenta como un incidente de Databricks.

**Pendiente de verificación remota:** ejecutar 04 y después 07 para cada snapshot, revisar los nuevos `quality_run_id`, las advertencias y los conteos históricos. El procedimiento y las consultas están en `docs/notebook_runbook.md`. No se han consultado ni modificado tablas en Databricks durante esta corrección. No se requiere volver a descargar los ZIP ni ejecutar 03/05; avanzar a Silver depende de revisar la evidencia real de esta revalidación.

**Fuente del contrato:** [Referencia oficial GTFS: archivos y calendarios](https://gtfs.org/documentation/schedule/reference/#dataset-files). La presencia de un archivo no demuestra que sus filas cumplan todas las reglas del estándar; esa validación se ampliará por etapas.

## Qué no publicar

- Access tokens, secretos, archivos `.env`, cookies, hostnames privados o identificadores de cuenta.
- Capturas con credenciales, rutas privadas de Volumes o información personal.
- Archivos raw completos si su tamaño, licencia o condiciones de uso no permiten compartirlos.
- Conclusiones sobre congestión, puntualidad o calidad del servicio que no estén respaldadas por la métrica y sus límites.
- Resultados de una única ejecución como si fueran una tendencia histórica.

## Hitos públicos

- [ ] Validación de fuentes, licencia y conectividad desde Databricks.
- [ ] Primer archivo GTFS-Realtime almacenado en raw con manifiesto.
- [x] Primera carga Bronze y auditoría; reejecución manual comprobada para `stop_times`.
- [ ] Decodificación a Silver con métricas de calidad y cuarentena.
- [ ] Versión del GTFS estático vinculada a entidades realtime.
- [ ] Primera métrica Gold de velocidad operacional y cobertura de flota.
- [ ] Baseline histórico y detección determinista de anomalías.
- [ ] Dashboard Power BI con definiciones de KPI.
- [ ] Agente n8n/Ollama en lectura para informe diario verificable.
- [ ] CI, runbook y retrospectiva final del proyecto.

## Regla editorial final

No se comparte solo una solución; se comparte el razonamiento que permitió elegirla y la evidencia que permite confiar en ella.
