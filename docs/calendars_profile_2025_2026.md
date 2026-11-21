# Mi perfil conjunto de calendarios: 2025 y 2026

**Fecha:** 10 de noviembre de 2026. Después de cerrar stops, consulté calendar y calendar_dates mediante Genie en modo lectura. Conservé las siete consultas definitivas en [un solo notebook](../databricks/notebooks/silver/12_profile_gtfs_calendars.ipynb), sin duplicar archivos SQL ni añadir pasos al Job. Recuperé sus resultados estructurados: 87 filas de metadata, patrones y agregados, todas sin truncamiento. No modifiqué tablas.

**Estado:** perfil inicial completado y contratos calendar_v1/calendar_dates_v1 implementados localmente después de revisar los hallazgos. Después ejecuté el Job de ambos calendarios en Databricks, comprobé físicamente las tablas Silver y consulté sus datos. El notebook conserva SQL individual ejecutado; no tiene aún una ejecución completa documentada como cuaderno. La evidencia fuente no equivale a una publicación Silver.

## Qué representa cada tabla

Calendar representa un conjunto de días de servicio mediante un patrón semanal y un intervalo inclusivo. Calendar_dates añade o retira servicio en fechas concretas. Es como tener un horario habitual y una hoja con excepciones por días específicos.

Service_id identifica ese conjunto de fechas, no una agencia. Que los dos catálogos contengan los números 1 a 7 no permite unir calendar con agency por ese número. La futura relación con viajes utilizará service_id y el mismo snapshot.

## Origen y encabezados

| Snapshot | SHA-256 | Calendar | Calendar_dates |
| --- | --- | ---: | ---: |
| 2025-10-28 | 07ba2ba9bb3b5bc1e38357355956757ce84fc68e6d05b74577bf017e189ab952 | 7 | 140 |
| 2026-09-29 | 08d14e0b3a5b9caa5451b722659871fd554e3273b94bdd770fdf81a26bf02097 | 7 | 133 |

La auditoría confirma los diez campos de calendar (service_id, siete días, start_date y end_date) y los tres de calendar_dates (service_id, date y exception_type) en ambos snapshots, sin campos ausentes entre ellos. El conjunto del encabezado no conserva necesariamente el orden físico del archivo.

Los 21 campos del esquema histórico incluyen 13 de negocio y ocho técnicos entre las dos tablas. Todos los campos de negocio son string en Bronze; bronze_loaded_at_utc es timestamp. Las cuatro combinaciones entidad/snapshot no tienen discrepancias de versión/ruta ni timestamps nulos en el control por hash.

## Controles comprobados

| Control | Calendar 2025 / 2026 | Calendar_dates 2025 / 2026 |
| --- | --- | --- |
| Filas / claves distintas | 7 / 7 y 7 / 7 | 140 / 140 y 133 / 133 |
| Copias idénticas adicionales | 0 / 0 | 0 / 0 |
| Claves con atributos distintos | 0 / 0 | 0 / 0 |
| Nulos, vacíos o solo espacios en negocio | 0 / 0 | 0 / 0 |
| Espacios extremos o caracteres de control | 0 / 0 | 0 / 0 |
| Fechas inválidas y códigos fuera de dominio | 0 / 0 | 0 / 0 |

Revisé 26 perfiles campo/snapshot, no 26 columnas distintas. Para claves compuestas usé JSON, no la concatenación con un separador que podría existir dentro de un ID. Las conversiones definitivas de fechas usan try_cast seguro e incluyen explícitamente null en el control. La comprobación inicial de Genie usaba otro parser y una condición de códigos que no cubría todos los null; no la conservo como consulta definitiva.

