# Mis notebooks Gold

Comienzo por la cobertura de viajes antes de construir indicadores de oferta planificada.
El notebook 19 conserva una consulta de solo lectura verificada mediante Genie.
No publica Gold ni modifica el Job principal.
La ficha de negocio y el orden de implementación están en docs/gold_plan.md y docs/contracts/trip_coverage.md.
Los futuros publicadores mantendrán separados validación, escritura e identidad del snapshot.

Notebook 20 ejecuta gtfs_gold/trip_coverage.py para validar o publicar la primera entidad Gold.
El modo inicial validate no escribe tablas ni auditorías Gold.
Publish reemplaza solamente el snapshot seleccionado y registra su auditoría Gold.
La cobertura 2026 ya está publicada y consumida en Power BI; no añadí esa tarea al coordinador.


Notebook 22 ejecuta gtfs_gold/route_service_day.py para preparar programación declarada por ruta y fecha.
La primera publicación 2026 ya terminó SUCCEEDED, con 305.165 claves únicas y reconciled=true.
Validate sigue siendo el modo inicial para las próximas ejecuciones.
Reutiliza la cobertura existente y fechas activas, sin volver a agregar stop_times.
La guía docs/gold_route_service_day_execution.md conserva configuración y comprobaciones.


Notebook 23 valida o publica el puente ruta–ubicación mediante gtfs_gold/route_stop.py.
La publicación en Workspace está pendiente. No requiere ejecutar otra vez el notebook 22.
La guía docs/gold_route_stop_execution.md conserva campos, diagnósticos y filtros del mapa.


Notebook 24 valida o publica extremos horarios por viaje mediante gtfs_gold/trip_timing.py.
Conserva viajes sin visitas y separa las plantillas por frecuencia.
Su publicación en Workspace está pendiente; la guía es docs/gold_trip_timing_execution.md.
