# Build in Public: construir un Lakehouse de movilidad para Bogotá

Esta es mi bitácora del proyecto. Quiero contar qué voy aprendiendo, qué falló y por qué tomé cada decisión, sin hacer pasar una prueba por algo que ya está listo para producción.

Estoy construyendo un lakehouse con datos oficiales de movilidad de Bogotá, Databricks, PySpark, Delta Lake y Power BI. Empecé explorando GTFS-Realtime y avancé con GTFS estático cuando la fuente en tiempo real falló. En cada entrada separaré una **hipótesis**, una **prueba** y un **resultado validado**.

## Compromiso de transparencia

- Compartir el problema, el contexto, la decisión tomada y su evidencia.
- Explicar por qué una solución aparentemente simple no era suficiente.
- Mostrar errores y correcciones sin publicar secretos, tokens, URLs privadas ni datos sensibles.
- No presentar prototipos como resultados de producción.
- Atribuir las fuentes oficiales de datos y respetar sus condiciones de uso.
- No hacer scraping de páginas HTML cuando existe una fuente oficial estructurada; en este proyecto se priorizan feeds GTFS y GTFS-Realtime.

## Retos que espero enfrentar

Documentaré cada reto cuando ocurra. La columna “evidencia” indica qué artefacto verificable debe acompañar la historia.

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

**Cómo se consumen:** un cliente hace una petición `GET`, conserva la respuesta binaria sin modificar y la decodifica como `FeedMessage` con `gtfs-realtime-bindings`. El header del feed contiene su versión y timestamp; ese timestamp no sustituye el momento UTC en que mi pipeline lo capturó.

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

**Decisión de arquitectura:** no empezaré por decodificar ni por visualizar. El primer notebook hará una prueba de conectividad y capturará evidencia raw: URL, `run_id`, timestamp UTC, código HTTP, tamaño y SHA-256. Solo una respuesta HTTP exitosa y válida se almacenará como snapshot inmutable en el Volume.

**Primer incidente real:** durante la exploración del 26 de octubre de 2026, los tres endpoints respondieron HTTP 500 desde el entorno de prueba. La respuesta correcta del pipeline no será inventar cero vehículos: registrará el fallo, aplicará reintentos con *backoff*, conservará la auditoría y evaluará la frescura del último snapshot exitoso.

**Límites que dejé claros:** GTFS-Realtime permite medir operación de flota. La métrica derivada será velocidad operacional; no afirmaré medir congestión de toda Bogotá sin una fuente independiente de tráfico.

**Fuentes:**