Contrasté también las 14 filas pequeñas de calendar con un cálculo independiente: siete IDs únicos por versión, indicadores 0/1, fechas válidas e intervalo ordenado. Esa comprobación del perfil es distinta de las pruebas automatizadas del procesador; sus resultados están en la [guía de ejecución](silver_execution.md#verificación-local-de-calendarios).

## Hallazgo principal: las fechas no siguen el año del ZIP

| Alcance temporal | Snapshot 2025-10-28 | Snapshot 2026-09-29 |
| --- | --- | --- |
| Intervalo de los siete patrones | 2000-01-01 a 2099-01-01 | 2026-01-01 a 2026-12-31 |
| Fechas distintas con excepciones | 20 | 19 |
| Primera / última excepción | 2023-01-01 / 2023-12-25 | 2026-01-01 / 2026-12-25 |
| Excepciones de año distinto al del snapshot | 140 | 0 |
| Referencias a IDs sin calendar | 0 | 0 |
| Fechas de excepción fuera del intervalo calendar | 0 | 0 |

Las 140 filas de 2025 son excepciones de 2023 aunque el ZIP se identifique como 2025. No encontré una causa confirmada. Un intervalo de 99 años tampoco demuestra que el servicio haya operado o vaya a operar durante todo ese período.

**Mi decisión:** conservar las fechas publicadas y registrar la limitación. No cambiaré 2023 por 2025 ni trasladaré festivos a otro año. Los errores de formato y un alcance temporal poco útil son problemas distintos. Para un análisis de 2025, esas excepciones no aportan ajustes festivos de 2025; no presentaré el resultado como un calendario de ese año completamente verificado.

## Patrones y excepciones

En 2025 hay siete servicios pero solo tres patrones semanales distintos: IDs 2 a 6 comparten lunes a viernes; el ID 1 marca domingo y el 7 lunes a sábado. No deduplico servicios por compartir patrón: otros viajes pueden referenciarlos por separado.

En 2026 hay siete patrones distintos. El ID 1 marca lunes a viernes y el 4 domingo. Es otro ejemplo de por qué mantengo versión y hash en la identidad.

| Tipo de excepción | 2025 | 2026 |
| --- | --- | --- |
| Añadir servicio (1) | 20 filas, service_id 1 | 19 filas, service_id 4 |
| Retirar servicio (2) | 120 filas, IDs 2 a 7 | 114 filas, IDs 1, 2, 3, 5, 6 y 7 |

Cada ID tiene una excepción para cada una de las 20 / 19 fechas. Esa regularidad no prueba por sí sola que la lista de días festivos esté completa o corresponda a una norma local verificada. Tampoco significa 140 o 133 viajes: son reglas de fechas.

## Qué propongo para Silver y qué dejo pendiente

El [contrato implementado](contracts/calendars.md) mantiene service_id como string, fechas como date y los indicadores/exception_type como int. No rellena ni reinterpreta el histórico. La clave de calendar sería versión + hash + service_id; la de calendar_dates añade date.

Antes de construir service_dates debo definir un horizonte explícito de análisis. No expandiré automáticamente 99 años ni limitaré la existencia de un ID a tener fechas activas dentro de una ventana arbitraria. Revisaré cómo distinguir patrón semanal y excepciones en la procedencia de cada día.

En Power BI separaré snapshot de fecha de servicio, mostraré la limitación de 2025 y evitaré comparar cantidades de días sobre horizontes diferentes. Cada futura tabla Gold seguirá completando la ficha de seis definiciones de negocio.

## Límites y siguiente paso

El perfil comprende las dos fuentes y sus relaciones internas; no consulta viajes ni horarios y no demuestra todavía esas referencias. No verifiqué un calendario oficial de festivos ni la operación real. Después del perfil ejecuté ambas tareas del Job en Workspace y comprobé las tablas y sus datos. El [cierre](silver_execution.md#cierre-de-la-ejecución-de-calendarios) distingue esa ejecución de las métricas fuente de este informe.

Tras revisar esta interpretación implementé el tipado con el pipeline compartido. La publicación de ambas fuentes ya quedó comprobada. El siguiente paso es service_dates, fijando primero su horizonte; las fechas y métricas de este informe siguen siendo evidencia del perfil inicial. Los archivos raw, tablas Bronze, carpetas temporales recuperadas y documentación Archify permanecen sin cambios.
