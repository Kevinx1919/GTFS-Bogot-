# Plan de trabajo de Silver — Bogotá GTFS Mobility Lakehouse

## 1. Estado y propósito

**Estado de este documento:** este es mi plan para construir Silver por etapas. La carpeta Silver contiene una guía SQL de agency como punto de entrada y un perfilador PySpark como alternativa. Revisé las salidas del perfilador PySpark de agency para 2025 y 2026 y las contrasté con consultas SQL mediante Genie. La guía SQL con widgets no tiene una comprobación de ejecución completa documentada. El [contrato v1 de agency](contracts/agency.md) define el primer incremento. Su núcleo Python de validación ya fue implementado y contrastado; el notebook 09 de lectura fue ejecutado y revisado en Databricks para ambos snapshots. La [publicación y el Job manual](silver_execution.md) ya están preparados y probados localmente con Delta real. Agency ya fue publicada para ambos snapshots y su Job manual terminó con éxito. Implementé y publiqué [routes_v1](contracts/routes.md) con Spark y el Job compartido. Al 10 de noviembre completé el [perfil de stops](stops_profile_2025_2026.md) en lectura. El contrato stops_v1 ya está implementado y ejecutado en Databricks: comprobé el Job, la tabla Silver y sus datos con una consulta breve. Calendar y calendar_dates ya están implementados y publicados: ejecuté sus tareas y consulté las tablas en Workspace. Service_dates está publicada y consultada para 2026: 1.403 pares únicos, siete servicios y fechas de enero a diciembre. Completé el perfil e implementé shape_points. Sus 36 pruebas seleccionadas pasaron. El flujo ya funciona en Databricks. Completé el perfil de trips, orden 6. Su contrato está implementado. Las 37 pruebas seleccionadas pasaron. El Job de trips ya funciona. Las nueve entidades actuales tienen despliegue funcional en Workspace. Continúo con stop_times, orden 8. Las demás entidades continúan como propuestas. El [cierre de stops](silver_execution.md#cierre-de-la-ejecución-de-stops) distingue esta comprobación de los conteos del perfil y de las pruebas locales.

**Punto de partida:** al reejecutar 04 comprobé que reconoció los hashes ya cargados de las ocho entidades de referencia de cada versión. La auditoría 07 de 2025 terminó en PASSED, sin fallos ni advertencias; la de 2026 en WARNING, sin fallos bloqueantes y con cinco advertencias de esquema conocidas. Esto no significa que ya estén probados los tipos, la unicidad o todas las reglas GTFS que necesitará Silver.

**Propósito:** quiero convertir las tablas fuente de Bronze en entidades tipadas y relacionadas que pueda analizar sin perder su procedencia. Revisaré una entidad, entenderé sus resultados, definiré reglas y solo entonces escribiré su transformación. Raw y Bronze conservan la evidencia original.

Silver prepara datos para responder preguntas de oferta planificada. Los indicadores agregados para Power BI pertenecerán a Gold. Ninguna tabla estática demostrará por sí sola operación real, puntualidad, espera experimentada, ocupación o demanda.

## 2. Aclaración: asignar tipos y rellenar datos son decisiones distintas

Me ayuda pensarlo como un código de producto: aunque tenga solo dígitos, lo uso para identificar, no para sumar. Si convierto "0012" a entero pierdo sus ceros; primero debo decidir qué significa ese campo. Es un ejemplo, no un error que haya encontrado en mis snapshots.

Asignar un tipo es indicar qué clase de valor admite una columna. Completar un dato faltante exige una regla y evidencia adicionales. Inicialmente no rellenaré ausencias con cero, texto genérico, promedios ni valores de otra versión.

| Campo y entrada de ejemplo | Resultado propuesto | Por qué |
| --- | --- | --- |
| route_id = "0012" | string "0012" | Es una identidad; conserva los ceros. |
| route_type = "3" | int 3 | Es un código cuyo dominio se debe validar. |
| stop_lat = "4.65" | double 4.65 | Es una coordenada sobre la que haré cálculos. |
| stop_lat = "texto" | Error de conversión registrado; conserva el original | Un valor inválido no equivale a una ausencia original. |
| Campo opcional vacío | null tipado si el contrato lo admite | Desconocido no significa cero. |

Los ejemplos son sintéticos, no hallazgos de los snapshots. En Spark usaré int, double, string y también date, decimal o timestamp cuando el significado lo requiera. Una columna que contiene números no debe convertirse automáticamente a un tipo numérico.

## 3. Ciclo que repetiré por cada entidad

| Paso | Qué haré | Entregable y condición para continuar |
| --- | --- | --- |
| 1. Seleccionar | Leer una sola versión y hash de Bronze; revisar auditoría y encabezados originales. | Snapshot explícito; origen disponible y sin fallos bloqueantes pendientes. |
| 2. Entender el grano | Explicar qué representa una fila y proponer su clave. | Una definición como "una ruta dentro de un snapshot"; nunca usar el nombre como identidad sin evidencia. |
| 3. Perfilar | Contar filas, claves distintas, nulos, cadenas vacías, espacios, valores frecuentes y problemas de formato. | Resumen por columna y por versión; ejemplos pequeños de los problemas, sin dar por sanos los datos antes de medirlos. |
| 4. Examinar duplicados | Separar filas idénticas de claves repetidas con atributos distintos. | Conteo y ejemplos de cada situación; decisión explícita para cada caso. |
| 5. Acordar contrato | Definir tipo, obligatoriedad, valores válidos, relaciones y consecuencia del error. | Ficha de columnas aprobada antes de transformar. |
| 6. Transformar | Aplicar conversiones y normalizaciones acordadas con funciones deterministas de Spark. | DataFrame tipado; valores originales recuperables desde Bronze y la evidencia de rechazo. |
| 7. Validar y separar | Evaluar claves, conversiones, dominios, relaciones y coherencia entre campos. | Aceptados, cuarentena y métricas explican toda la entrada; no hay descartes silenciosos. |
| 8. Probar | Ejecutar fixtures pequeños con casos correctos y de error. | Pruebas aprobadas; luego comprobación real en Databricks. |
| 9. Persistir y repetir | Guardar solo el snapshot seleccionado y verificar una segunda ejecución. | Mismas claves y valores de negocio con la misma entrada y reglas, sin duplicar filas ni alterar otras versiones. |
| 10. Documentar | Registrar decisiones, errores reales, resultados y límites. | Runbook y bitácora actualizados; puedo explicar el resultado antes de pasar a otra entidad. |

La primera ejecución de perfilado será de lectura: no guardará entidades Silver ni modificará Bronze. Si posteriormente decido persistir métricas de perfilado, se documentará ese efecto antes de añadirlo.

### Qué voy a medir sin mezclar categorías

- **Nulo:** no hay valor almacenado. Mediré su cantidad y porcentaje.
- **Vacío:** existe la cadena "". Si el lector CSV ya la convirtió a null, no afirmaré recuperar esa distinción desde Bronze; consultaré el archivo original cuando sea necesario.
- **Solo espacios:** el texto no aporta contenido después de trim; se medirá antes de normalizar.
- **Columna ausente:** no existía en el encabezado de ese snapshot. Usaré audit_gtfs_source_schema_observations; no se deduce únicamente de los null de la tabla histórica.
- **Inválido:** existe un valor, pero no cumple el formato, rango o regla acordados.

Los conteos pueden incluir categorías derivadas del mismo valor; no los sumaré como si fueran grupos independientes sin definir una clasificación exclusiva.

### Ficha que completaré antes de programar cada tabla

| Columna | Tipo propuesto | Obligatoria o condicional | Nulos/vacíos observados | Regla | Acción ante error | Decisión pendiente |
| --- | --- | --- | --- | --- | --- | --- |
| Cada campo publicado o derivado | Tipo explícito | Según significado y contrato | Se mide; no se rellena con un resultado esperado | Formato, rango, dominio o relación | Bloqueo, cuarentena, advertencia o informativo | Se cierra con evidencia |

## 4. Orden de trabajo y entidades propuestas

Llamaré **S** a la pareja (source_feed_version, source_sha256). Todas las claves y relaciones se evaluarán dentro de S. No mezclaré filas de 2025 y 2026 en un join por ID aislado. Una fecha de publicación no es una fecha de servicio. run_id identifica una ejecución, no una ruta o parada.

Agency, routes y stops ya tienen sus tablas silver_gtfs_* publicadas y su ejecución revisada en Workspace. El orden 4a, calendar y calendar_dates, ya está ejecutado en Databricks y comprobé sus datos. El orden 4b, service_dates, está publicado para 2026. Shape_points, orden 5, ya funciona en Databricks. Trips, orden 6, ya funciona. Frequencies, orden 7, ya funciona. Continúo con stop_times, orden 8. Los nombres y tipos de las demás entidades continúan como propuestas. Los archivos opcionales se procesarán solo si están publicados; su ausencia se documentará sin inventar registros.

| Orden | Entidad Silver | Qué representa una fila / clave dentro de S | Tipos principales propuestos | Qué revisaré y qué permite analizar |
| --- | --- | --- | --- | --- |
| 1 | agency | Una agencia o marca; agency_id cuando exista y sea válido | IDs, nombre, URL, idioma, teléfono y zona horaria: string | Unicidad, campos requeridos, URL y zona; prepara la relación con rutas. |
| 2 | routes | Una ruta; route_id | IDs, nombres, descripción, colores: string; route_type: int | Clave, nombre utilizable, códigos, agencia y campos de esquema; catálogo de rutas por versión y modo. |
| 3 | stops | Una ubicación GTFS; stop_id | IDs y nombre: string; latitud/longitud: double; location_type y wheelchair_boarding: int | Coordenadas y obligatoriedad según tipo, padre y jerarquía; ubicaciones publicadas, distinguiendo paradas de estaciones. |
| 4a | calendar y calendar_dates | Patrón de servicio: service_id; excepción: service_id + date | IDs: string; fechas: date; días semanales y exception_type: int | Fechas, códigos y duplicados; definir qué servicio se planifica y cuándo. Se aceptan las fuentes disponibles, no se exige que existan ambas. |
| 4b | service_dates, derivada | Un servicio activo en una fecha; service_id + service_date | ID: string; service_date: date; procedencia de activación: string | Aplicar patrón y excepciones; habilita análisis de oferta por fecha, sin expandir todavía todos los horarios. |
| 5 | shape_points | Un punto de trazado; shape_id + shape_pt_sequence | ID: string; secuencia: int; coordenadas y distancia publicada: double | Orden y rangos; geometría publicada, sin multiplicar horarios al unir todos los puntos. |
| 6 | trips | Un viaje o patrón publicado; trip_id | IDs y headsign: string; direction_id, si existe: int | Unicidad y referencias a rutas, servicios y geometrías cuando corresponda; patrones de viaje por ruta. |
| 7 | frequencies, si existe | Una ventana de un viaje; trip_id + inicio convertido | ID y horas fuente: string; segundos: long; headway_secs y exact_times: int | Ventanas, intervalos y relaciones; distinguir servicio por frecuencia de horarios exactos. |
| 8 | stop_times | Una visita planificada a una parada; trip_id + stop_sequence | IDs y horas fuente: string; secuencia y códigos: int; segundos: long; distancia: double | Visitas repetidas, conversiones y coherencia temporal; secuencia y horarios planificados por viaje. |
| 8b (operación) | Planificador de snapshots Silver, pendiente | Un trabajo por entidad + snapshot + regla | Metadata y listas JSON; no crea una entidad analítica | Selección dinámica desde Bronze validado, auditoría, dependencias, reintentos y salida sin novedades. Antes de programar el Job. |
| Después, según pregunta | feed_info y tarifas | feed_info: una fila por snapshot; fare_attributes: fare_id; fare_rules: combinación completa de campos de regla publicados | Metadata y IDs: string; fechas: date; importes: decimal con precisión/escala acordadas; códigos: int | Metadata y reglas tarifarias; no se fabrican filas cuando falta un opcional. No forman parte del primer incremento. |

Revisé siete filas y siete IDs distintos con contenido de agency en ambos snapshots. Ese resultado no implica siete empresas jurídicas ni continuidad de identidad entre años. Si llega un caso válido de agencia única sin ID, ampliaré el contrato antes de procesarlo; la v1 actual requiere ID fuente y no lo fabricará. No se resolverán agencias múltiples mediante nombres parecidos.

La referencia de servicios usa los IDs declarados por los calendarios disponibles. service_dates deriva los días activos; no se exigirá que un servicio tenga días dentro de un horizonte de consulta arbitrario para afirmar que su ID existe.

### Decisión acordada: conservar la identidad de cada snapshot

**Decisión inicial: 6 de noviembre de 2026. Estado al 10 de noviembre: implementada para agency y routes.** Elijo preservar el histórico con la clave `(source_feed_version, source_sha256, agency_id)`. Mantendré los nombres, IDs y URLs publicados en cada versión. La URL será un atributo, no una clave.

Encontré el ID `2` asociado a `TRANSMILENIO-DUAL` en 2025 y a `Transmilenio-Alimentadores` en 2026. No tengo evidencia del motivo de ese cambio. Una regeneración de códigos o una reorganización son posibilidades, no causas confirmadas. Es como guardar dos listas de un curso: el mismo número de lista en años distintos no garantiza que represente a la misma persona.

Aplicaré estas reglas en el primer incremento:

- Relacionaré `routes` y `agency` por versión, hash y `agency_id` juntos. No cruzaré snapshots por el ID aislado.
- No reemplazaré nombres o códigos de 2025 con valores de 2026. Tampoco deduplicaré agencias entre snapshots.
- Al reejecutar una transformación, su escritura se limitará al snapshot seleccionado; verificaré que las demás versiones sigan intactas.
- No crearé por ahora una identidad común ni una categoría homologada entre años. Una eventual correspondencia será independiente, explícita y respaldada por evidencia.
- Un cambio de atributos entre snapshots se registrará como hallazgo histórico. Un ID repetido con atributos contradictorios dentro del mismo snapshot seguirá siendo un conflicto de calidad.

Esta decisión protege el histórico; no demuestra continuidad de agencias, rutas ni operación entre versiones. Posteriormente apliqué la identidad por snapshot en las publicaciones de agency, routes y stops.

### Primer incremento: agencias y rutas

1. Perfilar agency de 2025; revisar su ficha; repetir para 2026.
2. Comparar completitud y encabezados: agency_fare_url no se publicó en 2025 y tiene siete valores con contenido en 2026. Su formato y disponibilidad web son comprobaciones distintas; la disponibilidad queda fuera de v1.
3. Aplicar el [contrato v1 de agency](contracts/agency.md), conservando la identidad por snapshot. Preparar y comprobar sus validadores antes de publicar su transformación; después continuar con el perfilado completo de routes.
4. Perfilar routes por separado en cada snapshot; revisar IDs, nombres, tipo, colores y relación con agency.
5. Documentar la ausencia de route_desc en el archivo de 2026; conservar la diferencia entre campo ausente y celda vacía.
6. Acordar y probar routes; verificar ambas versiones y la reejecución antes de continuar con stops.

No se usarán 676 y 1.045 registros de rutas para concluir automáticamente altas y bajas reales. Compararé claves y atributos; los cambios de codificación pueden requerir correspondencias respaldadas por evidencia.

## 5. Reglas transversales de calidad

| Situación | Tratamiento propuesto | Motivo |
| --- | --- | --- |
| Clave crítica vacía o conversión obligatoria inválida | Registrar el rechazo; no publicar la entidad hasta resolver o aprobar explícitamente una política parcial | Evitar que un identificador o dato esencial defectuoso contamine los análisis. |
| Filas idénticas de negocio en el mismo snapshot | Conservar una representación y auditar las copias consolidadas | Evitar duplicados manteniendo su multiplicidad; la comparación excluye timestamps de procesamiento. |
| Misma clave con atributos diferentes | Cuarentena y bloqueo de publicación de la entidad | No elegir una fila al azar con dropDuplicates. |
| Referencia obligatoria sin resolver | Registrar cuarentena y bloquear publicación inicial | Un join no debe eliminar silenciosamente registros. |
| Campo opcional sin valor válido | Aplicar su semántica y registrar el hallazgo; si se convierte a null, conservar original y motivo | No ocultar errores de conversión entre las ausencias originales. |
| Columna opcional ausente en el archivo | Registrar presencia en metadata y mantener el esquema curado acordado | Preservar la diferencia entre versiones. |
| Columna nueva o retirada | Revisar contra el contrato; no incorporar automáticamente a Silver | Una evolución de Bronze no aprueba por sí sola el uso analítico. |
| Nombre repetido o clave reutilizada entre snapshots | Investigar según grano; no deduplicar por nombre ni entre versiones | Puede representar entidades válidas o historia. |

No haré trim, mayúsculas o reemplazos en identificadores sin medir posibles colisiones. Conservaré la forma original para poder explicar cualquier normalización.

La reconciliación distinguirá grupos exclusivos: entrada = representaciones aceptadas + filas rechazadas + copias idénticas consolidadas. Si una clave tiene conflictos, todas sus filas se contabilizan como rechazadas; no se cuentan también como copias consolidadas. Una fila con varios errores cuenta una sola vez en cuarentena y puede tener varios motivos.

La cuarentena propuesta guardará S, entidad, clave candidata, contenido original, huella determinista, códigos de regla, versión de reglas y ejecución. La huella no identifica una línea física única cuando existen copias idénticas. No sustituye el ZIP original.

### Particularidades que verificaré antes de tipar

- Horas GTFS: conservar texto y segundos desde el día de servicio; 25:10:00 equivale a 90.600 segundos. No usar un tipo de hora limitado a 24 horas ni sumar esa hora a la fecha de publicación. El timestamp requiere fecha de servicio y zona de la agencia.
- Secuencias: validar enteros no negativos y orden; no exigir valores consecutivos. Una misma parada puede aparecer varias veces en un viaje.
- Horarios vacíos: evaluar el contexto y la precisión antes de rechazarlos; inicialmente no interpolar.
- Códigos: validar sus valores permitidos; un código con tres estados no se convierte a boolean. Un código de dirección no implica por sí solo norte o sur.
- Geometría: no asumir metros en shape_dist_traveled ni convertirla a distancia observada; confirmar unidades y coherencia.
- Frecuencias: exact_times distingue modalidades; no inventar salidas exactas para un servicio por intervalos ni contar su patrón como una salida adicional.

Estas condiciones proceden de la [referencia GTFS](https://gtfs.org/documentation/schedule/reference/), la [guía base](https://gtfs.org/getting-started/features/base/) y la [guía de complementos](https://gtfs.org/getting-started/features/base-add-ons/). Mi contrato se concretará por tabla; este documento no implementa un validador integral del estándar.

## 6. Persistencia, trazabilidad y configuración

**Implementado para agency y routes, con publicaciones confirmadas en el workspace:** reconstruir de forma determinista una entidad para S y reemplazar solo su ámbito después de validar, manteniendo las demás versiones. Antes de escribir comprobaré la selección y el comportamiento ante salida vacía. No se hará overwrite de toda la historia ni append indiscriminado en cada reejecución.

Cada resultado conservará source_feed_version, source_sha256 y source_file_path, y se asociará a silver_run_id, timestamp UTC, versión de reglas/código y manifiesto Raw. Cuando sea necesario fijaré la versión Delta leída de Bronze. Los campos técnicos de ejecución pueden cambiar entre reintentos; las claves y valores de negocio no deberían cambiar con la misma entrada y reglas.

Introduciré auditoría de ejecución, resultados de reglas y cuarentena junto al primer incremento. La metadata del snapshot podrá registrarse en una tabla de control o entidad auxiliar; no se creará una fila artificial de agencia o ruta para representar ese control. No se publicará un conjunto incompleto como si todas las entidades estuvieran validadas. Una escritura atómica de una tabla no garantiza una transacción de todas las tablas; evitaré ejecuciones concurrentes del mismo snapshot en la primera versión.

Catálogo, schema, Volumes, versión y hash serán parámetros. workspace.gtfs_bogota y los Volumes actuales serán defaults explicados del entorno de aprendizaje, no rutas personales fijas en funciones reutilizables. UTC se usa para procesamiento; la fecha de servicio y la zona de la agencia se manejan de forma explícita.

Antes del primer notebook de transformaciones confirmaré el runtime y el cómputo de Databricks. Puedo usar conversiones tolerantes como [try_cast](https://docs.databricks.com/aws/en/sql/language-manual/functions/try_cast), pero contaré sus fallos: devolver null no convierte el dato en válido.

## 7. Código, notebooks y pruebas

Carpeta creada: databricks/notebooks/silver/. Mantendré los notebooks anteriores en sus rutas para no afectar el Job Bronze. La carpeta organiza código, no almacena las tablas Delta ni necesita un Volume nuevo.

**Estado de notebooks:** empezar por [08_agency_sql_guiado.ipynb](../databricks/notebooks/silver/08_agency_sql_guiado.ipynb), que explica una pregunta por bloque y conserva el SQL completo en apéndices opcionales. 08_profile_gtfs_reference_entities.ipynb es la alternativa PySpark para automatizar después esas preguntas. No son dos pasos obligatorios. Agency y routes ya están revisadas y publicadas; [09_validate_gtfs_agency.ipynb](../databricks/notebooks/silver/09_validate_gtfs_agency.ipynb) aplica ahora las reglas de lectura, sin escritura. [10_publish_gtfs_entity.ipynb](../databricks/notebooks/silver/10_publish_gtfs_entity.ipynb) ya prepara la publicación y es la entrada del Job manual. El notebook 10 ya ejecutó las publicaciones de agency, routes y stops en el workspace. El [notebook 11](../databricks/notebooks/silver/11_profile_gtfs_stops.ipynb) conserva el perfil inicial de stops como guía de lectura, con seis consultas comprobadas mediante Genie; su ejecución completa como notebook aún no está documentada. La separación permite revisar resultados antes de introducir escrituras. Los bloques se documentarán en el runbook antes o al implementarlos.

Seguiré usando Python/PySpark dentro de notebooks para ejecutar y observar resultados. Las reglas se escribirán como funciones pequeñas; cuando necesite compartirlas y probarlas fuera del notebook, se extraerán a módulos versionados bajo databricks/. Las pruebas y fixtures pequeños se mantendrán en tests/. No se introduce ahora una nueva dependencia ni un framework de ejecución.

Casos mínimos por entidad: datos válidos, ID con ceros iniciales, null, vacío, espacios, columna opcional ausente, conversión inválida, duplicado idéntico, conflicto de clave, referencia rota y segunda ejecución sin duplicación. Se añadirán casos específicos: fechas inválidas y excepciones; horas mayores a 24; secuencias con saltos; parada repetida; frecuencias y opcionales ausentes.

Las pruebas por implementar tendrán dos niveles: fixtures locales para reglas deterministas y comprobación en Databricks para lectura/escritura Delta, métricas y reintento. Las 16 pruebas iniciales validaban las correcciones Raw/Bronze. La suite local ampliada tiene 105 casos únicos aprobados sin omisiones, incluida la repetición de publicación Delta tras ajustar su montaje temporal; el detalle de ejecución real se conserva por separado en la guía operativa. No usaré llamadas reales a las fuentes como única prueba automática.

## 8. Rendimiento y criterio de terminado

Con stop_times filtraré S y columnas al principio, agruparé métricas para reducir lecturas y evitaré collect de millones de filas, ordenamientos globales y UDF de Python cuando existan funciones Spark. Los joins y ventanas pueden redistribuir datos; se medirán. Usaré cache solo si se reutiliza el resultado y su costo lo justifica, liberándolo al terminar.

No expandiré todo stop_times por todas las fechas al comenzar. Elegiré particionado u otras optimizaciones después de medir tamaño, archivos, duración y lecturas; el número de filas por sí solo no decide el diseño físico.

Una entidad estará terminada cuando su grano y contrato estén documentados; las métricas expliquen la entrada; las filas publicadas cumplan claves, tipos y relaciones; los rechazos preserven evidencia; las pruebas pasen; la reejecución mantenga resultados de negocio; otras versiones sigan intactas; y yo pueda explicar qué obtuve y por qué lo considero válido. Solo entonces pasaré a la siguiente.

**Estado actual del primer paso:** revisé las salidas del perfilador PySpark de agency de ambos snapshots y los resultados SQL. Definí el [contrato v1](contracts/agency.md): tipos string, identidad por snapshot y política de ausencias y errores. El [núcleo de validación](agency_validation_2025_2026.md) ya pasó las pruebas locales y el contraste con ambos snapshots. El notebook 09 ya fue ejecutado para ambos snapshots en Databricks. Implementé cuarentena, auditoría y publicación, con pruebas Delta de reejecución aprobadas localmente. El Job ya ejecutó agency, routes y stops en Workspace; comprobé sus tablas y, al cerrar stops, consulté sus datos. La siguiente entidad fuente se revisará en el bloque conjunto calendar/calendar_dates.

## 9. Cómo empieza la revisión de agency

El bloque 2 muestra el tipo actual de cada columna mediante printSchema. Las columnas fuente se esperan como string por el diseño de Bronze; esto se comprueba antes de calcular el perfil. El encabezado de agency.txt en Staging determina si el proveedor publicó cada campo en esa versión.

El bloque 3 separa tipo Bronze, presencia fuente y tipo Silver propuesto. Calcula nulos, cadenas vacías, texto compuesto solo por espacios, texto no vacío, valores distintos no vacíos y espacios en extremos. Las primeras cuatro categorías son exclusivas; los valores distintos y los espacios extremos son diagnósticos adicionales. Si el lector CSV ya convirtió un vacío a null, el perfil no inventa su estado original. Un campo que no existía en el encabezado no se confunde con un campo publicado completamente vacío.

| Campo conocido | Propuesta Silver | Motivo y revisión posterior |
| --- | --- | --- |
| agency_id | string | Identificador, no cantidad; revisar unicidad y obligatoriedad. |
| agency_name | string | Nombre publicado; comprobar contenido sin usarlo como clave. |
| agency_url | string | URL; revisar formato antes de aprobar el contrato. |
| agency_timezone | string | Nombre de zona horaria, no fecha ni timestamp; validar su significado después. |
| agency_lang | string | Código de idioma; revisar valores publicados. |
| agency_phone | string | Conservar signos, ceros y formato telefónico. |
| agency_fare_url | string | Campo opcional; comprobar presencia y contenido por versión. |
| agency_email | string | Contacto opcional; su fila de perfil no implica que exista en la fuente. |

Otros campos publicados quedarían con tipo propuesto pendiente; no se convierten automáticamente por parecer numéricos. Esta tabla refleja los campos conocidos del proyecto, no todos los posibles campos futuros de GTFS.

El bloque 4 separa grupos de filas de negocio idénticas de IDs repetidos con atributos diferentes. Excluye columnas técnicas de la comparación y muestra potenciales colisiones de IDs al quitar espacios, sin aplicar esa limpieza. Las muestras se limitan a 20 filas; las métricas se calculan sobre todo el snapshot seleccionado. Solo se trae al driver una fila agregada por conjunto de métricas.

**Validación inicial del perfilador:** pasaron seis pruebas nuevas de parámetros y encabezados y las 16 existentes de Raw/Bronze. Tres pruebas adicionales con fixtures de Spark quedaron omitidas porque no están instalados PySpark y Java como entorno de pruebas local completo. Después revisé las salidas de ejecución manual del notebook en Databricks para ambos snapshots: siete filas e IDs distintos, sin ausencias en los campos publicados ni duplicados. Eso no ejecuta las tres pruebas de fixtures omitidas ni demuestra todavía validación de formatos o escrituras Silver.

El primer [informe real de agency 2025](agency_profile_2025.md) conserva la evidencia de esa revisión. El [contrato v1 de agency](contracts/agency.md) documenta las reglas que implementé y publiqué posteriormente en el workspace. El informe conserva el estado y los resultados de la revisión inicial.


## Incremento routes y ciclo simplificado

Apliqué el mismo ciclo de agency a routes, conservando el perfil inicial y el contrato sin copiar notebooks intermedios. El [perfil](routes_profile_2025_2026.md) registra presencia, nulos, duplicados, tipos, colores y referencias; el pipeline evalúa las reglas en cada corrida. Route_type y route_sort_order son int; los demás campos admitidos son string.

No convierto el límite de 1.000 filas de agency en una regla para todas las tablas: routes ya tiene 1.045 filas en 2026 y se procesa en Spark. El Job ampliado y ejecutado ordena agency antes de routes; el pipeline exige la dependencia del mismo snapshot. La [guía operativa](silver_execution.md) detalla las simplificaciones y el procedimiento para ampliar el flujo tras cerrar los próximos contratos.


## Siguiente bloque: calendar y calendar_dates

**Estado al 10 de noviembre de 2026:** cerré la ejecución de stops y completé el [perfil conjunto de calendar/calendar_dates](calendars_profile_2025_2026.md), con [contratos implementados](contracts/calendars.md). Implementé y publiqué calendar_v1 y calendar_dates_v1; ejecuté el Job ampliado y comprobé las tablas y su información en Workspace. Encontré intervalos 2000–2099 y excepciones de 2023 en el snapshot 2025; conservo esa evidencia y revisaré su alcance antes de derivar service_dates.

Calendar describe el patrón semanal de un servicio dentro de un intervalo de fechas. Calendar_dates registra excepciones para fechas concretas. Es como tener el horario habitual de una tienda y una lista de festivos en los que abre o cierra: necesito interpretar ambas fuentes juntas cuando estén publicadas.

1. Ya revisé encabezados, filas y controles de ambos snapshots en Bronze; el informe conserva presencia, completitud, claves y fechas. Las reglas siguientes guían el cierre del contrato. No volveré a ingerir Raw/Bronze.
2. Perfilaré claves, nulos, vacíos, duplicados idénticos y conflictos. La clave propuesta dentro del snapshot es service_id para calendar y service_id + date para calendar_dates.
3. Revisaré conversiones de fechas, intervalos, indicadores semanales y códigos de excepción. Los IDs seguirán como string; los tipos date e int siguen siendo propuestas hasta cerrar el contrato con evidencia.
4. Acordaré reglas para las combinaciones de fuentes disponibles; no exigiré que ambas existan ni trataré automáticamente un servicio declarado solo mediante excepciones como huérfano.
5. Cerré los contratos y reutilicé el pipeline, el escritor y el notebook 10. Las pruebas cubren fechas, claves compuestas, dependencia semanal condicional y reintentos; antes de afirmar publicación ejecutaré validate/publish en Databricks.

El orden 4b será service_dates: una fila por servicio activo y fecha, dentro de versión + hash, derivada del patrón y sus excepciones. No es otro TXT que deba descargar. No expandiré todavía los millones de horarios por todas las fechas ni confundiré fecha de publicación con fecha de servicio. La referencia de existencia de un servicio no dependerá de que tenga días activos dentro de un horizonte arbitrario de consulta.

## Próximo incremento: service_dates

**Estado al 12 de noviembre de 2026:** el despliegue de las dos fuentes y la primera derivación service_dates están completados. Comprobé la tabla derivada con 1.403 pares únicos y siete servicios en el horizonte 2026. El [cierre](silver_execution.md#cierre-de-la-ejecución-de-service_dates) distingue esa consulta de las pruebas locales. Shape_points ya funciona. Trips también funciona. Frequencies ya está publicada. El siguiente paso es stop_times.

Una fila representará un servicio activo en una fecha dentro del mismo snapshot. Aplicaré el patrón semanal en el intervalo correspondiente, añadiré excepciones de tipo 1 y retiraré las de tipo 2. Registraré la procedencia y el horizonte utilizado para no mezclar una expansión parcial con una cobertura completa.

Antes de implementar o publicar la derivación fijo el período que voy a calcular. En 2025, el intervalo fuente 2000–2099 no decide por sí solo un horizonte analítico y las excepciones son de 2023; no las traslado a otro año. Esta decisión no cambia las fuentes ni decide si existe un service_id. La existencia de servicios para validar trips se tratará independientemente de que tengan días activos en una ventana.

**Decisión de horizonte:** comenzaré solo con 2026-01-01 a 2026-12-31 del snapshot 2026-09-29. La [vista previa](service_dates_preview.md) calcula 1.403 pares activos, con [contrato derivado](contracts/service_dates.md) y procesador local preparados. Las 24 pruebas seleccionadas pasaron y la publicación en Databricks ya está comprobada con esos mismos 1.403 pares activos. El horizonte de 2025 no se añade a la primera tarea del Job.

Después de service_dates el plan continúa con shape_points, trips, frequencies y stop_times. Todavía no paso a Gold ni expando horarios por todas las fechas.

## Siguiente incremento: shape_points

Después de comprobar service_dates continúo con el orden 5. El [plan de shape_points](shape_points_plan.md) define el grano de punto de trazado, la clave S + shape_id + shape_pt_sequence, el mapeo desde shapes.txt/Bronze y las preguntas de perfilado. Los tipos y la política de calidad ya están implementados. El flujo ya funciona en Databricks.

Ya completé el [perfil inicial](shape_points_profile_2025_2026.md) mediante Genie: 909.878 / 926.501 puntos y 676 / 1.045 trazados, sin errores de claves o conversiones en los controles ejecutados. Conservé nueve consultas definitivas en el [notebook 14](../databricks/notebooks/silver/14_profile_gtfs_shape_points.ipynb). El [contrato implementado](contracts/shape_points.md) conserva segmentos de extremos iguales y trazados no referenciados; la distancia acumulada no está publicada. Después de revisar el significado y las reglas implementé el procesador. Reutilicé notebook 10 y el escritor. La plantilla añade una séptima tarea serial. Las 36 pruebas seleccionadas pasaron sin omisiones. El [cierre de shape_points](silver_execution.md#cierre-de-la-ejecución-de-shape_points) registra su despliegue funcional.

## Incremento completado: trips

Completé el [perfil de trips](trips_profile_2025_2026.md) con diez consultas definitivas. El [notebook 15](../databricks/notebooks/silver/15_profile_gtfs_trips.ipynb) conserva SQL verificado de lectura. Hay 107.162 / 181.060 trip_id únicos. Las referencias a rutas, servicios y trazados resuelven sin multiplicar filas.

El archivo 2025 no publica trip_headsign. El archivo 2026 lo publica sin contenido no blanco. La comparación directa con Staging coincide con Bronze para ese campo. No completaré esa ausencia con nombres de rutas.

El [contrato trips_v1](contracts/trips.md) conserva cinco campos string. Los IDs relacionan entidades; no son cantidades. El catálogo de servicios usa calendar/calendar_dates, no el horizonte de service_dates. Los 2 / 14 IDs relacionados con frequencies requieren su interpretación posterior. Implementé trips localmente y añadí su tarea a la plantilla. El [cierre de trips](silver_execution.md#cierre-de-la-ejecución-de-trips) registra su despliegue funcional confirmado.

## Incremento completado: frequencies

Completé el [perfil de frequencies](frequencies_profile_2025_2026.md) mediante nueve consultas correctas de lectura.
El [notebook 16](../databricks/notebooks/silver/16_profile_gtfs_frequencies.ipynb) conserva esas consultas.
Recuperé 77 filas estructuradas completas. Hay 2 / 14 ventanas, todas relacionadas con trips Silver del mismo snapshot.
No encontré errores en los controles ejecutados de completitud, claves, conversiones, procedencia y superposiciones por trip_id.
Todas corresponden a la ruta C_1, con route_type=6. Cada ventana actual usa un trip_id distinto.
No inferiré mejoras operativas desde el cambio de cantidad o intervalo.

Implementé el [contrato frequencies_v1](contracts/frequencies.md). Conserva horas fuente y deriva segundos de servicio como long.
Propone headway_secs int positivo y tratamiento explícito de exact_times ausente.
Implementé el procesador y añadí su tarea a la plantilla. El despliegue funcional de frequencies ya está confirmado.
Después de revisar el perfil implementé las reglas con Spark nativo y reutilicé notebook 10.
La plantilla añade publish_frequencies después de publish_trips. Las ocho tareas anteriores permanecen iguales.
La [guía de despliegue](silver_execution.md#despliegue-de-frequencies_v1) conserva parámetros y resultados esperados.
Las 42 pruebas seleccionadas pasaron sin omisiones. Frequencies ya está publicada en Databricks. El siguiente paso es perfilar stop_times, orden 8.
Stop_times seguirá después, en el orden 8. El planificador de snapshots permanece pendiente 8b.

## Siguiente incremento: stop_times

**Estado:** perfil completado y procesador local implementado. La publicación en Workspace permanece pendiente.
El [plan detallado](stop_times_plan.md), el [perfil](stop_times_profile_2025_2026.md) y el [contrato](contracts/stop_times.md) conservan las decisiones.
El [notebook 17](../databricks/notebooks/silver/17_profile_gtfs_stop_times.ipynb) contiene siete consultas verificadas de lectura.

Medí 5.698.892 visitas de 2025 y 9.408.893 visitas de 2026.
Conservo 61 visitas aisladas con advertencia. Registro 739 viajes sin visitas de 2026 como limitación de cobertura.
No invento paradas ni causas. No renumero secuencias válidas.
El contrato tipa campos, valida relaciones y compara horas como segundos del día de servicio.
Las frecuencias aportan contexto por viaje sin multiplicar las visitas.

La plantilla añade publish_stop_times como décima tarea. Reutilizo notebook 10, auditoría y escritor compartidos.
Las nueve tareas anteriores mantienen su configuración. El Job existente requiere actualización manual.
La [guía de despliegue](silver_execution.md#despliegue-de-stop_times_v1) explica validate y publish.
Archify conserva la revisión de las nueve entidades publicadas.
El planificador automático sigue pendiente 8b, después de comprobar este despliegue y antes de programar ejecuciones.

## Automatización pendiente: selección de snapshots Silver

**Estado:** pendiente, sin implementación. **Orden:** 8b, después de trips, frequencies y stop_times. Lo completaré antes de programar el Job automáticamente. Durante el desarrollo conservaré las listas manuales para ejecuciones controladas.

El Job actual usa listas fijas con versión/hash. Una versión nueva no entra automáticamente. El procesador acepta nuevos snapshots compatibles; la limitación actual está en seleccionar y entregar el trabajo.

Añadiré una tarea inicial propuesta, plan_silver. Consultará metadata de carga y validación Bronze. Contrastará cada entidad con audit_gtfs_silver_runs y sus dependencias. Construirá una lista dinámica por entidad. Los For each recibirán esas listas mediante valores de tarea.

Cada trabajo conservará entidad, source_feed_version, source_sha256 y la versión de reglas esperada. No elegiré solo la versión más reciente: pueden existir varios snapshots pendientes. La ejecución comprobará disponibilidad de fuentes y dependencias del mismo snapshot. No confundirá una fuente opcional ausente con una carga perdida.

Omitiré trabajos completados bajo la regla vigente y con publicación disponible. Mantendré pendientes los trabajos fallidos o rechazados. La auditoría y la comprobación del destino evitarán considerar terminada una publicación incompleta. Los reprocesamientos explícitos seguirán disponibles para corregir o reconstruir un snapshot.

Si no existe trabajo, el Job terminará sin publicar. Probaré listas vacías y sus efectos en las dependencias. La selección no recorrerá millones de filas de negocio. Usará metadata y auditoría, con comprobaciones acotadas cuando correspondan.

Service_dates conservará una política explícita de horizonte. La fecha de publicación no determina las fechas del servicio. Los contratos seguirán bloqueando cambios incompatibles. El planificador no aprobará esquemas nuevos ni modificará reglas automáticamente.

**Condiciones de cierre:** un snapshot Bronze válido genera el trabajo esperado; un trabajo completado se omite; un fallo queda pendiente. También comprobaré ausencia de novedades, reprocesamiento, dependencias opcionales, histórico y horizonte. Versionaré el planificador, la configuración y las pruebas antes de habilitar programación automática. No conecto esta responsabilidad con n8n/Ollama.

## Definición de negocio obligatoria para cada futura tabla Gold

Antes de implementar una tabla Gold completaré una ficha breve con estas seis respuestas. La conservaré junto a su SQL y la revisaré cuando cambien las reglas del indicador.

| Punto | Qué dejaré definido |
| --- | --- |
| 1. Qué pregunta responde | La pregunta de negocio concreta y el nombre del indicador. |
| 2. Qué representa una fila | El grano exacto: por snapshot, estación, fecha de servicio, franja u otra combinación explícita. |
| 3. Qué ubicaciones incluye | Tipos de stops incluidos, tratamiento de estaciones/plataformas y filtros aplicados. |
| 4. Cómo trata los valores ausentes | Qué ausencias se conservan como desconocidas, defaults normativos explícitos y cobertura disponible. No convertiré ausencia de accesibilidad en falta de accesibilidad. |
| 5. Qué claves usa para relacionar datos | Claves completas, versión/hash y cardinalidad esperada; cómo evitaré multiplicar filas al unir. |
| 6. Qué limitaciones debe mostrar Power BI | Alcance temporal, fuentes, cobertura y advertencias que cambian la lectura del indicador. |

Por ejemplo, un futuro conteo de ubicaciones publicadas por tipo tendría una fila por versión + hash + tipo de ubicación. Incluiría las ubicaciones Silver válidas del snapshot y distinguiría paradas/plataformas de estaciones. Un location_type no informado se interpretaría como tipo 0 únicamente mediante la semántica GTFS documentada; conservaría la evidencia fuente de ausencia. Códigos, zonas o accesibilidad opcionales ausentes no eliminarían lugares del conteo. El modelo relacionaría entidades mediante sus claves completas, sin duplicar ubicaciones por sus viajes u horarios.

En Power BI lo presentaría como catálogo publicado; la diferencia entre versiones no demostraría por sí sola expansión física o servicio efectivamente operado. Un análisis de accesibilidad explicaría que el archivo de 2025 no publicó ese campo. Este ejemplo es una propuesta de diseño: todavía no implementé una tabla Gold.

Las métricas de GTFS estático no tienen obligatoriamente grano de cinco minutos. Cada ficha define su grano; las futuras métricas operativas podrán usar esas franjas cuando la fuente y la pregunta lo permitan.

### Cobertura de viajes antes de calcular métricas Gold

Prepararé la clasificación de cobertura antes de las primeras métricas Gold, después de verificar stop_times Silver.
El [plan de cobertura](stop_times_plan.md#clasificación-de-cobertura-antes-de-las-métricas-gold) define sus reglas propuestas.
Conservaré una fila por viaje declarado y snapshot mediante trips y un left join con visitas agregadas.
Distinguiré sin_visitas, una_visita y varias_visitas. No interpretaré varias visitas como recorrido completo.
Cada métrica definirá horas necesarias, contexto de frecuencias, exclusiones y denominador.
Esta clasificación permanece planificada; no añadí una entidad Gold al registro Silver ni al Job.
