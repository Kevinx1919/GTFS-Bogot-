# Mi contrato Silver de agency — versión 1

**Fecha:** 6 de noviembre de 2026.
**Estado:** notebook 09 ejecutado y revisado para ambos snapshots en Databricks. Publicación, cuarentena, auditoría y Job manual preparados y comprobados localmente con Delta real; falta ejecutarlos en el workspace. No hay una publicación Silver allí comprobada.

## Qué representa una fila

Conservaré una agencia o marca tal como fue publicada dentro de un snapshot. Mi clave será `(source_feed_version, source_sha256, agency_id)`. Una fecha de publicación no es una fecha de servicio.

Ya revisé siete filas y siete IDs distintos con contenido en cada snapshot, con SQL mediante Genie y con las salidas de los bloques 2, 3 y 4 del perfilador PySpark ejecutado en Databricks. No encontré duplicados ni ausencias en los campos publicados. No exigiré siete filas a todas las versiones futuras.

Los códigos no garantizan continuidad entre años. Conservaré los nombres y URLs de cada versión, sin homologar categorías ni reemplazar atributos históricos. La URL y el nombre no serán claves. Relacionaré rutas y agencias únicamente dentro del mismo snapshot.

## Qué tipos y reglas aplicaré

Todos los campos de negocio de esta primera versión serán `string`. Definir el tipo no significa rellenar un dato.

| Campo | Presencia en mi contrato v1 | Regla de contenido | Tratamiento |
| --- | --- | --- | --- |
| agency_id | Obligatorio en las versiones actuales con varias agencias | Texto con contenido; único dentro del snapshot. Conservo ceros iniciales y mayúsculas. No exijo que sea numérico. | Ausencia o conflicto: rechazo y bloqueo de publicación. Espacios extremos: revisión y bloqueo hasta resolver, sin recortar el ID. |
| agency_name | Obligatorio | Texto con contenido; conservo el nombre publicado. No lo uso como clave ni cambio su capitalización. | Ausencia: rechazo y bloqueo. Espacios extremos: advertencia, conservando el original. |
| agency_url | Obligatorio | URL absoluta con esquema HTTP o HTTPS y host; sin espacios ni caracteres de control. | Ausencia o formato inválido: rechazo y bloqueo. No compruebo disponibilidad web ni fuerzo HTTPS. |
| agency_timezone | Obligatorio | Nombre reconocido de zona IANA. Todas las agencias del snapshot deben compartir zona. | Ausencia, zona no reconocida o incoherencia: bloqueo. No sustituyo una zona inválida por America/Bogota. |
| agency_lang | Opcional | Si existe contenido, comprobar etiqueta de idioma BCP 47 con una referencia o implementación adecuada. Una expresión regular simple no demuestra conformidad completa. | Ausencia permitida. Valor no validado o inválido: revisión y bloqueo en v1; conservo el valor y el motivo. |
| agency_phone | Opcional | Texto de contacto. Conservo signos, ceros, espacios y formato publicado; no impongo E.164, cantidad fija de dígitos ni solo números. | Ausencia permitida. Esta versión no demuestra que el número sea marcable o esté activo. |
| agency_fare_url | Opcional | Cuando tenga contenido, aplicar el mismo control de estructura que a agency_url. | Ausencia permitida. Formato inválido: rechazo y bloqueo en v1. |
| agency_email | Opcional | Si se publica, comprobar estructura básica de dirección y ausencia de espacios o controles; no verificar existencia del buzón. | Ausencia permitida. Una columna nueva requiere revisar el encabezado y aprobar su incorporación antes de publicar. |

