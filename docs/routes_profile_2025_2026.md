# Mi perfil inicial de routes: 2025 y 2026

**Fecha:** 6 de noviembre de 2026. Consulté Bronze y Silver agency mediante Genie en modo lectura. Recuperé resultados estructurados sin truncamiento. Conservo el [SQL ejecutado](../databricks/sql/silver/routes_profile_2025_2026.sql), no una descarga de las rutas.

| Comprobación | 2025-10-28 | 2026-09-29 |
| --- | ---: | ---: |
| Filas e IDs distintos | 676 | 1.045 |
| IDs nulos, vacíos o con espacios extremos | 0 | 0 |
| Copias de negocio adicionales | 0 | 0 |
| IDs con atributos conflictivos | 0 | 0 |
| Rutas sin agency Silver del mismo snapshot | 0 | 0 |
| route_long_name nulo | 1 | 0 |
| Filas con ambos nombres vacíos | 0 | 0 |
| route_type = 3, bus | 675 | 1.044 |
| route_type = 6, cable aéreo | 1 | 1 |
| Tipos o colores fuera del formato comprobado | 0 | 0 |
| Caracteres de control, versión/ruta incorrecta o timestamp nulo | 0 | 0 |

En los campos publicados no encontré cadenas vacías, valores compuestos por espacios ni espacios extremos en las consultas realizadas. El único null publicado fue un nombre largo de 2025; tiene nombre corto, por lo que no debo inventar uno. En los demás campos publicados los conteos de null fueron cero.

`route_desc` se publicó en 2025 con 676 valores y cinco descripciones distintas. No se publicó en 2026: sus 1.045 null históricos no representan errores de celdas del archivo. route_url y route_sort_order tampoco están publicados en estos snapshots. Los colores de 2026 están en minúsculas, lo cual es válido; no necesito cambiarlos para aprobar el formato hexadecimal.

Confirmé agency_v1 con siete filas y siete IDs únicos por snapshot en Silver. Esto respalda la dependencia de routes. En el momento de este perfil inicial contaba con dos ejecuciones exitosas del Job de agency. **Actualización al 10 de noviembre:** posteriormente ejecuté routes_v1 con el Job ampliado y comprobé las tablas Silver después de corregir el lector de nombres. Las métricas de este informe siguen correspondiendo al perfil inicial de lectura; no son métricas de una nueva ejecución del Job.

Un primer SQL de Genie falló al usar DISTINCT en una ventana. Recuperé y conservé la consulta corregida con agregación por ID; no cuento el intento fallido como prueba aprobada. Las consultas verifican las condiciones indicadas: no equivalen a una garantía de calidad perfecta ni demuestran la publicación de routes.

**Mi decisión:** conservo IDs y etiquetas por snapshot, convierto route_type a int y mantengo los demás campos observados como string. Definí las reglas y límites en el [contrato routes_v1](contracts/routes.md). No interpreto 676 → 1.045 como un incremento real de oferta ni como continuidad de identidades.
