# Plan de trabajo de Silver — Bogotá GTFS Mobility Lakehouse

## 1. Estado y propósito

**Estado de este documento:** este es mi plan para construir Silver por etapas. La carpeta Silver contiene una guía SQL de agency como punto de entrada y un perfilador PySpark como alternativa. La guía nueva y el perfilador siguen pendientes de ejecución real; el perfilado SQL histórico de 2025 sí fue comprobado. Aún no hay transformaciones ni tablas Silver. Los tipos y reglas indicados son propuestas que se confirmarán con el perfilado de cada entidad.

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

Los nombres silver_gtfs_* son propuestos y aún no existen como resultado de este plan. Los archivos opcionales se procesarán solo si están publicados; su ausencia se documentará sin inventar registros.

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
| Después, según pregunta | feed_info y tarifas | feed_info: una fila por snapshot; fare_attributes: fare_id; fare_rules: combinación completa de campos de regla publicados | Metadata y IDs: string; fechas: date; importes: decimal con precisión/escala acordadas; códigos: int | Metadata y reglas tarifarias; no se fabrican filas cuando falta un opcional. No forman parte del primer incremento. |

Ya comprobé siete filas de agency en ambos snapshots: perfilaré sus IDs; no asumiré que siete filas implican siete agencias distintas. Si aparece un caso válido de agencia única sin ID, definiré una clave técnica explícita conservando el ID fuente nulo. No se resolverán agencias múltiples mediante nombres parecidos.

La referencia de servicios usa los IDs declarados por los calendarios disponibles. service_dates deriva los días activos; no se exigirá que un servicio tenga días dentro de un horizonte de consulta arbitrario para afirmar que su ID existe.

### Primer incremento: agencias y rutas

1. Perfilar agency de 2025; revisar su ficha; repetir para 2026.
2. Comparar completitud y encabezados: agency_fare_url apareció en 2026, pero aún no se ha medido si tiene contenido útil.
3. Acordar la clave y las reglas de agency. Probar y verificar su transformación antes de pasar a routes.
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

**Propuesta, pendiente de implementación:** reconstruir de forma determinista una entidad para S y reemplazar solo su ámbito después de validar, manteniendo las demás versiones. Antes de escribir comprobaré la selección y el comportamiento ante salida vacía. No se hará overwrite de toda la historia ni append indiscriminado en cada reejecución.

Cada resultado conservará source_feed_version, source_sha256 y source_file_path, y se asociará a silver_run_id, timestamp UTC, versión de reglas/código y manifiesto Raw. Cuando sea necesario fijaré la versión Delta leída de Bronze. Los campos técnicos de ejecución pueden cambiar entre reintentos; las claves y valores de negocio no deberían cambiar con la misma entrada y reglas.

Introduciré auditoría de ejecución, resultados de reglas y cuarentena junto al primer incremento. La metadata del snapshot podrá registrarse en una tabla de control o entidad auxiliar; no se creará una fila artificial de agencia o ruta para representar ese control. No se publicará un conjunto incompleto como si todas las entidades estuvieran validadas. Una escritura atómica de una tabla no garantiza una transacción de todas las tablas; evitaré ejecuciones concurrentes del mismo snapshot en la primera versión.

Catálogo, schema, Volumes, versión y hash serán parámetros. workspace.gtfs_bogota y los Volumes actuales serán defaults explicados del entorno de aprendizaje, no rutas personales fijas en funciones reutilizables. UTC se usa para procesamiento; la fecha de servicio y la zona de la agencia se manejan de forma explícita.

