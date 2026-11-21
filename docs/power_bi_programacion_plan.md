# Mi segundo panel: Programación

> **Estado vigente — 20 de noviembre de 2026:** las cuatro Gold de 2026 están publicadas e importadas y los cuatro paneles están implementados. La navegación nativa funciona; la revisión integral y la actualización completa siguen pendientes. [Estado actual](project_status.md).

## Registro de diseño e implementación

Conservo a continuación las decisiones y comprobaciones de cada etapa. Los pendientes de esas fechas describen su momento; el estado vigente anterior los sustituye.

**Estado:** primera implementación guardada en PBIP y comprobada con datos reales; revisión en Desktop pendiente.

## Historia de negocio

Como persona que revisa programación, necesito conocer los días y las horas que publica una selección de rutas.
Quiero contrastar dos fechas y recuperar ejemplos concretos para revisar una diferencia.

**Pregunta principal:** ¿cómo se reparte la programación por día y por hora, y qué horas publican los viajes elegibles?

Panorama me orienta sobre cantidades, componentes y red del catálogo.
Programación profundiza en calendario, primeras salidas, extremos y ventanas de frecuencia.
No lo utilizaré para certificar operación continua, puntualidad o tiempos de espera.

## Qué construiré

| Bloque | Pregunta | Fuente y definición |
| --- | --- | --- |
| Indicadores horarios | ¿Qué viajes sostienen los extremos mostrados? | Viajes activos elegibles, primera salida y última llegada de sus extremos. |
| Calendario mensual | ¿Qué días muestran programación y con qué cantidad? | route_service_day; viajes sin frecuencias o plantillas, sin mezclar unidades. |
| Perfil por hora | ¿En qué horas se concentran las primeras salidas declaradas? | Un conteo por viaje elegible, usando su primera salida; comparo A y B. |
| Muestra de viajes | ¿Qué ejemplos concretos publican esas horas? | Seis primeros viajes elegibles de A, ordenados por primera salida y clave. |
| Ventanas de frecuencia | ¿Qué intervalos y tramos horarios publica la selección? | Ventanas Silver de plantillas con servicios activos en A. |
| Alcance del cálculo | ¿Cuántos viajes quedan fuera y qué precisión publican los extremos? | Categorías de trip_timing y precisión de extremos; cada denominador queda visible. |

## Fuentes, grano y filtros

Uso gold_gtfs_route_service_day, gold_gtfs_trip_timing, silver_gtfs_service_dates y silver_gtfs_frequencies.
Trips identifica el servicio y conserva la ruta de cada viaje.
No necesito importar stop_times ni crear una nueva tabla Gold para este incremento.

Trip_timing contiene una fila por viaje del catálogo.
La fecha no filtra ese hecho por una relación física directa.
Obtengo los servicios activos de service_dates para la fecha seleccionada.
Aplico service_key a trips y trip_key a timing mediante TREATAS.
Las claves incluyen versión, SHA-256 e ID.
Repito el ámbito para B sin retirar componente o ruta.
Conservo las relaciones físicas anteriores.

## Reglas de los horarios

- Uso únicamente timing_status=eligible para el perfil y los extremos comparables.
- Tomo la salida de la primera visita y la llegada de la última según el contrato Gold.
- Conservo horas mayores de 24; 26:00 continúa al día siguiente de la fecha de servicio.
- No convierto esos segundos en timestamps UTC ni los reduzco con módulo 24.
- La menor salida y la mayor llegada no prueban continuidad entre ambas.
- Cada viaje aporta una sola primera salida al perfil por hora.
- La suma del perfil debe igualar los viajes elegibles del contexto.
- Mantengo exact_as_published, approximate y unknown como precisión publicada, no como exactitud observada.
- Las plantillas quedan fuera del perfil de salidas individuales.
- Presento headway_secs en segundos, sin convertir 16 segundos en 16 minutos.
- No expando salidas ni estimo espera o capacidad a partir de ventanas.
- Las frecuencias se leen en un panel propio incluso cuando no hay viajes elegibles.

## Estados y límites

Permito selección global, componente o ruta.
Una ruta sin programación en A mantiene cero viajes activos y horas ausentes.
La programación de B puede seguir visible para contrastar esa ausencia.
Una fecha fuera del horizonte o ausente no produce cero de negocio.
El calendario no etiqueta festivos a partir del nombre del día.
La muestra de viajes queda limitada y muestra su tamaño frente al total elegible.
Las ventanas visibles también indican cuándo existe un límite de filas.

## Diseño

Mantengo colores, tipografía y navegación del Panorama aprobado.
El calendario y los extremos horarios dan identidad propia a esta página.
Comparo A en rojo y B en amarillo, siempre con letras o etiquetas.
Uso HTML/SVG para presentación y filtros y navegación nativos de Power BI.
La vista previa utiliza resultados DAX reales.
No utilizo control de pantalla.

## Comprobaciones antes del cierre

1. Concilio viajes activos de timing con declarados del hecho diario.
2. Concilio categorías excluyentes de timing con los viajes activos.
3. Concilio la suma por hora con elegibles, para A y B.
4. Compruebo rutas inactivas en A y activas en B.
5. Compruebo TransMiCable sin salidas individuales y con ventanas activas.
6. Compruebo horas mayores de 24 y precisión aproximada.
7. Valido archivos PBIR y filtros por identidad.
8. Reviso la vista previa en tres anchos; Desktop queda sujeto a su revisión real.


## Cierre de la primera implementación

Guardé el panel y 18 medidas en el PBIP.
Consulté 90 selecciones y comprobé sus conciliaciones en la vista previa.
Añadí una etiqueta de ruta que distingue códigos cortos repetidos mediante su ID.
Sincronicé los cuatro filtros entre Panorama y Programación mediante la definición nativa.
La revisión del renderizado y la sincronización dentro de Desktop sigue pendiente.

La [documentación del panel](../BI/imagenes/programacion/README.md) contiene ejemplos, alcance y comprobaciones.
La [vista previa](../BI/imagenes/programacion/programacion_preview.html) permite revisar tres fechas y cuatro rutas concretas.
No amplié fuentes, contratos Gold ni relaciones físicas.
