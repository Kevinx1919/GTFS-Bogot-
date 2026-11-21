# Mi contrato Silver stops_v1

**Fecha:** 10 de noviembre de 2026. Cerré estas reglas después de revisar el [perfil real](../stops_profile_2025_2026.md). Su implementación está en stops_spark.py y reutiliza preparación, reconciliación y publicación. Ya ejecuté el Job en Databricks y comprobé la tabla Silver y sus datos mediante una consulta breve. La [guía Silver](../silver_execution.md#cierre-de-la-ejecución-de-stops) conserva el alcance de esa comprobación y lo separa de las pruebas locales y del perfil fuente.

## Grano, origen e identidad

Una fila representa una ubicación publicada dentro de `(source_feed_version, source_sha256)`. La clave validada es esa pareja más stop_id. No es una homologación entre años ni una restricción SQL PRIMARY KEY declarada. La relación de padre apunta a otra ubicación del mismo snapshot; stops no necesita una tabla Silver routes o agency.

Leo la versión Delta fijada de Bronze y el encabezado real del TXT en Staging. Selecciono por hash para detectar una versión o ruta incoherente en vez de ocultarla con otro filtro. Compruebo versión, hash, ruta y timestamp de procedencia. Los campos publicados deben conservar string en Bronze; el timestamp técnico debe ser timestamp y la sesión debe usar UTC.

## Esquema de negocio

| Campo | Tipo Silver | Regla |
| --- | --- | --- |
| stop_id | string | Requerido; no vacío ni con espacios extremos. No lo modifico. |
| stop_code | string nullable | Opcional; permito repeticiones y conservo ceros iniciales. |
| stop_name | string nullable | Requerido para tipos efectivos 0, 1 y 2. Quito solo espacios Unicode de los bordes; no cambio caja, acentos ni espacios interiores. |
| stop_lat | double nullable | Requerido para tipos efectivos 0, 1 y 2; formato numérico, finitud y rango [-90, 90]. |
| stop_lon | double nullable | Requerido para tipos efectivos 0, 1 y 2; formato numérico, finitud y rango [-180, 180]. |
| location_type | int nullable | Si existe con contenido, entero no negativo y dominio 0–4. Si falta, uso 0 solo para validar la semántica GTFS; conservo null en la columna. |
| parent_station | string nullable | Referencia de ubicación del mismo snapshot, condicionada por el tipo. No limpio el ID. |
| zone_id | string nullable | Opcional, zona tarifaria; no exijo unicidad ni invento valores. Rechazo espacios extremos de este ID. |
| wheelchair_boarding | int nullable | Opcional; dominio 0–2. No copio otro snapshot ni resuelvo herencia de accesibilidad en esta versión. |

Los enteros admiten ceros iniciales en la representación fuente, como routes_v1; rechazo decimales, signos negativos y desbordamientos. Las coordenadas admiten decimal y notación científica finita; rechazo texto, NaN, infinito y valores fuera de rango. Un par (0, 0) produce advertencia, no una regla geográfica universal de rechazo. No verifico pertenencia al polígono oficial de Bogotá en esta versión.

El encabezado exige stop_id. La obligatoriedad de nombre y coordenadas se comprueba por fila, incluso cuando una de esas columnas esté ausente. Un campo fuente nuevo o repetido detiene el proceso para revisar el contrato; esta versión solo admite los nueve campos de negocio descritos. Ausencias y valores compuestos por espacios de opcionales quedan null. source_columns conserva los nombres publicados, también cuando todos sus valores sean null.

## Jerarquía de padres

Aplico la [referencia GTFS stops.txt](https://gtfs.org/documentation/schedule/reference/#stopstxt): tipo efectivo 0 permite una estación padre; tipo 1 no lleva padre; tipos 2 y 3 requieren estación padre; tipo 4 requiere una plataforma de tipo efectivo 0. Compruebo existencia, autorreferencias, conflictos del padre y tipo esperado.

Agrupo el mapa de padres por ID antes de unir. Copias idénticas no multiplican hijos; dos variantes del mismo padre generan rechazo de sus variantes y de los hijos que lo referencian. Para encontrar padres exijo procedencia válida del snapshot. Los errores de cualquier fila impiden publicar el snapshot completo; no publico hijos aislados de un padre rechazado.

Una estación sin hijos referenciados genera `STATION_WITHOUT_CHILDREN`, como diagnóstico para revisar, sin inferir que no exista físicamente. Las doce estaciones señaladas en el perfil de 2026 no bloquean por esa sola condición. No fabriqué vínculos para completarlas.

## Duplicados, normalización y advertencias

La huella de negocio usa los valores fuente publicados **antes de normalizar nombres**, excluyendo metadata técnica. Consolido copias válidas idénticas y elijo la de timestamp Bronze más antiguo, con desempate estable. Si un ID tiene atributos fuente distintos, rechazo sus variantes aunque sus nombres fueran iguales después de quitar espacios. Así no oculto un conflicto mediante la limpieza.

Rechazo caracteres de control Unicode en campos publicados. Los espacios extremos de stop_id, parent_station y zone_id son errores; en los demás campos generan advertencia. Los nombres se limpian con una expresión Unicode explícita. Los campos numéricos además deben cumplir su formato; no admito espacios extremos como parte de un número. Stop_code con espacios se advierte y conserva como texto.

La salida contiene nueve campos de negocio, los cuatro de procedencia Bronze, source_columns y silver_rule_version; el escritor añade silver_run_id y silver_loaded_at_utc: **17 columnas físicas**. La fuente original de una etiqueta normalizada se recupera en Bronze mediante la clave completa.

El resumen conserva las métricas comunes y añade `name_trimmed_rows` y `stations_without_children`, contados sobre candidatos únicos válidos. Son diagnósticos del resultado de ejecución, no columnas nuevas de la auditoría existente. warning_rows cuenta filas fuente con alguna advertencia; no es la suma de motivos. Un nombre con espacios en una estación sin hijos puede aportar dos motivos en una sola fila.

## Publicación, rechazo y consumo

Uso silver_gtfs_stops, quarantine_gtfs_stops y audit_gtfs_silver_runs. Reutilizo el escritor: validate no escribe; publish registra cuarentena/auditoría y sustituye solo versión + hash cuando no hay rechazos, verificando la salida y el histórico configurado. No hay evolución automática del esquema ni transacción única entre las tres tablas. Un fallo posterior a escribir conserva la marca silver_committed para revisión.

El registro no declara dependencia de datos para stops. La plantilla manual la ejecuta después de routes como decisión operativa de serialización: mantengo una sola tarea escritora a la vez sobre la auditoría común. No es una relación stops → routes.

En Gold conservaré la separación de estaciones y plataformas, el ámbito del snapshot y las ausencias de accesibilidad o zona. Cada futura tabla Gold completará su [definición de negocio](../silver_design.md#definición-de-negocio-obligatoria-para-cada-futura-tabla-gold) antes de implementar indicadores.
