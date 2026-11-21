# Perfilado de agency — snapshot 2025-10-28

**Fecha de revisión:** 30 de octubre de 2026.
**Estado:** revisé agency con consultas SQL de lectura mediante Databricks Genie y recuperé sus resultados estructurados. Todavía no he ejecutado el notebook 08, modificado Bronze ni creado Silver.

## Alcance y evidencia

- Tabla: workspace.gtfs_bogota.bronze_gtfs_agency.
- source_feed_version: 2025-10-28.
- source_sha256: 07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952.
- Pedí una muestra limitada a 20 y recuperé las 7 filas del snapshot, sin truncamiento.
- Consulté audit_gtfs_source_schema_observations y encontré una observación de agency.txt para la misma versión y hash.
- Recuperé los resultados estructurados de las dos consultas de perfilado con estado SUCCEEDED y sin truncamiento.
- Con ayuda de Codex contrasté las métricas SQL con un cálculo determinista independiente sobre las siete filas completas: coincidieron.
- Seleccioné columnas explícitas y dejé la procedencia técnica fuera de la comparación de duplicados.

**Para repasar el proceso, mi punto de entrada es el [notebook SQL guiado](../databricks/notebooks/silver/08_agency_sql_guiado.ipynb).** Explica una pregunta por bloque e incluye las consultas largas originales al final. Las [consultas SQL ejecutadas](../databricks/sql/silver/agency_profile_2025.sql) se conservan también como evidencia histórica, sin cambios. No guardo en Git las filas fuente, respuestas completas de ejecución, credenciales ni enlaces privados del workspace.

## Presencia de columnas

La auditoría de encabezados registra seis columnas publicadas: agency_id, agency_lang, agency_name, agency_phone, agency_timezone, agency_url.

agency_fare_url existe como string en la tabla Delta histórica, pero no estaba en el encabezado de 2025. Sus siete null representan esta ausencia de columna; no son siete celdas que el proveedor hubiera publicado vacías. agency_email tampoco aparece en el encabezado ni en el esquema Bronze inspeccionado.

Para esta comprobación leí la observación de esquema que dejó Bronze. No hice una nueva lectura del archivo Staging ni del ZIP Raw desde el conector.

## Métricas por campo

| Campo | Publicado | Tipo actual / propuesto | Nulos | Vacíos | Solo espacios | No vacíos | Distintos no vacíos | Espacios extremos |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agency_id | Sí | string / string | 0 | 0 | 0 | 7 | 7 | 0 |
| agency_name | Sí | string / string | 0 | 0 | 0 | 7 | 7 | 0 |
| agency_url | Sí | string / string | 0 | 0 | 0 | 7 | 1 | 0 |
| agency_timezone | Sí | string / string | 0 | 0 | 0 | 7 | 1 | 0 |
| agency_lang | Sí | string / string | 0 | 0 | 0 | 7 | 1 | 0 |
| agency_phone | Sí | string / string | 0 | 0 | 0 | 7 | 1 | 0 |
| agency_fare_url | No | string / string | 7 | 0 | 0 | 0 | 0 | 0 |

Para las columnas publicadas, nulos, vacíos, solo espacios y no vacíos explican las siete filas. La variedad y los espacios en extremos son diagnósticos adicionales, no categorías para sumar a ese total.

Encontré una sola URL, zona horaria, idioma y teléfono para los siete IDs. No usé esos atributos compartidos como motivo para consolidar agencias. Esto es como si dos oficinas compartieran recepción: el teléfono puede ser el mismo y cada oficina seguir teniendo su propia identificación. Los nombres también son siete valores distintos, pero eso no los convierte en una clave histórica estable.

## Identidad y duplicados

| Métrica | Resultado |
| --- | ---: |
| Filas del snapshot | 7 |
| IDs distintos no vacíos | 7 |
| IDs nulos, vacíos o compuestos por espacios | 0 |
| Copias idénticas adicionales de negocio | 0 |
| IDs repetidos | 0 |
| IDs con atributos de negocio contradictorios | 0 |
| Colisiones potenciales al quitar espacios extremos del ID | 0 |

Con estos resultados propongo la clave candidata (source_feed_version, source_sha256, agency_id) para este snapshot. No demuestran persistencia de IDs entre años ni una identidad jurídica de empresas operadoras.

## Decisiones propuestas para Silver

1. Mantendré como string los seis campos publicados. ID y teléfono son texto por su significado, aunque parte de su contenido sean dígitos.
2. No veo una razón para eliminar, consolidar o rellenar registros en los controles realizados para este snapshot.
3. Si decido incluir agency_fare_url en el esquema curado, lo dejaré nullable y conservaré evidencia de que la columna no fue publicada en 2025. No copiaré una URL desde otra versión.
4. Conservaré el nombre publicado, incluidas sus mayúsculas; no lo normalizaré automáticamente.
5. Revisaré agency de 2026 y después definiré obligatoriedad, formatos y reglas de publicación antes de escribir la transformación.

## Qué sigue pendiente

- Terminar de revisar y entender este resultado antes de avanzar a 2026 o a otra entidad.
- Perfilado por columna y duplicados de 2026; conocer su conteo no sustituye ese análisis.
- Validaciones específicas de URL, idioma, zona horaria y relaciones desde routes.
- Ejecución del notebook 08 y de sus pruebas Spark; este informe prueba las consultas SQL, no la implementación PySpark.
- Contrato final, auditoría de publicación, cuarentena e idempotencia Silver.

No fijé una versión Delta de la tabla durante estas lecturas. El informe identifica versión y hash de origen y registra el resultado observado; no garantiza reproducir el estado físico si alguien modifica Bronze indebidamente.
