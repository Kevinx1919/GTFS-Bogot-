# Mis historias de negocio para Power BI

**Fecha:** 17 de noviembre de 2026.
**Estado:** preguntas y diseño candidatos documentados; prototipo HTML revisado.
Las fórmulas finales y el modelo de consumo requieren completar sus contratos.
Todavía no construí el reporte en Power BI.
**Entrega inicial:** GTFS estático, Gold y Power BI.

## Propósito y contexto

Quiero que cada página ayude a revisar una decisión concreta.
Imagino personas con responsabilidades distintas dentro de TransMilenio.
Estas historias son escenarios de portafolio; no representan entrevistas ni solicitudes reales de la entidad.
Uso roles funcionales; no afirmo que sus nombres coincidan con cargos vigentes.

La entidad declara funciones de gestión, organización y planeación del transporte público masivo.
También declara funciones relacionadas con contratación y coordinación del sistema.
Tomo ese contexto de su [página oficial de objeto y funciones](https://www.transmilenio.gov.co/comunicaciones/publicaciones/2025/objeto-y-funciones-de-transmlenio-s-a).
Las historias y el diseño del reporte son mi propuesta, no una interpretación de obligaciones contractuales.

Mi pregunta general será:
**¿Cómo describe el GTFS la oferta planificada y qué información necesito revisar antes de utilizarla?**

El reporte apoyará revisiones de programación, red publicada y aptitud del dato.
Una revisión puede terminar en una solicitud de aclaración, no necesariamente en una modificación del servicio.

## Palabras que mantendré constantes

| Palabra | Significado en mi reporte |
| --- | --- |
| Snapshot | Versión del feed identificada por versión y SHA-256. |
| Ruta publicada | Registro de routes dentro de un snapshot. |
| Viaje declarado | Registro de trips; puede actuar como plantilla por frecuencia. |
| Visita | Registro de stop_times: una ubicación dentro de la secuencia de un viaje declarado. |
| Servicio activo | service_id habilitado para una fecha según service_dates. |
| Ventana de frecuencia | Intervalo publicado con un headway_secs; no describe operación observada. |
| Ubicación | Registro de stops; puede representar una parada, plataforma, estación u otro tipo. |
| Agencia GTFS | Registro de agency; no identifica necesariamente una empresa operadora ni un contrato. |

## Inicio y cuatro páginas analíticas candidatas

Amplié la propuesta con una portada visual y una ficha General por componente.
El [diseño de navegación e imágenes](power_bi_navigation_images.md) documenta las opciones verificadas y las correspondencias pendientes.
La portada añade accesos; General desarrolla el panorama de la primera página.
Son cinco páginas físicas si mantengo Inicio separado.

| Página | Persona principal | Pregunta central | Acción posible |
| --- | --- | --- | --- |
| 1. General por componente | Gerencia | ¿Qué describe este snapshot y dónde requiere revisión? | Elegir un componente o ruta para revisión técnica. |
| 2. Programación y calendario | Programación del servicio | ¿Qué programación declara una ruta para una fecha? | Contrastar patrones, fechas y ventanas con la programación de referencia. |
| 3. Red publicada y ubicaciones | Planeación e información al público | ¿Qué ubicaciones relaciona el feed con cada ruta? | Revisar recorridos y completar información publicada. |
| 4. Calidad y revisión técnica | Responsable del dato y supervisión técnica | ¿Qué puedo analizar y qué debo aclarar primero? | Abrir una revisión con claves y evidencia reproducible. |

La cuarta página también apoyará a quien prepara una revisión contractual.
No incluiré un semáforo de cumplimiento contractual sin fuentes contractuales y operación observada.
Si necesito cuatro páginas físicas, uniré Inicio y General.
Conservaré las otras tres páginas analíticas y sus límites visibles.

## Página 1: General por componente

### HU-01 — Conocer el contenido del snapshot

**Como responsable de gerencia, quiero conocer la red publicada para priorizar una revisión con el equipo técnico.**

- **Pregunta:** ¿Cuántas rutas y ubicaciones publica el snapshot por agencia GTFS y tipo de ruta?
- **Indicadores candidatos:** rutas distintas; ubicaciones por tipo; viajes declarados, con sus clases de cobertura.
- **Acción:** seleccionar un grupo y abrir su detalle.
- **Fuentes:** agency, routes, stops, trips y cobertura de viajes.
- **Aceptación:** cada tarjeta indica snapshot, unidad y filtros aplicados.
- **Límite:** no denomino operadores a las agencias GTFS ni buses al conteo de viajes declarados.

Las ubicaciones pertenecen al catálogo completo cuando no aplico una relación con rutas.
Un filtro de agencia no filtrará ese catálogo sin un puente de relaciones definido.

### HU-02 — Encontrar rutas que necesitan aclaraciones

**Como responsable de gerencia, quiero localizar programación con información limitada para pedir una revisión específica.**

- **Pregunta:** ¿Qué rutas concentran viajes declarados sin visitas o con una sola visita?
- **Indicador candidato:** proporción por ruta, acompañada del numerador y del denominador.
- **Acción:** abrir los viajes afectados y solicitar aclaraciones al responsable del dato.
- **Fuentes:** trips, routes y cobertura de viajes.
- **Aceptación:** las categorías concilian con todos los viajes declarados del contexto seleccionado.
- **Límite:** una ausencia de visitas no demuestra una cancelación ni una infracción.

No convertiré una clasificación técnica en una calificación de calidad del servicio.

### HU-03 — Entender una comparación entre fechas

**Como responsable de gerencia, quiero comparar dos fechas para revisar diferencias en la programación publicada.**

- **Pregunta:** ¿Qué rutas tienen viajes declarados asociados a servicios activos en cada fecha?
- **Indicadores candidatos:** rutas con programación declarada; viajes declarados asociados a servicios activos.
- **Acción:** solicitar explicación de diferencias a programación.
- **Fuentes:** service_dates, trips, routes y frequencies.
- **Aceptación:** ambas fechas pertenecen al horizonte 2026 del mismo snapshot.
- **Límite:** separo plantillas por frecuencia; no presento estos conteos como salidas operadas.

Comparo días según la información publicada en el snapshot seleccionado.
No afirmo que el snapshot reconstruya lo ocurrido realmente en esas fechas.

## Página 2: programación y calendario

### HU-04 — Revisar el calendario de una ruta

**Como responsable de programación, quiero consultar fechas activas para contrastar el calendario publicado de una ruta.**

- **Pregunta:** ¿Qué fechas habilitan los servicios utilizados por los viajes declarados de esta ruta?
- **Indicadores candidatos:** días con programación declarada; servicios activos; fechas con adiciones explícitas.
- **Acción:** contrastar una fecha esperada con patrones semanales y excepciones.
- **Fuentes:** calendar, calendar_dates, service_dates, trips y routes.
- **Aceptación:** las adiciones y retiradas reproducen la derivación de service_dates.
- **Límite:** un service_id no representa un bus ni una salida individual.

El detalle mostrará las retiradas desde calendar_dates.
Service_dates contiene días activos; no conserva filas de días retirados.

### HU-05 — Revisar el intervalo horario publicado

**Como responsable de programación, quiero consultar horas publicadas para detectar casos que requieren revisión.**

- **Pregunta:** ¿Qué primeras y últimas horas publicadas encuentro en los viajes declarados de una ruta y fecha?
- **Indicadores candidatos:** extremos horarios del conjunto elegible; viajes excluidos por información insuficiente.
- **Acción:** revisar casos concretos contra la programación de referencia.
- **Fuentes:** stop_times, trips, service_dates, frequencies y cobertura de viajes.
- **Aceptación:** conservo horas superiores a 24:00 y muestro las clases de cobertura.
- **Límite:** los extremos no prueban continuidad del servicio durante todo el intervalo.

Definiré primero si mido extremos de todas las visitas o solamente extremos de cada viaje.
No trataré las horas de una plantilla por frecuencia como salidas individuales.
Mostraré sus ventanas en una visualización separada.
Un timepoint aproximado impide presentar todas las horas como exactas.

### HU-06 — Interpretar la programación por frecuencia

**Como responsable de programación, quiero separar las ventanas de frecuencia para evitar confundir plantillas con salidas individuales.**

- **Pregunta:** ¿Qué rutas publican ventanas de frecuencia y qué intervalos declaran?
- **Indicadores candidatos:** plantillas distintas; ventanas; headway_secs por ventana.
- **Acción:** revisar duración, intervalo y alcance de cada ventana.
- **Fuentes:** frequencies, trips y routes.
- **Aceptación:** cuento ventanas y plantillas por separado.
- **Límite:** no convierto automáticamente duración dividida por intervalo en viajes exactos.

El perfil 2026 documenta 14 ventanas para 14 viajes declarados de una ruta de cable.
No presentaré sus intervalos como frecuencia general de los buses.

## Página 3: red publicada y ubicaciones

### HU-07 — Explorar las ubicaciones relacionadas con una ruta

**Como responsable de planeación, quiero explorar las ubicaciones publicadas de una ruta para revisar su representación geográfica.**

- **Pregunta:** ¿Qué ubicaciones aparecen en los viajes declarados de una ruta?
- **Indicadores candidatos:** ubicaciones distintas con visitas; viajes declarados que las referencian.
- **Acción:** abrir un viaje y revisar su secuencia y trazado publicado.
- **Fuentes:** routes, trips, stop_times, stops y shape_points.
- **Aceptación:** el detalle distingue secuencia de visitas y puntos del trazado.
- **Límite:** un punto del trazado no representa automáticamente una parada.

El modo catálogo no exige una fecha activa.
El modo por fecha utiliza service_dates y muestra ese alcance.
No uniré todos los puntos del trazado con todas las visitas para calcular los conteos.

### HU-08 — Distinguir estaciones y plataformas

**Como responsable de información al público, quiero distinguir estaciones y plataformas para revisar nombres y relaciones de ubicaciones.**

- **Pregunta:** ¿Qué plataformas pertenecen a cada estación publicada?
- **Indicadores candidatos:** ubicaciones por tipo; estaciones con y sin ubicaciones hijas publicadas.
- **Acción:** solicitar revisión de nombres, jerarquías o información faltante.
- **Fuentes:** stops, con una relación padre-hijo dentro del snapshot.
- **Aceptación:** los conteos distinguen estaciones, plataformas y otros tipos.
- **Límite:** no sumo estaciones y plataformas como si fueran paradas equivalentes.

Una estación sin hijas publicadas es un caso de revisión del catálogo.
No demuestra que la estación física carezca de plataformas.

### HU-09 — Revisar información publicada de accesibilidad

**Como responsable de accesibilidad, quiero conocer la cobertura del atributo para priorizar la revisión de información publicada.**

- **Pregunta:** ¿Qué códigos de wheelchair_boarding publica el feed para cada tipo de ubicación?
- **Indicadores candidatos:** códigos 1, 2, 0 y ausencias, separados por tipo.
- **Acción:** solicitar información o verificación de casos específicos.
- **Fuentes:** stops y su metadata de columnas publicadas.
- **Aceptación:** muestro conteos y proporciones con denominadores del tipo seleccionado.
- **Límite:** no calculo un porcentaje global de estaciones accesibles con estos códigos sin resolver su semántica.

Stops_v1 no resuelve la herencia de accesibilidad entre estaciones y plataformas.
Un valor ausente o desconocido no prueba una barrera física.
La validación de coordenadas tampoco certifica pertenencia al polígono de Bogotá.

## Página 4: calidad y revisión técnica

### HU-10 — Preparar evidencia para supervisión

**Como responsable de supervisión técnica, quiero consultar la programación publicada para preparar preguntas con evidencia identificable.**

- **Pregunta:** ¿Qué ruta, servicio, fechas y visitas declara el snapshot para el caso revisado?
- **Detalle candidato:** ruta, viaje declarado, servicio, fechas, cobertura y referencias de procedencia.
- **Acción:** adjuntar claves y alcance al solicitar aclaraciones al equipo correspondiente.
- **Fuentes:** routes, trips, service_dates, stop_times y auditorías.
- **Aceptación:** el detalle conserva snapshot e IDs; no inventa una relación con contratos.
- **Límite:** necesito un catálogo contractual validado para asociar rutas, operadores y obligaciones.

Es como preparar una carpeta de evidencia antes de una reunión.
El feed ayuda a describir lo publicado; no demuestra que el contrato se cumplió.

### HU-11 — Priorizar revisiones del dato

**Como responsable del dato, quiero localizar casos con información limitada para organizar una revisión reproducible.**

- **Pregunta:** ¿Qué rutas concentran viajes declarados sin visitas, con una visita o con otras limitaciones definidas?
- **Indicadores candidatos:** casos por categoría y ruta; participación dentro de los viajes declarados de cada ruta.
- **Acción:** revisar un caso, registrar la respuesta y decidir si requiere una corrección en origen.
- **Fuentes:** cobertura de viajes y catálogos Silver.
- **Aceptación:** el detalle permite recuperar el caso con la clave completa.
- **Límite:** el reporte no modifica Raw, Bronze ni Silver y no atribuye causas sin evidencia.

El perfil 2026 encontró 739 viajes sin visitas y 61 con una visita.
Estos resultados justifican explorar esta historia; todavía no definen un umbral de alarma.
Una regla Silver aprobada y una limitación analítica pueden coexistir.

### HU-12 — Saber qué información puedo utilizar

**Como analista de Power BI, quiero identificar fuentes y límites para interpretar correctamente cada indicador.**

- **Pregunta:** ¿Qué snapshot, reglas y exclusiones sustentan el resultado seleccionado?
- **Detalle candidato:** procedencia, horizonte, fuentes, ejecución utilizada y exclusiones del indicador.
- **Acción:** decidir si el resultado sirve para la pregunta planteada.
- **Fuentes:** auditorías Bronze/Silver, contratos y futura auditoría Gold.
- **Aceptación:** la fecha de carga permanece separada del período de servicio y de la versión fuente.
- **Límite:** una ejecución exitosa no prueba actualidad del servicio ni exactitud de la operación.

Mostraré la ejecución vinculada a la tabla consumida, no solamente el último intento registrado.
No definiré antigüedad aceptable sin acordar una política de actualización.

## Preguntas valiosas que necesitan otras fuentes

| Persona | Pregunta | Información adicional necesaria |
| --- | --- | --- |
| Supervisión contractual | ¿Cada operador cumplió su programación contratada? | Contratos, obligaciones, programación aprobada, operación observada y correspondencias con vigencia temporal. |
| Gerencia | ¿Dónde necesito aumentar flota? | Demanda, capacidad, flota disponible y operación observada compatible. |
| Atención al público | ¿Cuánto esperaron realmente las personas? | Observaciones de llegadas y metodología explícita de espera. |
| Planeación | ¿Qué barrios o poblaciones carecen de cobertura? | Polígonos oficiales, población y método de acceso o distancia. |
| Finanzas | ¿Cuánto dinero recaudó una ruta? | Transacciones o recaudo, reglas de asignación y correspondencias verificadas. |
| Operación | ¿Qué viajes llegaron tarde o se cancelaron? | Programación de referencia y eventos observados con claves compatibles. |

El GTFS estático contribuye a algunas comparaciones cuando incorpore esas fuentes.
Por sí solo no responde esas preguntas.

## Priorización propuesta

| Prioridad | Historias | Motivo |
| --- | --- | --- |
| Primera | HU-01, HU-02, HU-04, HU-06, HU-07, HU-08, HU-10, HU-11, HU-12 | Aprovechan entidades disponibles y permiten revisiones concretas. |
| Segunda | HU-03, HU-05, HU-09 | Necesitan cerrar definiciones de comparación, horas y accesibilidad antes de implementar métricas. |
| Ampliación | Cumplimiento, demanda, recaudo y cobertura poblacional | Requieren fuentes ajenas al alcance estático inicial. |

La prioridad es una propuesta; no sustituye una validación con personas del negocio.
Puedo demostrar cuatro páginas sin incluir todas las historias desde el primer incremento.

## Traducción de historias a Gold

Silver conserva entidades tipadas y referencias validadas.
Gold prepara preguntas, agregaciones, categorías y denominadores para el reporte.
No necesito una tabla Gold distinta por historia ni por página.

| Pieza candidata | Una fila representa | Historias relacionadas |
| --- | --- | --- |
| Cobertura de viajes | Un viaje declarado dentro de un snapshot. | HU-01, HU-02, HU-10, HU-11. |
| Programación por ruta y fecha | Una ruta y fecha dentro de un snapshot y horizonte. | HU-03, HU-04. |
| Relación ruta-ubicación | Una pareja distinta de ruta y ubicación dentro de un snapshot. | HU-07. |
| Catálogo analítico de ubicaciones | Una ubicación dentro de un snapshot, con tipo y relación padre. | HU-01, HU-08, HU-09. |
| Contexto y trazabilidad | Un snapshot o ejecución, según el contrato de cada tabla. | HU-12 y contexto de todas las páginas. |

No fijé nombres físicos ni publiqué estas piezas como tablas Gold.
La cobertura dispone de un prototipo local; las demás piezas requieren sus contratos de negocio.
Las horas y ventanas pueden necesitar piezas adicionales cuando cierre HU-05 y HU-06.

## Reglas del modelo y criterios comunes

- Conservaré versión y hash en las relaciones junto con cada ID de negocio.
- Mostraré inicialmente programación por fecha solo para el horizonte 2026 ya derivado.
- Mantendré 2025 como catálogo histórico; no inventaré un calendario diario 2025.
- No interpretaré cambios de IDs entre snapshots como aperturas o cierres físicos demostrados.
- Agregaré visitas y ventanas por viaje antes de unirlas con trips.
- Construiré relaciones ruta-ubicación distintas; no multiplicaré sus conteos por visitas repetidas.
- No expandiré todas las visitas por todas las fechas para obtener un agregado de rutas por fecha.
- Reconciliaré categorías con sus totales del mismo contexto.
- Indicaré cuándo una tarjeta usa catálogo completo y cuándo usa programación asociada a una fecha.
- Mantendré visibles ausencias, exclusiones y denominadores.
- No mezclaré automáticamente códigos GTFS con operadores, contratos, localidades o vehículos físicos.

Cada nueva tabla Gold responderá seis preguntas antes de implementarse:

1. Qué pregunta responde.
2. Qué representa una fila.
3. Qué ubicaciones incluye.
4. Cómo trata los valores ausentes.
5. Qué claves usa para relacionar datos.
6. Qué limitaciones debe mostrar Power BI.

## Necesidad de las tres entidades pendientes

Estas historias no exigen incorporar tarifas al reporte inicial.
Mantengo fare_attributes y fare_rules en Bronze hasta elegir una pregunta tarifaria concreta.
La tarifa 2026 revisada corresponde a TransMiCable; no representa una tarifa universal del sistema.
Feed_info puede enriquecer el contexto si selecciono sus atributos publicados.
Su ausencia en Silver no impide identificar el snapshot mediante la trazabilidad existente.
Conservo la [evaluación previa](remaining_silver_assessment.md) para decidir futuras ampliaciones.

## Próxima decisión

Primero acordaré las páginas y las historias prioritarias.
Después cerraré las fichas de indicadores con ejemplos de rutas, fechas y exclusiones.
Solo entonces elegiré las tablas Gold necesarias y publicaré el primer incremento.

## Evidencia del proyecto

- [Contratos y arquitectura Silver](silver_design.md).
- [Cobertura de viajes medida en 2026](trip_coverage_profile_2026.md).
- [Contrato de viajes](contracts/trips.md).
- [Contrato de ubicaciones](contracts/stops.md).
- [Contrato de fechas activas](contracts/service_dates.md).
- [Perfil de frecuencias](frequencies_profile_2025_2026.md).
- [Plan de cierre](gold_plan.md).
