# Brief para mi agente de LinkedIn: mi lakehouse GTFS y la documentación interactiva con Archify

Fecha de contexto: 7 de noviembre de 2026.

Este es material de contexto para preparar una publicación, no el texto final del post. Quiero presentar la idea de mi proyecto y usarlo como ejemplo de una alternativa para documentar arquitectura, pipelines y modelos de datos mediante diagramas interactivos.

## 1. Qué quiero comunicar

**Estoy construyendo un lakehouse de movilidad para Bogotá mientras aprendo Databricks. En el proceso incorporé Archify para que la documentación también se pueda explorar: seguir recorridos, consultar referencias al código y entender relaciones entre tablas.**

El proyecto aporta el caso real. El tema principal de esta publicación es cómo estoy documentándolo y qué cambia al poder recorrer una explicación, además de leerla.

Quiero compartir una experiencia de aprendizaje y una aplicación concreta de una herramienta existente. No desarrollé Archify ni pretendo presentar la documentación interactiva como una invención propia. Mi aporte consiste en aplicarla al proyecto, respaldar los diagramas con código y mantener claras las diferencias entre lo construido y lo pendiente.

Como orientación editorial, dedicaría aproximadamente dos tercios del post al enfoque de documentación y un tercio al contexto del lakehouse. Esta proporción es una preferencia para la publicación, no una medición.

## 2. El proyecto en pocas palabras

**Nombre:** Bogotá GTFS Mobility Lakehouse.

**Contexto personal:** es un proyecto de portafolio con el que estoy aprendiendo Databricks, PySpark, arquitectura medallion y calidad de datos. Lo construyo por etapas y procuro entender los resultados antes de avanzar.

**Idea:** conservar y organizar datos oficiales de movilidad de Bogotá para analizar la oferta planificada de TransMilenio. Más adelante quiero relacionarla con fuentes oficiales de validaciones y salidas, después de comprobar que sus fechas, ubicaciones y niveles de detalle sean compatibles.

