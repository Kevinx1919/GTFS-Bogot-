# Mi procedimiento manual de actualización del lakehouse y Power BI

**Actualización:** 20 de noviembre de 2026.
**Estado:** procedimiento documentado; falta comprobar una ejecución completa de principio a fin.
No ejecuté este recorrido como parte de la actualización de documentación.

## 1. Elijo la identidad y el alcance

Confirmo la versión y el SHA-256 del snapshot; no combino la versión de un archivo con el hash de otro.
Reviso el horizonte de service_dates, actualmente 2026, antes de preparar indicadores diarios.
El período del feed no reemplaza esa decisión de negocio.

## 2. Compruebo Bronze y Silver

Para una ingesta utilizo la configuración versionada del coordinador y los Jobs hijos.
El Job principal planifica Bronze, ingiere lo necesario y llama a Silver.
Espero un cierre Bronze completo y elegible, y reviso avisos y bloqueantes.
Después reviso el plan Silver: COMPLETE evita republicar, OUT_OF_SCOPE explica límites y BLOCKED exige resolver la causa.
Una lista vacía no es un fallo cuando el destino y su auditoría ya coinciden.

[Coordinador](pipeline_coordinator.md) · [Planificador Silver](silver_planner.md) · [Ejecución Silver](silver_execution.md).

## 3. Valido y publico Gold

| Orden | Notebook | Producto | Dependencia principal |
| --- | --- | --- | --- |
| 1 | Gold 20 | trip_coverage | trips, stop_times y frequencies Silver auditadas. |
| 2 | Gold 22 | route_service_day | Cobertura Gold y service_dates Silver del horizonte. |
| Independiente después de Silver | Gold 23 | route_stop | routes, trips, stop_times y stops Silver. |
| Independiente después de Silver | Gold 24 | trip_timing | trips, stop_times y frequencies Silver. |

En cada notebook ejecuto validate, reviso reconciliación, claves, categorías y ámbito.
Solo después ejecuto publish y compruebo SUCCEEDED, persisted=true y el cierre guardado.
No infiero éxito desde una vista previa ni desde la existencia de una tabla antigua.

[Cobertura](gold_precheck_2026_11_19.md) · [Programación diaria](gold_route_service_day_execution.md) · [Ruta–ubicación](gold_route_stop_execution.md) · [Extremos horarios](gold_trip_timing_execution.md).

## 4. Actualizo el modelo de Power BI

Abro el PBIP vigente y utilizo la conexión Databricks ya configurada.
Actualizo las tablas importadas sin exportar CSV ni descargar todas las visitas o puntos de trazado.
Compruebo conteos, identidad del snapshot, relaciones y categorías antes de leer los indicadores.
Mantengo las claves técnicas necesarias para relacionar y las oculto de la presentación.
No elimino columnas de Silver para reducir el modelo de consumo.

Los .dax documentan medidas; no se importan automáticamente por estar en una carpeta.
El PBIP contiene las definiciones ejecutables; el PBIX anterior no se actualiza por editar esos archivos.
Si el proyecto cambió externamente, lo vuelvo a abrir sin sobrescribirlo con una sesión anterior.

## 5. Compruebo el recorrido del reporte

Pruebo Panorama, Programación, Red publicada y Revisión.
Compruebo el botón activo, el menú sin duplicados y el cambio de página con Ctrl + clic en Desktop.
Reviso componente y ruta sincronizados, fechas A/B y combinaciones sin datos.
Las tarjetas ilustradas filtran Panorama localmente; no espero que sincronicen otras páginas.
Contrasto al menos un caso con su consulta o resumen Gold, conservando denominadores y límites.
Registro tiempos medidos y errores; no asigno una duración estimada como si fuera observada.

## 6. Registro el cierre

Guardo la identidad, las ejecuciones, los conteos y el resultado de los casos revisados sin credenciales.
Actualizo el [estado del proyecto](project_status.md), el [cierre](power_bi_cierre_v1.md) y las vistas afectadas de Archify.
Este procedimiento no activa horarios productivos, publica en Service ni añade automatización Gold/Power BI al coordinador.