Me baso en la [referencia oficial de agency.txt](https://gtfs.org/documentation/schedule/reference/#agencytxt) y sus [tipos de campo](https://gtfs.org/documentation/schedule/reference/#field-types). El control de URL será estructural; no lo presentaré como una comprobación completa de cada requisito de codificación de URLs. El control básico de correo tampoco será un validador integral del estándar de correo.

La política de bloquear valores opcionales presentes pero inválidos es una decisión conservadora de mi primera implementación, no una exigencia universal de GTFS. Los teléfonos se conservan sin validación completa de formato.

En GTFS, agency_id es condicional: con varias agencias se requiere. Mi v1 exige IDs fuente para sus snapshots actuales. Si llega una fuente válida con una sola agencia sin ID, detendré esta implementación para ampliar el contrato; no inventaré un identificador ni declararé inválido todo ese supuesto del estándar.

Para zonas e idiomas fijé langcodes 3.5.1 y tzdata 2026.6 en databricks/requirements-silver.txt. El validador bloquea dependencias ausentes o con versiones distintas; las versiones se devuelven en el resultado. Si el entorno no permite validar un valor, marcaré revisión pendiente y no lo contaré como aprobado. America/Bogota y es son valores observados, no sustitutos automáticos ni los únicos valores válidos del estándar.

## Cómo distinguiré ausencias y errores

- Si una columna opcional no estaba en el encabezado, su salida podrá ser null tipado. Conservaré la lista de columnas publicadas para explicar su ausencia.
- Si una columna opcional publicada contiene null, cadena vacía o solo espacios, admitiré la ausencia y la representaré como null en Silver. Registraré sus conteos antes de transformar; no reconstruiré un vacío que el lector CSV ya hubiera convertido a null.
- Si una columna requerida no existe, bloquearé el snapshot antes de transformar. Si existe pero una fila no tiene contenido, registraré esa fila rechazada.
- Un valor con contenido que falla su formato no se convertirá silenciosamente en una ausencia permitida. Conservaré el original y el código de error.
- No aplicaré trim a valores con contenido, reemplazos de nombres o cambios de identificadores en este incremento.
- Los caracteres de tabulación, retorno de carro o salto de línea dentro de valores publicados se registrarán como errores de contenido. No los borraré silenciosamente.
- Una columna publicada no contemplada o una retirada de columna requerida detendrá la publicación hasta revisar el contrato. Los campos opcionales conocidos podrán faltar.

En 2025, agency_fare_url no estaba publicado: sus siete null históricos no son siete celdas fuente vacías. En 2026 está publicado con siete valores con contenido. agency_email no aparece en ninguno de los encabezados revisados; su fila en el perfil no significa que se haya descargado una columna de correos.

Es como revisar un formulario: no tener la casilla de correo es distinto de tenerla vacía, y ambas situaciones son distintas de escribir una dirección incorrecta.

## Duplicados y errores antes de publicar

Compararé las columnas de negocio publicadas, excluyendo timestamps y procedencia técnica. Para agency, Spark filtra el hash y selecciona columnas; la lectura está limitada a 1.000 filas. Los validadores de URL e idioma y la lista IANA se aplican en Python, sin UDF, y el adaptador devuelve DataFrames con esquemas explícitos. Esta excepción acotada no se aplicará a entidades grandes como trips o stop_times.

1. Una fila sin errores será candidata a publicación.
2. Si hay copias idénticas y válidas dentro del mismo snapshot, conservaré una representación y auditaré las copias consolidadas. No deduplicaré entre snapshots. La procedencia temporal de esa representación conservará el menor bronze_loaded_at_utc entre las copias.
3. Si el mismo ID tiene atributos de negocio diferentes, rechazaré todas sus filas y bloquearé la publicación del snapshot. No elegiré una con dropDuplicates.
4. Una fila rechazada contará una sola vez, aunque tenga varios motivos. Si pertenece a un conflicto, no se contabilizará además como una copia consolidada.
5. La reconciliación será: entrada = representaciones válidas + filas rechazadas + copias idénticas válidas consolidadas.
6. En v1, cualquier error bloqueante impedirá publicar agency de ese snapshot. Las representaciones válidas se podrán revisar en memoria, pero no publicar como conjunto parcial.

La futura cuarentena conservará snapshot, contenido fuente, clave cuando exista, motivos, versión de reglas y ejecución. Una huella del contenido no identifica por sí sola una línea física entre copias idénticas. La cuarentena y la auditoría también necesitarán pruebas de reintento; todavía no están implementadas.

## Esquema técnico y protección del histórico

Además de los ocho campos de negocio conocidos, la salida conservará:

| Campo técnico | Tipo propuesto | Uso |
| --- | --- | --- |
| source_feed_version | string | Versión publicada, con formato ISO validado; parte de la clave. |
| source_sha256 | string | Hash de origen de 64 caracteres hexadecimales; parte de la clave. |
| source_file_path | string | Archivo fuente del snapshot seleccionado. |
| bronze_loaded_at_utc | timestamp | Procedencia de la carga Bronze, conservada sin sustituirla por la fecha Silver. |
| source_columns | array<string> | Encabezado publicado, para distinguir ausencia de columna y celda sin valor. |
| silver_run_id | string | Identifica la ejecución, no la agencia. |
| silver_loaded_at_utc | timestamp | Marca de procesamiento con sesión UTC. |
| silver_rule_version | string | Versión de este contrato y sus reglas. |

Antes de transformar verificaré tabla, columnas técnicas, selección no vacía y coherencia de hash, versión y ruta. Raw y Bronze seguirán siendo la evidencia original.

La tabla propuesta es `silver_gtfs_agency`, en catálogo y schema parametrizados. La futura escritura reconstruirá solo el snapshot seleccionado después de validarlo. No usaré append indiscriminado ni reemplazaré toda la historia. Si la salida queda vacía, bloquearé la escritura.

Al repetir la misma entrada y reglas, las claves y valores de negocio deben coincidir sin duplicarse. El ID de ejecución y su timestamp pueden cambiar. Comprobaré además que el contenido de cualquier otro snapshot permanezca intacto. Esto es un requisito para implementar y probar, no una garantía ya verificada sobre Silver.

## Evidencia y condiciones antes de escribir

| Revisión | Estado |
| --- | --- |
| Encabezados, tipos Bronze, completitud e IDs de 2025 y 2026 | Revisados mediante salidas de ejecución y consultas SQL. |
| Duplicados y colisiones de ID de ambos snapshots | Revisados; no se encontraron casos en estos controles. |
| Identidad por snapshot y preservación de nombres | Decisión acordada. |
| Estructura de URL, zona IANA y etiqueta de idioma | Núcleo Python ejecutado sobre las 14 filas completas de ambos snapshots: sin rechazos. El notebook 09 y su adaptador Spark también se ejecutaron y revisaron para ambos snapshots en Databricks. |
| Formato integral de teléfonos, disponibilidad de webs y buzones | Fuera del control de esta v1; no afirmaré que están verificados. |
| Cuarentena, auditoría, escritura Delta y reejecución | Implementadas y probadas con fixtures Delta en Linux; publicación y Job en el workspace pendientes. |

Añadí pruebas con datos sintéticos para: ID con ceros, campos requeridos sin contenido, opcionales ausentes o vacíos, URL relativa, HTTP permitido, zona desconocida o inconsistente, idioma inválido o no verificable, espacios en IDs, copias idénticas y conflicto de clave. Las pruebas del núcleo comprueban también que ID 2 de 2025 y de 2026 conserven sus nombres distintos; todavía falta verificar la coexistencia en tablas Delta.

En Databricks verificaré selección y formatos antes de escribir, bloqueo sin modificar la tabla ante errores, publicación de un snapshot válido y segunda ejecución sin duplicación ni cambios en la otra versión. Las pruebas locales actuales sí incluyen estos comportamientos en Delta real; no demuestran todavía la ejecución ni los permisos en Unity Catalog del workspace.

El [informe de validación](../agency_validation_2025_2026.md) distingue pruebas locales, datos reales consultados y ejecución Spark pendiente. El notebook 09 usa los mismos módulos del núcleo y ya fue ejecutado para ambos snapshots. Solo lee y muestra candidatos y rechazos en memoria. El [notebook 10 y el Job](../silver_execution.md) reutilizan las reglas e incorporan la publicación por snapshot; todavía no fueron ejecutados en el workspace. No necesito repetir Raw o Bronze para esta comprobación.