**Punto de partida actual:** GTFS estático. Este formato organiza información del transporte mediante archivos como agencias, rutas, paradas, viajes, calendarios y horarios. Me permite estudiar la planificación publicada; por sí solo no demuestra lo que ocurrió en la operación real. Referencia: [especificación oficial GTFS Schedule](https://gtfs.org/documentation/schedule/reference/).

**Objetivo de largo plazo:** obtener métricas documentadas y trazables para análisis en Power BI. No estoy presentando un producto terminado ni una plataforma de producción completa.

## 3. Arquitectura general y qué significa cada parte

El recorrido implementado del GTFS estático es:

```text
Fuente oficial: ZIP GTFS
        ↓
Captura y manifiesto con procedencia
        ↓
Raw: ZIP original en un Volume de Unity Catalog
        ↓
Extracción
        ↓
Staging: TXT del snapshot en otro Volume
        ↓
Bronze: tablas Delta con datos fuente y procedencia
        ↓
Silver: validación, tipos, duplicados y relaciones
        ↓
Gold y Power BI: siguientes etapas, todavía pendientes
```

| Parte | Cómo la entiendo en mi proyecto |
| --- | --- |
| Raw | Guardo la evidencia original y sus manifiestos para poder volver a lo recibido. |
| Staging | Conservo los TXT extraídos del ZIP para su lectura y revisión. |
| Bronze | Cargo los datos fuente en Delta, conservando los campos de negocio como texto y añadiendo procedencia. |
| Silver | Aplico contratos por entidad: tipos explícitos, claves, calidad, duplicados y referencias. |
| Gold | Prepararé indicadores con una pregunta y un nivel de detalle definidos. Sigue pendiente. |
| Power BI | Será una capa de consumo analítico. Sigue pendiente. |

Los Volumes almacenan archivos. Bronze y Silver son tablas Delta. En la organización actual ambas capas comparten `workspace.gtfs_bogota` y se distinguen por sus nombres y responsabilidades: `bronze_gtfs_*` y `silver_gtfs_*`.

Mi stack actual incluye Python, PySpark, Databricks Free Edition, Unity Catalog, Volumes, Delta Lake, SQL, Jobs y GitHub. Archify se utiliza en el equipo de documentación; no es una dependencia del procesamiento de datos en Databricks.

## 4. Qué tengo y qué sigue pendiente

| Componente | Estado que puedo comunicar |
| --- | --- |
| Captura Raw y extracción a Staging | Ejecutadas para los snapshots estáticos trabajados. |
| Tablas Bronze y controles del snapshot | Ejecutados; con trazabilidad e identificación de cambios de esquema. |
| Silver de agency | Implementada y publicada para ambos snapshots. |
| Silver de routes | Implementada; confirmé la ejecución del flujo y la existencia de las tablas Silver después de corregir el manejo de identificadores de tablas. |
| Job manual Silver | Ejecutado para el flujo agency → routes; con trabajo por entidad y snapshot. |
| Resto de entidades Silver | Pendientes de desarrollar por etapas. |
| Gold, tableros Power BI e integración analítica con demanda | Pendientes. |
| GTFS-Realtime | Incorporación pendiente y sujeta a disponibilidad y validación de la fuente. |
| n8n/Ollama | Posible apoyo futuro de lectura y narrativa; no es un componente operativo del pipeline actual. |
| Documentación con Archify | Cinco HTML creados, comprobados en navegador y revisados visualmente; incluidos en la documentación versionada del repositorio; sin una demo web alojada. |

Algunas secciones antiguas del README todavía describen routes como pendiente de publicación. Para este brief tomo la confirmación posterior de ejecución y existencia de las tablas que registré durante el desarrollo. No estoy afirmando una nueva consulta en vivo de Databricks realizada al escribir este documento.

### Cifras disponibles, si necesito dar contexto

| Dato | Alcance |
| --- | --- |
| Snapshots trabajados | `2025-10-28` y `2026-09-29`. |
| Agency | 7 registros por snapshot. No implica siete empresas jurídicas distintas. |
| Routes | 676 registros en 2025 y 1.045 en 2026, según el perfilado. |
| Stop_times de 2026 | 9.408.893 filas en Bronze; no significa que esta entidad ya esté transformada en Silver. |

No necesito meter todas estas cifras en el post. Puedo usar una para mostrar que la documentación explica un caso real y reservar el resto como contexto.

## 5. Decisiones del proyecto que vale la pena explicar

### Conservar el histórico sin inventar continuidad

Encontré cambios en los nombres asociados a `agency_id` entre versiones. También comprobé que una URL puede repetirse entre agencias, por lo que no sirve como identificador único.

Decidí conservar la identidad dentro de cada snapshot, sin homologar agencias entre años por semejanza de nombre o por un ID aislado:

```text
Clave de agency = versión del feed + SHA-256 del snapshot + agency_id
Clave de routes = versión del feed + SHA-256 del snapshot + route_id
Relación routes → agency = versión del feed + SHA-256 + agency_id
```

Es como comparar dos ediciones de un catálogo: que ambas tengan un elemento con código 2 no prueba que describan lo mismo. Esta comparación es explicativa.

### Asignar tipos según el significado

Un ID sigue siendo `string`, aunque tenga dígitos. En routes, `route_type` y `route_sort_order` pasan a `int` con validaciones. Asignar tipos no significa rellenar datos faltantes ni fabricar valores.

### Distinguir una columna ausente de un valor nulo

Silver lee las filas de Bronze y también el encabezado del TXT en Staging. Esto permite distinguir un campo no publicado en una versión de uno publicado sin contenido. Conservo `source_columns` como parte de esa trazabilidad.

### Separar exploración, reglas y ejecución

Los notebooks 08 apoyan el perfilado y la explicación; el 09 valida agency sin publicar. La lógica reutilizable está en módulos Python. El notebook 10 actúa como entrada de ejecución para el pipeline compartido de agency y routes.

El Job ordena agency antes de routes porque routes necesita la referencia del mismo snapshot. Cada trabajo lleva entidad, versión y hash. La publicación mantiene auditoría y cuarentena; ante rechazos no publico solo un subconjunto de candidatos como si todo el snapshot hubiera sido aceptado.

La reejecución busca conservar el resultado de negocio sin duplicar el snapshot ni alterar otros históricos. Los identificadores y timestamps de ejecución pueden cambiar entre intentos.

## 6. Qué problema de documentación estoy abordando

Mientras avanzo aparecen más notebooks, módulos, parámetros, tablas y estados del Job. Una descripción larga puede explicar cada pieza, pero me cuesta reconstruir el recorrido completo cuando retomo el proyecto.

Quiero que la documentación ayude a responder preguntas concretas:

- ¿Dónde están los archivos y dónde empiezan las tablas?
- ¿Qué ocurre cuando pulso `Run now`?
- ¿Por qué routes espera a agency?
- ¿Qué diferencia hay entre un rechazo de calidad y un fallo de publicación?
- ¿Qué columnas identifican un registro y cuáles solo describen una ejecución?
- ¿Qué está implementado y qué sigue en el plan?

La idea no es añadir dibujos decorativos: quiero una entrada visual a las decisiones, respaldada por el código y complementada por contratos y procedimientos.

## 7. La herramienta que incorporé: Archify

[Archify](https://github.com/tt-a1i/archify) es un proyecto de código abierto que permite generar diagramas interactivos en HTML con ayuda de un agente. Puede partir de una descripción o del análisis de un repositorio. En mi caso lo instalé como skill local de Codex y lo apliqué a código y documentación del lakehouse. La versión instalada en esta experiencia es 3.2.0; no estoy afirmando que sea la última disponible.

En los documentos creados puedo explorar componentes y recorridos, consultar referencias al código, buscar elementos, usar zoom, cambiar entre temas claro y oscuro y acceder a opciones de exportación. Los HTML se abren en el navegador; leer el diagrama no requiere entrar en mi workspace de Databricks.

La animación explica las conexiones del dibujo. No representa datos circulando en vivo ni confirma el estado de un Job.

Fuente de la herramienta y sus capacidades generales: [repositorio oficial de Archify](https://github.com/tt-a1i/archify). Las decisiones de uso descritas aquí corresponden a mi implementación local.

## 8. Los tres documentos visuales que ya preparé

| Documento | Vistas creadas | Pregunta principal |
| --- | --- | --- |
| Mapa del lakehouse | Un diagrama de flujo de datos. | ¿Dónde están los datos y cómo avanzan entre capas? |
| Recorrido del Job Silver | Orden del Job y detalle de una iteración por snapshot. | ¿Qué pasa al ejecutar y qué ocurre ante errores? |
| Modelo GTFS | ERD Silver actual y panorama de crecimiento. | ¿Cómo se relacionan las tablas y cómo ampliaré el modelo? |

En total son **cinco HTML interactivos**.

### Mapa del lakehouse

Muestra fuente, captura, Raw, extracción, Staging, ingesta Bronze y pipeline Silver. Incluye las dos entradas de Silver: filas Bronze y encabezado del TXT. Gold y Power BI están identificados como trabajo futuro.

### Recorrido del Job Silver

La primera vista muestra agency → routes y la dependencia de éxito. La segunda explica una iteración: lectura, validación, auditoría, cuarentena, decisión, publicación y comprobación final. Diferencia errores previos, rechazos y fallos de publicación; también contempla que un fallo posterior a escribir exige revisar lo que quedó persistido.

### Modelo GTFS

El ERD contiene las **16 columnas de agency y las 18 de routes**, con tipos y claves compuestas. Sus marcas de clave representan validaciones del contrato; no afirman restricciones PRIMARY KEY o FOREIGN KEY declaradas en Delta.

El panorama incorpora el alcance pendiente: stops, puntos de shapes, calendar, calendar_dates, la propuesta derivada service_dates, trips, frequencies, stop_times, feed_info y tarifas. Sus ramas agrupan responsabilidades; no son relaciones de clave foránea ni indican el orden exacto del Job.

## 9. Cómo documento ahora y cómo lo mantendré

1. Parto de una pregunta que el documento debe resolver.
2. Reviso los archivos, contratos y operaciones reales de lectura y escritura del repositorio.
3. Fijo el commit del código que estoy explicando y vinculo elementos con archivos y líneas de esa revisión.
4. Creo una fuente JSON editable para el tipo de diagrama adecuado.
5. Genero el HTML con Archify y ejecuto sus comprobaciones de estructura, referencias, entrega y navegador.
6. Reviso capturas en claro y oscuro a 1440×900 y 2048×1320.
7. Conservo fuente, HTML, guía de lectura y un resumen público de verificación dentro del proyecto.
8. Cuando cambia una responsabilidad, una dependencia o un contrato, reviso el documento afectado junto con el código.

Los diagramas actuales apuntan al código del commit `598bc0de6b65b25ffa2ef13b628ab0966fd41dcd`.

```text
docs/flujo_pipeline/
├── README.md
├── mapa_lakehouse/
│   ├── README.md
│   ├── mapa_lakehouse.dataflow.json
│   ├── mapa_lakehouse.html
│   └── verificacion.json
├── job_silver/
│   ├── README.md
│   ├── recorrido_job.workflow.json
│   ├── recorrido_job.html
│   ├── iteracion_snapshot.workflow.json
│   ├── iteracion_snapshot.html
│   └── verificacion.json
└── modelo_gtfs/
    ├── README.md
    ├── modelo_silver.erd.json
    ├── modelo_silver.html
    ├── panorama_gtfs.tree.json
    ├── panorama_gtfs.html
    └── verificacion.json
```

Las fuentes JSON permiten reproducir y revisar cambios mediante Git; los HTML son la salida de lectura. Los contratos siguen definiendo las reglas y el runbook sigue explicando cómo operar. El diagrama facilita entrar a esas referencias.

La actualización no es automática: un cambio de código no vuelve a generar los documentos por sí solo. La calidad visual tampoco garantiza que el pipeline esté correcto; esa comprobación corresponde a pruebas y ejecuciones del procesamiento.

## 10. Qué valor encuentro y qué no he medido

| Valor que busco | Cómo se refleja en esta experiencia |
| --- | --- |
| Retomar el proyecto con menos esfuerzo | Puedo ubicar una etapa y seguir sus conexiones antes de abrir los archivos. |
| Explicar decisiones | La clave por snapshot, la dependencia agency–routes y las etapas futuras quedan visibles. |
| Conectar explicación y evidencia | Los elementos enlazan código de una revisión fija. |
| Dar distintos niveles de detalle | Paso del mapa general al interior de una iteración o a las columnas de las tablas. |
| Mantener la documentación revisable | Guardo fuente editable, HTML y comprobaciones junto al proyecto. |
| Compartir lo que voy aprendiendo | Puedo mostrar un recorrido concreto sin exigir que otra persona conozca todo Databricks. |

Son ventajas prácticas que encuentro y objetivos de uso. No tengo un estudio de productividad ni una medición de ahorro de horas, reducción de errores o velocidad de aprendizaje. No atribuiré porcentajes de eficiencia a esta experiencia.

## 11. Contexto secundario: Codex y Databricks Genie

Durante el desarrollo incorporé la conexión MCP con Genie para pedir consultas de lectura y contrastar hallazgos sobre las tablas. Esto facilita acercar el asistente al contexto de los datos sin depender de copiar manualmente cada resultado.

Las consultas relevantes quedaron documentadas y llevadas a notebooks para conservar la explicación. Genie apoya la exploración; las transformaciones y publicaciones son deterministas y están implementadas en código.

Es un punto complementario para otra publicación o una mención breve. En esta ocasión quiero mantener el foco en Archify y la documentación interactiva.

## 12. Material visual que puedo usar para la publicación

Mi opción preferida sería una grabación corta de pantalla con este recorrido:

1. Abro el mapa del lakehouse y ubico Raw, Bronze y Silver.
2. Cambio al Job y sigo la dependencia agency → routes.
3. Abro el modelo y señalo versión, hash e ID.
4. Selecciono un elemento y muestro su referencia al código.

También puedo preparar un carrusel: contexto del proyecto, mapa del lakehouse, recorrido del Job y modelo con el aprendizaje principal.

Una captura ayuda a mostrar el diseño; el vídeo permite apreciar la interactividad. La duración y los formatos se decidirán al preparar la pieza. Usaré los diagramas como material visual para no exponer pantallas con credenciales o configuración personal del workspace.

## 13. Orientaciones para redactar mi publicación

Quiero una voz cercana, en primera persona, de alguien que construye y aprende. Evitar una narración externa sobre mí.

Posibles ideas de apertura, para adaptar:

- «Mientras aprendo Databricks con un proyecto de movilidad de Bogotá, también estoy probando otra forma de documentarlo: recorrer sus flujos en el navegador».
- «Mi proyecto empezó con archivos GTFS. Ahora también tiene mapas interactivos para explicar dónde van los datos y por qué tomé ciertas decisiones».
- «Quería entender mejor mi propio pipeline cuando volviera a abrir el proyecto. Por eso incorporé documentación que puedo explorar».

La publicación puede seguir este orden: dificultad concreta de explicar el flujo, contexto breve del lakehouse, aplicación de Archify, ejemplo visual y aprendizaje personal.

Puedo cerrar con una pregunta como: «¿Cómo documentan ustedes un pipeline para que otra persona pueda entender sus decisiones y recorridos?».

Etiquetas posibles, para escoger pocas: `#IngenieriaDeDatos`, `#Databricks`, `#DocumentacionTecnica`, `#DataEngineering`, `#BuildInPublic`. Puedo añadir Archify si encaja con el enfoque.

## 14. Enlaces y estado de publicación

### Enlaces de referencia

| Recurso | Enlace y uso |
| --- | --- |
| Mi repositorio | [Bogotá GTFS Mobility Lakehouse](https://github.com/Kevinx1919/GTFS-Bogot-). Confirmé que su visibilidad es pública mediante el conector de GitHub. |
| Código que respaldan los diagramas | [Revisión fija del proyecto](https://github.com/Kevinx1919/GTFS-Bogot-/tree/598bc0de6b65b25ffa2ef13b628ab0966fd41dcd). |
| Reglas de agency | [Contrato agency](https://github.com/Kevinx1919/GTFS-Bogot-/blob/598bc0de6b65b25ffa2ef13b628ab0966fd41dcd/docs/contracts/agency.md). |
| Reglas de routes | [Contrato routes](https://github.com/Kevinx1919/GTFS-Bogot-/blob/598bc0de6b65b25ffa2ef13b628ab0966fd41dcd/docs/contracts/routes.md). |
| Archify | [Repositorio de la herramienta](https://github.com/tt-a1i/archify). Debe quedar acreditada como herramienta externa. |
| Revisión usada para instalar la skill | [Archify en el commit fijado](https://github.com/tt-a1i/archify/tree/a4065941f12be7967436261d9934784e381d423c/archify). |
| GTFS | [Referencia oficial GTFS Schedule](https://gtfs.org/documentation/schedule/reference/). |
| Fuentes de movilidad | [Portal de datos abiertos de TransMilenio](https://datosabiertos-transmilenio.hub.arcgis.com/), registrado como fuente en el proyecto. |

### Documentos locales para preparar la pieza

- [Índice de documentación visual](flujo_pipeline/README.md).
- [Mapa del lakehouse](flujo_pipeline/mapa_lakehouse/mapa_lakehouse.html).
- [Orden del Job](flujo_pipeline/job_silver/recorrido_job.html).
- [Iteración por snapshot](flujo_pipeline/job_silver/iteracion_snapshot.html).
- [Modelo Silver actual](flujo_pipeline/modelo_gtfs/modelo_silver.html).
- [Panorama de crecimiento GTFS](flujo_pipeline/modelo_gtfs/panorama_gtfs.html).

Estos enlaces relativos funcionan junto al repositorio local; no son URLs para pegar en LinkedIn. Si transfiero solo este Markdown a otro agente, también tendré que compartir los HTML o material visual para que pueda inspeccionarlos.

La carpeta visual y este brief se incluyen en la documentación versionada del repositorio. No hay una demo propia alojada en una URL pública. No debo prometer «pruébalo aquí» enlazando una ruta del computador. Tener un HTML en GitHub tampoco equivale a tener una página interactiva alojada. Si más adelante publico una demo, podré añadir su URL real.

## 15. Límites para que el mensaje represente el proyecto con precisión

- Presento un proyecto en desarrollo y mi experiencia de aprendizaje, no un sistema completo en producción.
- No atribuyo a los datos estáticos mediciones de ocupación, puntualidad, tiempos de espera o congestión real.
- No presento Gold, Power BI, demanda integrada o GTFS-Realtime como componentes operativos actuales.
- No afirmo que todos los contratos Silver estén terminados; el incremento implementado comprende agency y routes.
- No digo que los diagramas se mantengan solos ni que sus animaciones sean monitoreo en tiempo real.
- No atribuyo la creación de Archify a mi proyecto ni invento resultados cuantificados de productividad.
- Distingo lo que comprobé en los HTML de lo que ejecuté en Databricks.

**Idea que quiero que quede:** mientras construyo un proyecto de datos, también puedo construir una explicación que otra persona recorra y contraste con el código. Archify es la herramienta que estoy probando para hacerlo, y el lakehouse de Bogotá es mi caso concreto.