- [Endpoints GTFS de TransMilenio](https://gis.transmilenio.gov.co/gtfs/)
- [Especificación GTFS-Realtime](https://gtfs.org/documentation/realtime/reference/)
- [Bindings oficiales de Python](https://gtfs.org/documentation/realtime/language-bindings/python/)
- [Dataset GTFS estático de Bogotá](https://datosabiertos.bogota.gov.co/dataset/especificacion-gtfs-general-transport-feed-specification-sitp)

### Hito 02 — El primer incidente del proveedor: GTFS-Realtime indisponible

**Objetivo:** después de validar el Workspace, Unity Catalog y el Volume, intenté almacenar el primer snapshot de `vehiclepos.pb`.

**Resultado observado:** el endpoint oficial devolvió HTTP 500 en tres intentos consecutivos. El notebook aplicó esperas de 1 y 2 segundos entre reintentos; no recibió bytes de un feed válido y, por diseño, no creó archivo raw ni hash de contenido.

```text
Intento 1 → HTTP 500 → espera 1 segundo
Intento 2 → HTTP 500 → espera 2 segundos
Intento 3 → HTTP 500 → ejecución finalizada sin escritura raw
```

**Problema adicional encontrado:** el primer reporte mostraba `final_http_status = null`. La causa fue una particularidad de la librería `requests`: una respuesta HTTP de error se evalúa como falsa en una condición. La expresión `response.status_code if response else None` confundía “recibí un HTTP 500” con “no recibí respuesta”.

**Corrección aplicada:** la condición se cambió a `response is not None`, que distingue correctamente un error de red de una respuesta HTTP fallida.

**Decisión de ingeniería:** el pipeline no reinterpreta HTTP 500 como cero vehículos ni persiste páginas de error como feeds. En producción registrará el intento en una tabla de auditoría y calculará la frescura desde el último snapshot exitoso. La captura de binarios raw solo se habilita si la respuesta es HTTP 200 y pasa la validación de formato.

**Cómo seguí avanzando:** continué con el GTFS estático versionado. Esa fuente permite analizar la oferta planificada —rutas, paradas, viajes, calendarios y frecuencias— y comparar cambios entre versiones. El Realtime seguirá como dependencia externa observada, no como una suposición.

**Evidencia conservada:** `run_id`, fecha UTC, endpoint, tres códigos HTTP 500, número de intentos, cero bytes recibidos y ausencia de hash.

### Hito 03 — Del monitoreo de flota a la relación entre oferta y demanda

**Nuevo descubrimiento:** el ecosistema de datos abiertos de TransMilenio ofrece más que GTFS. Encontré conjuntos de validaciones y salidas en CSV, ZIP y XLSX: validaciones diarias, validaciones mensuales históricas, salidas diarias del componente troncal y reportes mensuales por franja.

**Qué cambia en el problema:** el GTFS estático explica la oferta planificada —qué rutas, paradas, viajes y calendarios deberían operar—. Las validaciones y salidas aportan demanda observada agregada. Juntas permiten analizar cambios de demanda, cambios de oferta y un proxy de presión demanda-oferta planificada.

**Decisión de alcance:** el MVP deja de depender de GTFS-Realtime. Decidí priorizar el GTFS estático versionado y las validaciones mensuales; luego evaluaré salidas y validaciones diarias por volumen, formato y granularidad. GTFS-Realtime permanece monitorizado y se añadirá cuando vuelva a entregar snapshots válidos.

**Límite analítico:** validaciones no equivalen a pasajeros por vehículo, ocupación, tiempo de espera ni matriz origen-destino. No afirmaré esas métricas sin una fuente que las soporte. Cualquier cruce entre demanda y GTFS requerirá una llave o tabla de mapeo verificable entre estaciones/paradas, fecha y franja.

**Decisión de seguridad:** la presencia de un endpoint ArcGIS para generar tokens no obliga a autenticar los recursos públicos. Se solicitará token únicamente si una fuente específica responde 401/403 o se declara privada. Los tokens, de ser necesarios, vivirán en Databricks Secrets y nunca en el repositorio.

### Hito 04 — Automatizar el descubrimiento antes de automatizar la descarga

**Problema:** mantener una lista manual de URLs GTFS funciona para una prueba, pero deja de ser confiable cuando el proveedor publica nuevas versiones. Si una persona debe editar una fecha en el notebook para cada ejecución, el pipeline no es realmente incremental ni reproducible.

**Decisión:** el pipeline consultará primero el grupo público de GTFS en ArcGIS. Un notebook de descubrimiento registrará cada versión publicada, su identificador de portal, la URL candidata, sus fechas de publicación/modificación y una huella de metadata. Solo después se construirá un plan de ingesta para Raw, Staging y Bronze.

**Regla de automatización:** el Job tendrá tres modos: cargar la versión más reciente aún no ingerida, hacer un backfill por rango de fechas o reprocesar una versión explícita. El modo automático no seleccionará directamente “lo último” mientras descarga: primero persiste un plan para que un reintento sea reproducible.

**Qué voy a verificar:** que el catálogo retorna versiones con el patrón `GTFS Estáticos AAAA-MM-DD`, que la URL es un ZIP directo antes de descargar y que una versión ya presente en Bronze no vuelva a entrar al plan.

**Corrección de integración:** el identificador del grupo GTFS pertenece a ArcGIS Online. La primera consulta al portal GIS operativo de TransMilenio respondió HTTP 400 con el mensaje de grupo inexistente o inaccesible. No era un problema de autenticación: se corrigió el host del catálogo a `www.arcgis.com` y se verificó que el grupo devuelve versiones publicadas y enlaces directos a ZIP.

### Hito 05 — La evolución de un feed no siempre es una columna nueva

**Resultado:** al comparar el snapshot GTFS de 2026 con el de 2025, apareció `feed_info.txt` y dejó de publicarse `fare_rules.txt`. El feed siguió siendo válido: ambos son archivos opcionales dentro del estándar GTFS.

**Decisión:** Raw y Staging preservan cada archivo publicado. Bronze carga `feed_info` cuando aparece, no genera filas artificiales cuando falta `fare_rules` y registra la ausencia como parte del contrato de esa versión. Solo la ausencia de un archivo requerido detiene la corrida.

### Hito 06 — El cambio silencioso de `route_desc`

**Resultado:** `routes.txt` pasó de 676 registros en el snapshot de 2025 a 1.045 registros en 2026. La comparación de esquemas mostró que `route_desc` estaba presente en 2025 y dejó de publicarse en 2026.

**Decisión:** añadí una auditoría de deriva de esquema al notebook Bronze. El control compara solo columnas de negocio —no la trazabilidad técnica agregada por el pipeline— y reporta columnas omitidas o nuevas. La tabla Delta conserva `route_desc` por historia; las filas de 2026 quedan en `null` para ese campo, sin datos fabricados.

**Límite analítico:** la diferencia de 369 registros no se interpreta todavía como 369 rutas nuevas. Primero se compararán `route_id` y demás atributos en Silver para distinguir altas, bajas, variantes y cambios de codificación.

### Hito 07 — Cuando un error Delta es una alerta útil de contrato

**Resultado:** al cargar entidades de referencia de 2026, Delta detuvo la escritura por discrepancias de esquema. La auditoría mostró tres campos nuevos: `agency_fare_url`, `wheelchair_boarding` y `trip_headsign`. También confirmó que ninguna tabla había recibido filas parciales del nuevo snapshot.

**Decisión:** mantuve `autoMerge` global deshabilitado. La escritura Bronze utiliza `mergeSchema` de manera explícita y localizada, después de auditar las columnas nuevas. Así Delta incorpora campos publicados por el proveedor sin permitir evolución silenciosa en transformaciones posteriores.

### Hito 08 — Primer flujo Raw a Bronze ejecutado con éxito

**Fecha:** 29 de octubre de 2026. El primer Job manual de GTFS estático terminó con todas sus tareas en `Succeeded`. Mi objetivo era conservar versiones oficiales y tener una carga Bronze reproducible, con evidencia y controles de calidad.

**Cómo llegan los datos:** el notebook 06 consulta el catálogo público de ArcGIS para descubrir publicaciones. La descarga del GTFS estático es una petición HTTP a un ZIP publicado por la fuente; no es un feed en tiempo real. El notebook 02 conserva el ZIP original en Raw y un manifiesto con versión, URL, `run_id`, captura UTC, estado HTTP, tamaño y SHA-256. El notebook 03 extrae los archivos a Staging y carga rutas; los notebooks 04 y 05 cargan las demás entidades en tablas Delta Bronze. El notebook 07 evalúa el snapshot y registra los resultados de calidad y observación de esquemas.

**El Job construido:** `gtfs_bogota_bronze_manual` ejecutó `raw_gtfs → staging_y_rutas`, luego `bronze_referencias` y `bronze_operativos` en paralelo, y finalmente `validar_bronze`. La versión se pasó como parámetro y Raw comunicó la versión y el hash a las tareas posteriores mediante task values. La ejecución observada tardó 3 min 33 s y todas las tareas terminaron correctamente. El notebook 06 existe, pero todavía no forma parte de este Job.

**Evidencia de calidad:** validé los snapshots `2025-10-28` y `2026-09-29`. Al comparar sus encabezados, la evaluación de 2026 registró 49 reglas `PASS`, 3 `NOT_APPLICABLE` y 5 `WARN`, sin fallos bloqueantes. Las advertencias corresponden a cambios de columnas en `agency`, `routes`, `stops`, `trips` y `stop_times`; se conservan para revisión. La ausencia opcional de `fare_rules.txt` se registra sin inventar filas. El resultado `WARNING` es distinto del éxito técnico del Job: señala hallazgos que requieren interpretación.

**Idempotencia comprobada:** después de ejecutar el Job para 2026, consulté la tabla y confirmé que `bronze_gtfs_stop_times` conserva 9.408.893 filas para esa versión y hash, sin duplicar ese conteo. La auditoría conserva evaluaciones sucesivas; esta comprobación de una tabla no demuestra por sí sola todas las condiciones de concurrencia o recuperación.

**Resultado disponible:** snapshots de 2025 y 2026 en Raw, archivos extraídos en Staging, tablas Bronze Delta y tablas de auditoría de calidad y esquemas. Las tablas mantienen procedencia del snapshot; Silver aún no está implementada. GTFS-Realtime devolvió HTTP 500 en las pruebas previas y sigue siendo una fuente pendiente.

**Lo que me falta antes de programarlo:** conectar el descubrimiento al Job, tratar la ausencia de versiones nuevas como una salida normal, probar cargas parciales y reintentos, y hacer visibles las advertencias. El Job actual es manual y su configuración está en la interfaz de Databricks; todavía debe versionarse como configuración reproducible. El siguiente paso analítico es diseñar Silver según las preguntas de negocio y la granularidad de cada entidad.

### Hito 09 — Revisar el contrato de Bronze antes de diseñar Silver

**Fecha de inicio:** 29 de octubre de 2026. Con el PR #1 fusionado, creé `feature/silver-referencias` desde `main`, en `1bde977`. Antes de empezar Silver, revisé con apoyo de Codex si Bronze tenía una base suficientemente clara para seguir.

**Qué encontré:** el notebook 02 calculaba `validation_passed`, pero permitía continuar aunque faltara un archivo esencial o la definición de calendario. Los notebooks 04 y 07 exigían `calendar.txt` y `calendar_dates.txt` al mismo tiempo, aunque GTFS admite las combinaciones válidas de esos archivos. Además, la relación de servicios solo se comprobaba con ambas tablas, las versiones nulas quedaban fuera de la comprobación de procedencia y las filas atribuidas a un archivo ausente no bloqueaban la auditoría. El notebook 00 todavía apuntaba al schema del proyecto anterior.

**Cómo decidí corregirlo:** preparé con Codex una barrera antes de escribir Raw, la validación del grupo de calendarios y la comprobación de servicios con los archivos disponibles. También añadí controles para versiones nulas o diferentes y filas sin archivo fuente, exigí los encabezados semanales cuando exista `calendar.txt` y corregí el destino del notebook de prueba. Mantuve los campos fuente como texto; los tipos analíticos y la deduplicación siguen siendo trabajo de Silver.

Esto es como revisar una entrega: marcar una caja como incompleta no sirve de mucho si después la dejo entrar como si estuviera lista. La validación tiene que detener el flujo cuando encuentra un problema que impide continuar.

**Verificación local:** las correcciones de 00, 02, 04 y 07 conservaron sus rutas y los esquemas de las tablas Bronze. La suite `py -B -m unittest discover -s tests -v` pasó 16 pruebas, incluidos subcasos de las tres combinaciones de calendarios. Comprobé el rechazo antes de escribir y el reintento Raw sin sobrescribir el ZIP ni el manifiesto de la misma corrida. Usé ZIP sintéticos y dobles de Spark; eso no equivale a probar el motor Spark/Delta real.

**Un error de las pruebas:** el primer pase tuvo dos fallos por cómo el doble local capturaba constantes. Corregí ese soporte con Codex y añadí un snapshot completo válido para asegurar que los checks de presencia no fallaran por error. El siguiente pase terminó bien. Fue un problema del soporte local de pruebas, no un incidente de Databricks.

**Lo que obtuve en Databricks para 2026:** ejecuté la revisión y el notebook 07 terminó en `WARNING`, con cero fallos bloqueantes y cinco advertencias de esquema en `agency`, `routes`, `stop_times`, `stops` y `trips`. `calendar_definition_present` pasó con ambos archivos. Los checks de versión mostraron cero discrepancias y las cuatro relaciones revisadas mostraron cero claves huérfanas.

El conteo de `stop_times` se mantuvo en 9.408.893 filas. También revisé 1.045 rutas, 8.314 ubicaciones, 181.060 viajes, 926.501 puntos de geometría, 7 agencias, 7 filas de calendario, 133 excepciones y 14 ventanas de frecuencia. Son registros del snapshot planificado; no representan por sí solos servicio realmente operado.

**Cómo interpreté las advertencias:** las cinco entidades y sus encabezados coincidían con los cambios del Hito 08. En la evidencia que guardé no incluí los detalles comparativos de columnas ni el `quality_run_id`. La ausencia de `fare_rules`, con cero filas, era esperada por tratarse de un opcional. En `feed_info`, la evolución de esquema no aplicaba porque no había una observación anterior comparable. También separé dos cosas que al principio pueden confundirse: `PASS` indica que la regla se cumplió; `BLOCKING` o `WARNING` indican su severidad, no que haya fallado.

**Reejecución de 04 para 2026:** las ocho entidades mostraron `snapshot_already_loaded = true`. Los conteos leídos desde Staging coincidían con la auditoría Bronze: agency 7, calendar 7, calendar_dates 133, fare_attributes 1, feed_info 1, frequencies 14, stops 8.314 y trips 181.060. Entendí que `source_row_count` cuenta filas leídas, no filas nuevas insertadas. Para esas ocho tablas y hashes, el código omitió nuevas inserciones; todavía no puedo extender esa conclusión a todos los escenarios de concurrencia o recuperación.

**Revalidación de 2025:** obtuve `snapshot_already_loaded = true` en las ocho entidades: agency 7, calendar 7, calendar_dates 140, fare_attributes 7, fare_rules 676, frequencies 2, stops 6.530 y trips 107.162 filas leídas. El notebook 07 terminó en `PASSED`, con cero fallos bloqueantes y cero advertencias. Para esta parte guardé el resumen, sin un nuevo detalle por regla ni una nueva consulta del conteo de horarios de 2025.

**Cierre y aprendizaje:** con las salidas de 04 y 07 para ambos snapshots cerré la revalidación prevista. No necesité descargar otra vez los ZIP ni ejecutar 03/05. En esta etapa revisé las salidas de la interfaz; la conexión directa desde Codex llegó después, en el Hito 12. Conservaré los `quality_run_id` junto a las evidencias de ejecución. El procedimiento está en `docs/notebook_runbook.md`.

Silver seguía pendiente. Dejé para la etapa de automatización la concurrencia, la recuperación integral, la persistencia del plan de descubrimiento y la configuración versionada del Job. Tampoco presenté las pruebas locales como una prueba de integración completa de Raw. Que 2025 no tuviera advertencias no demostraba que su esquema fuera igual al de 2026.

**Fuente del contrato:** [Referencia oficial GTFS: archivos y calendarios](https://gtfs.org/documentation/schedule/reference/#dataset-files). La presencia de un archivo no demuestra que todas sus filas cumplan el estándar; iré ampliando las reglas por etapas.

### Hito 10 — Consolidar Silver como un proceso de decisiones por entidad

Después de revalidar Bronze, ordené el plan de Silver. Quería tener claro qué iba a revisar y por qué, antes de llenar el proyecto de transformaciones.

**Mi forma de avanzar:** elegir el snapshot, entender qué representa una fila, definir su clave, medir nulos/vacíos/espacios y duplicados, decidir tipos y reglas, transformar, registrar rechazos, probar y verificar la reejecución. Asignar un tipo no significa rellenar un dato que la fuente no publicó.

**Lo que preparé:** guardé el plan en `docs/silver_design.md` y creé `databricks/notebooks/silver/` con su README. Mantuve los notebooks Bronze en sus rutas para conservar las referencias del Job y actualicé el runbook.

Decidí empezar por agency y después routes. Son entidades con las que puedo entender identidad, relaciones y calidad antes de llegar a los millones de filas de horarios. Solo pasaré a la siguiente cuando pueda explicar el resultado de la anterior.

**Límite de este hito:** en ese momento solo preparé estructura y documentación. Aún no había creado notebooks ejecutables, medido errores de conversión ni escrito tablas Silver. Las pruebas que tenía seguían correspondiendo a Raw/Bronze.

### Hito 11 — Primer perfilado de agency preparado para revisión

**Fecha:** 30 de octubre de 2026. Con apoyo de Codex preparé `08_profile_gtfs_reference_entities` en la carpeta Silver. Todavía no lo había ejecutado en Databricks ni tenía resultados reales de nulos o duplicados de agency.

**Qué preparé:** cuatro bloques de lectura: parámetros; procedencia, esquema y muestra; métricas por columna; y duplicados. Propuse conservar como string los campos conocidos, incluidos ID y teléfono. Para un campo nuevo dejaría la decisión pendiente, en vez de convertirlo por su apariencia numérica.

**Qué quería distinguir:** una columna ausente, un null, una cadena vacía y un texto compuesto por espacios; copias idénticas de negocio frente a IDs con atributos distintos; y posibles colisiones al quitar espacios. Excluí los timestamps de procesamiento de la comparación de duplicados. No apliqué limpieza ni creé cuarentena.

**Verificación local:** pasaron seis pruebas nuevas de parámetros y encabezados y las 16 existentes. Omití tres pruebas con fixtures Spark porque faltaba el entorno local requerido. Revisé sintaxis y estructura, pero seguía pendiente comprobar el notebook contra Spark real.

**Lo que dejé pendiente:** ejecutar primero los bloques 1 y 2 para 2025, mirar conteo, esquema y filas, y después interpretar las métricas de 3 y 4. Más adelante repetiría la revisión para 2026. No añadí el notebook al Job Bronze ni avancé a routes o a la transformación Silver.

### Hito 12 — Primera consulta directa a Databricks mediante Genie

**Fecha:** 30 de octubre de 2026. Como trabajo con Free Edition, investigué con Codex si podía conectar el proyecto mediante navegador, MCP o API. Revisé documentación oficial con agent-browser y encontré la integración Databricks Genie. Al conectarla, pude hacer las primeras consultas reales desde las herramientas de Codex.

**La primera comprobación:** Genie ejecutó `DESCRIBE workspace.gtfs_bogota.bronze_gtfs_agency`. Recuperé el resultado estructurado con estado SUCCEEDED: 11 columnas reales, siete de negocio string y cuatro técnicas. De las técnicas, tres son string y `bronze_loaded_at_utc` es timestamp. No conté como columnas las dos líneas informativas de clustering que también devuelve DESCRIBE.

**La segunda comprobación:** pedí un conteo con versión y hash explícitos. La consulta terminó en SUCCEEDED y devolvió 7 registros de agency para 2025-10-28 y 7 para 2026-09-29. En ese momento solo había comprobado cantidades, no la unicidad de los IDs.

**Cómo entiendo la conexión:** Codex usa herramientas MCP para enviar una pregunta o SQL a Genie. Genie puede ejecutar la consulta en Databricks y devolver el SQL, el progreso y los resultados. Luego reviso esa evidencia con Codex y guardo lo útil en el proyecto. Los permisos siguen dependiendo de la identidad autenticada y del workspace; la IA no me concede acceso nuevo por sí sola.

Me ayudó pensarlo como un mensajero con una solicitud concreta: Codex prepara la pregunta, la conexión la lleva a Genie y recibo una respuesta que puedo comprobar. Tener el mensajero no cambia qué puertas tengo permiso para abrir.

**Una precisión sobre la CLI:** Codex admite MCP también desde Codex CLI cuando está configurado, pero esta prueba la hice desde Codex desktop y las herramientas de la integración. No utilicé Databricks CLI ni comprobé esta conexión concreta desde Codex CLI.

**Qué gané en el flujo de trabajo:** pude revisar esquema, conteos y calidad sin copiar cada salida de la interfaz a la conversación. También pude contrastar resultados, trabajar con respuestas acotadas y guardar el SQL para repetir el diagnóstico. Así dedico más atención a entender el dato y menos a moverlo entre ventanas. No he medido minutos ahorrados, consumo de cómputo ni ahorro económico, y no doy por correcta una consulta solo porque la haya generado una IA.

**Mi criterio de trabajo:** uso MCP como conexión, Genie como ayuda para consultar y Codex para revisar, explicar y preparar código. Las reglas de calidad y las transformaciones siguen siendo deterministas y quedan en archivos del proyecto. Genie no guarda consultas en Git ni las publica en GitHub automáticamente: debo conservarlas y hacer commit/push.

**Qué comprobé y qué no:** leí metadatos y conté agency. No probé escrituras, ejecución de notebooks/Jobs, acceso a Volumes ni todas las tablas. Haber usado consultas de lectura no demuestra que mi cuenta tenga únicamente esos permisos. No modifiqué tablas, creé dashboards ni guardé credenciales o la URL del workspace en el repositorio.

**Otras opciones que revisé:** CLI/API con OAuth, PAT si el workspace lo permite y MCP oficiales. No encontré Databricks CLI en el PATH local ni lo instalé. El MCP SQL documentado requiere activar Unity Gateway beta desde la consola de cuenta; Free Edition no permite entrar a esa consola, así que no asumí que estuviera disponible. Esa limitación no impidió las consultas que sí comprobé mediante Genie.

**Fuentes:** [Autenticación CLI](https://docs.databricks.com/aws/en/dev-tools/cli/authentication), [límites Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations), [MCP oficiales](https://docs.databricks.com/aws/en/agents/mcp-tools/built-in-mcp-services) y [MCP en Codex](https://learn.chatgpt.com/docs/extend/mcp).

### Hito 13 — Perfilado real de agency 2025 antes de transformar

**Fecha:** 30 de octubre de 2026. Revisé el snapshot 2025-10-28 y su hash documentado con consultas de lectura mediante Genie. Recuperé las siete filas completas, una observación de encabezados y los resultados estructurados de dos consultas de métricas. Guardé el SQL en `databricks/sql/silver/agency_profile_2025.sql` y el informe agregado en `docs/agency_profile_2025.md`, sin copiar filas raw ni enlaces privados a Git.

**Qué encontré:** siete IDs distintos no vacíos; cero copias idénticas adicionales, IDs repetidos, conflictos de clave o colisiones potenciales al quitar espacios. Los seis campos publicados tenían siete valores no vacíos y cero nulos, cadenas vacías o valores compuestos por espacios. `agency_id` y `agency_name` tenían siete valores distintos; URL, zona horaria, idioma y teléfono tenían uno cada uno.

**Qué aprendí:** compartir un teléfono o una URL no convierte dos filas en duplicados. Es como si dos oficinas compartieran recepción: pueden seguir teniendo identidades distintas. La auditoría también confirmó que `agency_fare_url` no se publicó en 2025; sus siete null en Delta no eran celdas que hubieran dejado vacías en el archivo.

Por ahora mantengo la propuesta string para los campos conocidos. No encontré una razón para rellenar o eliminar datos en los controles realizados, ni para convertir el ID a entero solo porque contenga dígitos.

**Cómo contrasté el resultado:** ambas consultas de métricas terminaron en SUCCEEDED, sin truncamiento. Comparé sus valores con un cálculo determinista independiente sobre las siete filas recuperadas y coincidieron. Esto comprueba la evidencia SQL de ese snapshot; no demuestra todavía la ejecución del notebook PySpark, la validez de todos los formatos ni la calidad de 2026.

**Cómo ordené el aprendizaje:** al revisar todo el perfil automático de golpe, el recorrido se volvió difícil de seguir. Preparé `databricks/notebooks/silver/08_agency_sql_guiado.ipynb` como entrada principal: una pregunta por bloque y las dos consultas largas originales como apéndices. Conservo el `.sql` original como evidencia y el perfilador PySpark como alternativa para automatizar después esas preguntas. Todavía no he ejecutado la guía nueva en Databricks.

**Lo que sigue:** revisar con calma el informe de 2025, perfilar agency de 2026 y definir el contrato Silver. No he modificado Bronze, creado Silver ni avanzado a routes. Tampoco interpreto los IDs como una identidad empresarial validada o una garantía de continuidad entre versiones.

### Hito 14 — Decisión de preservar agency por snapshot

**Fecha:** 6 de noviembre de 2026. Revisé las salidas del perfilador PySpark de agency para 2025 y 2026. En ambos snapshots encontré siete filas y siete IDs distintos con contenido, sin duplicados ni colisiones potenciales al quitar espacios. Los campos publicados tenían contenido; `agency_fare_url` estaba ausente en 2025 y publicado con siete valores no vacíos en 2026. Estas comprobaciones no sustituyen la validación de formatos pendiente.

**El hallazgo:** algunos números de `agency_id` aparecen asociados a nombres distintos entre versiones. No encontré una causa confirmada del cambio y no interpreto la URL compartida como identificador.

**Qué contrasté:** con consultas de lectura mediante Genie revisé las rutas dentro de cada snapshot. Recuperé 676 IDs de ruta distintos en 2025 y 1.045 en 2026; solo uno coincidía literalmente entre versiones. También encontré coincidencias de etiquetas de ruta entre categorías distintas. Esto no demuestra desapariciones, altas reales ni continuidad de servicios, y no respalda una equivalencia automática de agencias.

**Mi decisión:** conservaré la clave `(source_feed_version, source_sha256, agency_id)` y los atributos originales de cada versión. Las relaciones con rutas usarán esos tres campos. No sobrescribiré el histórico ni construiré ahora una homologación entre años. Dejé las reglas en el [plan Silver](docs/silver_design.md).

**Alcance:** quedó documentada la decisión. Todavía no he creado tablas o transformaciones Silver. Antes de publicar comprobaré que una reejecución no duplique el snapshot ni altere otras versiones.

### Hito 15 — Contrato v1 de agency antes de publicar Silver

**Fecha:** 6 de noviembre de 2026. Después de entender el perfilado de ambos snapshots, definí el [contrato v1 de agency](docs/contracts/agency.md). Todos sus campos de negocio conservarán string. Exigiré ID con contenido para estas versiones con varias agencias y mantendré la clave por versión, hash e ID.

**Las reglas:** separé campos requeridos, ausencias opcionales y valores presentes que no cumplen su formato. No rellenaré desde otro año ni convertiré un error en null sin explicarlo. En la primera implementación, un error bloqueante impedirá publicar un snapshot parcial; la evidencia de rechazo quedará en cuarentena y auditoría cuando las implemente.

**Mi límite:** completitud y unicidad ya fueron revisadas. Aún no he ejecutado los validadores de formato de URL, zona e idioma, ni creado Silver. Documenté el alcance acotado de teléfonos y correo y las pruebas necesarias para no presentar controles básicos como una validación integral.

**Cómo continuaré:** prepararé los validadores y la transformación determinista con su runbook y sus pruebas. Comprobaré que una reejecución mantenga las claves y valores de negocio y no altere el otro snapshot. Este hito modifica documentación; no datos ni notebooks.

### Hito 16 — Validadores de agency y primer contraste del contrato

**Fecha:** 6 de noviembre de 2026. Implementé las reglas en módulos Python pequeños y preparé el notebook 09 para ejecutarlas con PySpark. El notebook lee Bronze y el encabezado Staging, limita agency a 1.000 filas y muestra candidatos, rechazos con motivos y advertencias. No escribe tablas ni modifica el Job.

**Qué probé:** la suite completa terminó con 51 pruebas: 45 aprobadas y 6 omitidas porque falta PySpark local. Java sí está disponible. Los casos del núcleo incluyen ausencias, URLs inválidas, idiomas y zonas, controles, conflictos, copias y separación de snapshots. Las seis omitidas requieren Spark; no las cuento como aprobadas.

**El contraste real:** recuperé mediante Genie las 14 filas completas y los encabezados auditados, sin truncamiento. Ejecuté localmente el mismo núcleo Python que usa el notebook: cada snapshot produjo siete candidatos, cero rechazos, cero copias consolidadas y cero advertencias, con reconciliación correcta. Fijé langcodes 3.5.1 y tzdata 2026.6. Guardé el [SQL y el informe agregado](docs/agency_validation_2025_2026.md), no las filas fuente en Git.

**La diferencia que mantengo clara:** el núcleo ya fue ejecutado con datos reales; eso no demuestra la ejecución del notebook 09, la importación de módulos en Workspace ni el lector Spark. Tampoco he persistido Silver o cuarentena ni probado transacciones Delta.

**Mi siguiente comprobación:** ejecutar 09 por bloques en Databricks, con el repositorio completo y cada snapshot, antes de preparar la escritura limitada al snapshot y sus pruebas de reintento.

### Hito 17 — Publicación por snapshot y base del Job Silver

**Fecha:** 6 de noviembre de 2026. Terminé de revisar las salidas del notebook 09 ejecutado en Databricks para 2025 y 2026: siete candidatos, cero rechazos, cero copias y cero advertencias por snapshot, con reconciliación correcta. Así cerré la comprobación del lector y el validador antes de preparar escrituras.

**Qué preparé:** implementé publicación Delta por versión y hash, cuarentena y auditoría por intento. El notebook 10 ejecuta lectura, validación y publicación con una llamada, sin repetir manualmente 08 y 09. El [registro de entidades](databricks/config/silver_entities.json) habilita solo agency; otras entidades necesitarán su contrato y procesador.

**La comprobación:** ejecuté la suite completa en Linux con Spark 4.0.1 y Delta 4.0.0: 64 pruebas aprobadas, sin omisiones. Comprobé las catorce filas de dos snapshots sintéticos, reejecución sin duplicación, conservación de nombres históricos, dos hashes con la misma fecha, rechazo sin alterar Silver, cuarentena y un fallo posterior a un commit. No confundí estas pruebas locales con una publicación en el workspace.

**La automatización:** dejé versionada una [plantilla de Job manual](databricks/jobs/gtfs_bogota_silver_manual.template.json) y su generador, con For each para los dos snapshots y concurrencia 1. Las reglas rutinarias se ejecutarán juntas; revisaré manualmente incidencias y decisiones de negocio. No tiene horario automático y todavía no fue creado en Databricks.

**Lo que falta:** sincronizar el notebook 10, crear el Job y ejecutar la primera publicación en el workspace. Ya identifiqué la raíz del repositorio y generé su configuración real fuera de Git. Al comprobar la carpeta, la consola indicó que no admite control automatizado; detuve la interacción sin crear recursos. Genie permite consultas, pero sus herramientas disponibles no crean Jobs y no tengo un perfil CLI local autenticado. La [guía de ejecución](docs/silver_execution.md) deja el procedimiento y la evolución hacia más tablas.

### Hito 18 — Agency publicada y Job manual comprobado

**Fecha:** 6 de noviembre de 2026. Publiqué agency para 2025 y 2026 desde el notebook 10. El primer resultado confirmó siete filas, cero rechazos y lectura posterior correcta; después apareció el segundo snapshot. Creé el Job manual y, tras corregir una sintaxis del notebook, obtuve dos ejecuciones exitosas. Confirmé con Genie siete filas e IDs únicos por snapshot, con agency_v1.

Resolví dos diferencias entre preparar código y ejecutarlo: el entorno del notebook 10 necesitaba sus propias dependencias y errorifexists no era compatible con la primera creación. Cambié a writeTo(...).using("delta").create() y comprobé que no reemplaza una tabla existente. Al reiniciar Python tuve que volver al bloque de imports antes de ejecutar funciones.

### Hito 19 — Routes con contrato propio y pipeline compartido

**Fecha:** 6 de noviembre de 2026. Perfilé routes de ambos snapshots mediante Genie, recuperando resultados estructurados y conservando el SQL de lectura. Encontré 676 y 1.045 rutas, sin IDs vacíos, copias, conflictos ni agencias huérfanas en los controles ejecutados. El nombre largo nulo de 2025 tiene nombre corto; route_desc no fue publicado en 2026. No convierto estas diferencias en afirmaciones sobre operación real o continuidad entre años.

Definí [routes_v1](docs/contracts/routes.md) e implementé sus conversiones, controles y duplicados con expresiones Spark. Reutilicé el escritor, auditoría, cuarentena y notebook 10; mantuve el esquema de agency. Fijé versiones Delta de entrada y preparé una etapa routes que depende del éxito de agency.

Simplifiqué la ejecución: no copié notebooks 08 y 09 para routes, retiré la instalación y los dos reinicios que se repetían por iteración y eliminé el conteo histórico adicional del notebook 10. El resumen de publicación ya verifica la salida. Mi objetivo es reducir trabajo repetido sin quitar controles; no afirmo una mejora de tiempo hasta medir el Job ampliado.

**Validación local:** pasaron 75 pruebas completas con Spark 4.0.1 y Delta 4.0.0, sin omisiones, y tres pruebas adicionales de despacho del pipeline sin IO. Comprobé reintentos, cuarentena y conservación de ambos snapshots; no extrapolo ese resultado a un tiempo de ejecución en Free Edition.

**Alcance:** el perfil de origen y la dependencia agency están consultados en Databricks. El nuevo código y la plantilla están preparados localmente; todavía debo sincronizarlos, actualizar el Job existente y ejecutar routes_v1 en Workspace. No he modificado Bronze ni publicado routes mediante Genie.

### Hito 20 — Corregir el lector del pipeline tras la primera ejecución ampliada

Al ejecutar el Job ampliado encontré un doble entrecomillado de identificadores: el pipeline entregaba nombres con backticks a un lector que esperaba nombres planos. El fallo bloqueó agency antes de validar y dejó routes sin ejecutar. Corregí ambas rutas del código conservando la validación estricta de nombres.

Las pruebas previas de despacho sustituían el lector, por lo que no detectaron esa incompatibilidad. Cambié esas pruebas para ejecutar la función real y reproduje el mismo ValueError antes de corregirlo. Añadí un recorrido con tablas Delta de prueba para agency, routes y reintento. Pasaron las tres pruebas de despacho corregidas y la nueva prueba de integración con Spark y Delta reales, incluido el reintento de routes sin duplicados. La recuperación del Job en el workspace requiere sincronizar la corrección y reparar el run; no presento las pruebas locales como esa recuperación.

### Hito 21 — Cerrar la ejecución de routes y comenzar stops con evidencia

**Actualización al 10 de noviembre de 2026:** después de sincronizar el fix del lector ejecuté el Job ampliado agency → routes y comprobé que existen las tablas Silver. Actualicé las guías que todavía mostraban esa ejecución como pendiente. La confirmación corresponde al resultado que revisé durante el desarrollo; hoy no hice una nueva consulta de Silver para volver a demostrarlo.

Completé el [perfil de stops](docs/stops_profile_2025_2026.md) mediante Genie en modo lectura, recuperando seis resultados estructurados sin truncamiento. En 2025 encontré 6.530 ubicaciones de tipo parada/plataforma; en 2026, 8.159 de ese tipo y 155 estaciones. Los IDs son únicos en ambos snapshots y las 750 referencias a padres de 2026 resuelven hacia estaciones del mismo snapshot. Las comprobaciones ejecutadas de conversión, rangos y jerarquía no encontraron errores.

Hay decisiones reales que revisar: 4 / 159 códigos opcionales nulos, 27 / 1 nombres con espacios extremos y wheelchair_boarding ausente en 2025. No relleno la accesibilidad histórica con la de otra versión ni deduplico por nombres o códigos repetidos.

Conservé las consultas en [un solo notebook de lectura](databricks/notebooks/silver/11_profile_gtfs_stops.ipynb), sin duplicar un archivo SQL ni añadir otro paso al Job. Sustituí una consulta inicial de nueve CTEs por una agregación compacta por campo con regex Unicode, y comprobé su resultado mediante Genie. El contenedor del notebook está preparado, no ejecutado de principio a fin. Stops sigue pendiente de contrato implementado y publicación; el próximo paso es entender este perfil y cerrar sus reglas.

### Hito 22 — Implementar stops y definir cómo explicaré cada tabla Gold

**Fecha:** 10 de noviembre de 2026. Cerré [stops_v1](docs/contracts/stops.md) e implementé sus reglas con Spark nativo: coordenadas double, tipos de ubicación y accesibilidad int, identificadores string y limpieza Unicode solo en los bordes del nombre. Conservé las ausencias y la identidad por versión + hash + ID. Compruebo la jerarquía dentro del mismo snapshot, agrupo padres antes de unir para no multiplicar hijos y mantengo visibles los conflictos fuente antes de normalizar. Una estación sin hijos referenciados genera advertencia; no invento sus plataformas.

Reutilicé el notebook 10, la escritura Delta, auditoría y cuarentena. Extraje la preparación y reconciliación que compartían routes y stops a spark_validation.py, conservando las reglas propias de cada tabla. Es como usar el mismo control de entrada para dos salas: cada una sigue teniendo sus condiciones, pero no necesito construir dos puertas idénticas. La plantilla añade publish_stops después de routes para serializar escrituras, sin declarar una dependencia de datos entre ambas.

**Verificación local:** pasaron las 91 pruebas completas, sin omisiones, con Spark 4.0.1 y Delta 4.0.0. Incluyen los contratos anteriores, las reglas de stops y un recorrido con Delta real: dos snapshots, reintento sin duplicados y rechazo con cuarentena sin alterar Silver. Usé datos sintéticos y un encabezado Staging de prueba; no ejecuté stops en mi workspace durante esta comprobación. No afirmo una mejora de tiempo del Job hasta medirla allí.

Añadí al [plan](docs/silver_design.md#definición-de-negocio-obligatoria-para-cada-futura-tabla-gold) una ficha obligatoria para cada futura tabla Gold: qué pregunta responde, qué representa una fila, qué ubicaciones incluye, cómo trata ausencias, qué claves usa y qué limitaciones debe mostrar Power BI. Así un conteo de ubicaciones no se presentará como crecimiento físico demostrado, ni un campo de accesibilidad ausente como falta de accesibilidad.

**Lo que sigue:** sincronizar el repositorio, validar stops de ambos snapshots con el notebook 10 y revisar los resúmenes antes de publicar. Después ampliaré el Job manual y comprobaré su reejecución. No necesito repetir Bronze ni añadir el notebook de perfilado al Job. La [guía de ejecución](docs/silver_execution.md#mi-siguiente-despliegue-stops_v1) conserva los parámetros y resultados esperados; todavía no hay una publicación de stops comprobada en Databricks.

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
- [x] Primera entidad Silver (agency) publicada con métricas de calidad, cuarentena y Job manual.
- [ ] Versión del GTFS estático vinculada a entidades realtime.
- [ ] Primera métrica Gold de velocidad operacional y cobertura de flota.
- [ ] Baseline histórico y detección determinista de anomalías.
- [ ] Dashboard Power BI con definiciones de KPI.
- [ ] Agente n8n/Ollama en lectura para informe diario verificable.
- [ ] CI, runbook y retrospectiva final del proyecto.

## Regla editorial final

Quiero que esta bitácora permita seguir mi razonamiento: qué problema encontré, qué decidí y con qué evidencia puedo sostener el resultado.