Antes del primer notebook de transformaciones confirmaré el runtime y el cómputo de Databricks. Puedo usar conversiones tolerantes como [try_cast](https://docs.databricks.com/aws/en/sql/language-manual/functions/try_cast), pero contaré sus fallos: devolver null no convierte el dato en válido.

## 7. Código, notebooks y pruebas

Carpeta creada: databricks/notebooks/silver/. Mantendré los notebooks anteriores en sus rutas para no afectar el Job Bronze. La carpeta organiza código, no almacena las tablas Delta ni necesita un Volume nuevo.

**Estado de notebooks:** empezar por [08_agency_sql_guiado.ipynb](../databricks/notebooks/silver/08_agency_sql_guiado.ipynb), que explica una pregunta por bloque y conserva el SQL completo en apéndices opcionales. 08_profile_gtfs_reference_entities.ipynb es la alternativa PySpark para automatizar después esas preguntas. No son dos pasos obligatorios. Routes se revisará después de agency; 09_silver_gtfs_reference_entities.ipynb sigue siendo una propuesta para la transformación posterior. La separación permite revisar resultados antes de introducir escrituras. Los bloques se documentarán en el runbook antes o al implementarlos.

Seguiré usando Python/PySpark dentro de notebooks para ejecutar y observar resultados. Las reglas se escribirán como funciones pequeñas; cuando necesite compartirlas y probarlas fuera del notebook, se extraerán a módulos versionados bajo databricks/. Las pruebas y fixtures pequeños se mantendrán en tests/. No se introduce ahora una nueva dependencia ni un framework de ejecución.

Casos mínimos por entidad: datos válidos, ID con ceros iniciales, null, vacío, espacios, columna opcional ausente, conversión inválida, duplicado idéntico, conflicto de clave, referencia rota y segunda ejecución sin duplicación. Se añadirán casos específicos: fechas inválidas y excepciones; horas mayores a 24; secuencias con saltos; parada repetida; frecuencias y opcionales ausentes.

Las pruebas por implementar tendrán dos niveles: fixtures locales para reglas deterministas y comprobación en Databricks para lectura/escritura Delta, métricas y reintento. Las 16 pruebas que existen hoy validan las correcciones Raw/Bronze; no son pruebas de Silver. No usaré llamadas reales a las fuentes como única prueba automática.

## 8. Rendimiento y criterio de terminado

Con stop_times filtraré S y columnas al principio, agruparé métricas para reducir lecturas y evitaré collect de millones de filas, ordenamientos globales y UDF de Python cuando existan funciones Spark. Los joins y ventanas pueden redistribuir datos; se medirán. Usaré cache solo si se reutiliza el resultado y su costo lo justifica, liberándolo al terminar.

No expandiré todo stop_times por todas las fechas al comenzar. Elegiré particionado u otras optimizaciones después de medir tamaño, archivos, duración y lecturas; el número de filas por sí solo no decide el diseño físico.

Una entidad estará terminada cuando su grano y contrato estén documentados; las métricas expliquen la entrada; las filas publicadas cumplan claves, tipos y relaciones; los rechazos preserven evidencia; las pruebas pasen; la reejecución mantenga resultados de negocio; otras versiones sigan intactas; y yo pueda explicar qué obtuve y por qué lo considero válido. Solo entonces pasaré a la siguiente.

**Estado actual del primer paso:** agency 2025 ya fue perfilada mediante SQL y sus resultados están en el [informe](agency_profile_2025.md). Quiero revisar con calma lo encontrado antes de continuar con 2026. El notebook 08 está creado y puede usarse para contrastar los mismos controles en PySpark; todavía no lo he ejecutado en Databricks.

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

**Validación local:** pasaron seis pruebas nuevas de parámetros y encabezados y las 16 existentes de Raw/Bronze. Tres pruebas adicionales con fixtures de Spark quedaron omitidas porque no están instalados PySpark y Java como entorno de pruebas local completo. Las métricas del notebook y su compatibilidad con el cómputo real siguen pendientes de ejecutar en Databricks. El perfilado SQL de agency 2025 sí está comprobado; la revisión de nulos y duplicados de 2026 sigue pendiente.

El primer [informe real de agency 2025](agency_profile_2025.md) documenta resultados agregados y decisiones propuestas; no se ha aprobado ni escrito aún la transformación Silver.
