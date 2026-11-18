# Mi propuesta de inicio, componentes e imágenes para Power BI

**Fecha:** 17 de noviembre de 2026.
**Estado:** prototipo HTML/JavaScript comprobado; archivo Power BI y visuales instalados todavía sin probar.
**Actualización:** 18 de noviembre de 2026.

## Cómo incorporo la referencia visual

La captura muestra un encabezado, fondo oscuro y contenedores con bordes suaves.
Tomo esos elementos como referencia de composición.
No deduzco sus interacciones ni la versión de Image Grid desde una captura.

Quiero separar dos acciones:

- Elegir una sección cambia la página.
- Elegir un componente cambia el contexto de análisis.

Una imagen puede representar cualquiera de esas acciones, pero debe indicar cuál realiza.
No esperaré que una imagen decorativa aplique filtros automáticamente.

## Organización propuesta: inicio y cuatro páginas analíticas

| Página | Contenido | Interacción principal |
| --- | --- | --- |
| 0. Inicio | Presentación breve, alcance y cuatro accesos visuales. | Abrir General, Programación, Red o Calidad. |
| 1. General por componente | Imagen, descripción, rutas publicadas, viajes declarados y ubicaciones relacionadas. | Seleccionar un componente y explorar sus indicadores. |
| 2. Programación y calendario | Fechas activas, patrones y ventanas de frecuencia. | Elegir fecha y ruta dentro del contexto seleccionado. |
| 3. Red publicada y ubicaciones | Mapa, secuencias y jerarquía de ubicaciones. | Explorar rutas y ubicaciones del componente. |
| 4. Calidad y revisión técnica | Cobertura del dato, casos concretos y procedencia. | Revisar casos y recuperar sus claves. |

Son cinco páginas físicas: una portada y cuatro páginas analíticas.
No añado otra página General que repita el panorama anterior.
Si necesito cuatro páginas físicas, puedo unir Inicio y General, conservando los accesos a las otras tres.

La portada tendrá cuatro tarjetas con una ilustración, título y una pregunta breve.
Cada tarjeta abrirá su página correspondiente.
Las páginas analíticas tendrán navegación persistente y un acceso visible a Inicio.

## Cómo funcionará General

Primero selecciono el snapshot.
Después selecciono un componente mediante tarjetas con imagen y nombre.
La selección cambia el título, la descripción, la imagen y los indicadores relacionados.
Un botón independiente abre Programación, Red o Calidad con el contexto sincronizado.

Por ejemplo, selecciono TransMiCable.
El reporte muestra la información publicada correspondiente a ese grupo en el snapshot elegido.
Consulto sus rutas, viajes declarados, ventanas y ubicaciones relacionadas.
La ilustración de una cabina ayuda a reconocer el contexto.
La cabina no representa una cantidad de vehículos físicos.

Usaré una selección única para la ficha individual.
Definiré también un estado de conjunto, con título e imagen propios.
Las selecciones múltiples no mostrarán arbitrariamente la imagen del primer componente.

## Nombres y correspondencias de componentes

No presentaré SITP y TransMiCable como categorías excluyentes.
SITP nombra el sistema integrado, que también incluye cable.
La [caracterización oficial de operación y control](https://www.transmilenio.gov.co/files/a13a96e6-4a00-49f0-b376-234dd2b47351/a13a970a-9f95-4d19-8eb5-d97294107ee2/C-SO-001-Operacion-y-Control-del-SITP-V5.pdf) distingue sus componentes.

Como etiquetas iniciales propongo Todo el sistema, Troncal, Zonal y TransMiCable.
Acordaré dónde ubicar Alimentación y Dual antes de aprobar las agrupaciones.
No deduciré esa correspondencia solamente del color del vehículo o de route_type.
Un mismo tipo GTFS de bus puede abarcar varios grupos del reporte.

Conservaré una correspondencia revisada entre cada snapshot y sus agencias o rutas.
Los agency_id cambiaron de significado entre 2025 y 2026.
No construiré una tabla global que asigne nombres de componentes usando solo agency_id.
Mantendré sin clasificar los casos que no tengan una correspondencia aprobada.

El catálogo de presentación puede contener:

| Campo | Uso |
| --- | --- |
| component_key | Clave propia del grupo de presentación. |
| display_name | Nombre visible acordado. |
| description | Explicación breve del grupo. |
| display_order | Orden de las tarjetas. |
| image_reference | Referencia a una imagen compatible con el visual elegido. |
| image_source | Procedencia de la imagen. |
| usage_rights | Permiso o licencia aplicable. |

La correspondencia con los datos conservará versión, hash y las claves necesarias.
Este enriquecimiento semántico no modificará los archivos fuente ni los IDs Silver.
El catálogo define presentación; las medidas y relaciones determinan qué datos cambian.

Los conteos de ubicaciones por componente usarán las visitas de sus viajes declarados.
No filtraré stops directamente por agency_id, porque stops no contiene esa relación.
Un conteo de catálogo completo permanecerá identificado como tal.

## Opciones verificadas para imágenes e interacción

| Necesidad | Opción | Aplicación propuesta |
| --- | --- | --- |
| Seleccionar un componente | Button slicer nativo | Tarjetas con imagen y etiqueta para filtrar. |
| Mostrar una imagen según el contexto | Image visual nativo con Select from data | Imagen principal en General. |
| Abrir otra página | Botones, navegadores o acción Page navigation del visual de imagen | Accesos de Inicio y menú persistente. |
| Conservar el componente entre páginas | Sync slicers | Sincronizar snapshot y componente donde corresponda. |
| Mostrar una galería personalizada | Image Grid u otro visual de AppSource | Alternativa si aporta una función necesaria. |

Microsoft documenta imágenes y etiquetas en el [Button slicer](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-button-slicer).
También documenta fuentes de datos y acciones de navegación en el [Image visual](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-image-visual).
Los [navegadores de páginas](https://learn.microsoft.com/en-us/power-bi/create-reports/button-navigators) permiten construir el menú del reporte.
La [sincronización de segmentadores](https://learn.microsoft.com/en-us/power-bi/visuals/power-bi-visualization-slicers) conserva selecciones entre páginas configuradas.

Recomiendo probar primero Button slicer, Image visual y navegación nativa.
Compruebo su disponibilidad en la versión instalada de Power BI Desktop.
No necesito instalar otro visual para comenzar esa prueba.

Image Grid ya forma parte de la experiencia del proyecto de referencia.
No asumo que el visual instalado admita sincronización, navegación o todas las interacciones necesarias.
Verificaré su publicador y versión mediante una prueba pequeña antes de elegirlo.
Existen visuales con nombres parecidos; no atribuyo funciones de uno a otro.
La [guía de AppSource](https://learn.microsoft.com/en-us/power-bi/developer/visuals/import-visual) explica cómo consultar e incorporar visuales.

## Cómo prepararé las imágenes

Puedo utilizar ilustraciones vectoriales propias o fotografías con permisos de uso comprobados.
Para las tarjetas recomiendo ilustraciones simples de los componentes acordados.
Mantendré el mismo encuadre, escala, estilo y proporción entre imágenes.
Un fondo transparente permite reutilizarlas sobre el diseño del reporte.

Como especificación inicial propongo tarjetas cuadradas de 512 por 512 píxeles.
Para una fotografía principal propongo una proporción de 16:9.
Son decisiones de diseño, no requisitos de Power BI.
Verificaré el formato admitido por cada visual antes de exportar.
Mantendré los nombres como texto del reporte, sin incrustarlos dentro de cada imagen.

Las fotografías reales comunican el contexto físico.
Las ilustraciones propias ofrecen mayor uniformidad entre componentes.
Una imagen generada debe presentarse como ilustración, sin atribuirle evidencia sobre infraestructura o flota.
No copiaré logotipos ni fotografías sin revisar sus condiciones de uso.

Las imágenes estáticas de Inicio pueden cargarse desde archivos locales al reporte.
Las imágenes dinámicas pueden usar referencias web accesibles o archivos de OneLake compatibles.
Una ruta C:\Users\... no sirve como URL web para las personas que abran el reporte.
La [documentación de imágenes](https://learn.microsoft.com/en-us/power-bi/create-reports/power-bi-images-tables) explica Image URL y sus requisitos.

Mantendré un registro versionado de recursos, procedencia y derechos cuando prepare los archivos.
No crearé una dependencia de un enlace temporal de una conversación.
No convertiré una imagen ausente en un error del indicador: utilizaré un recurso de reserva y una etiqueta clara.

## Criterios de aceptación del prototipo

1. Las cuatro tarjetas de Inicio abren la página correcta.
2. La selección TransMiCable cambia título, imagen e indicadores compatibles.
3. El contexto se conserva al navegar entre páginas configuradas.
4. Volver a Inicio no cambia filtros sin una acción explícita de restablecimiento.
5. Todo el sistema muestra contexto agregado sin contar rutas dos veces.
6. Las ubicaciones relacionadas concilian con el puente definido, sin multiplicarse por visitas repetidas.
7. Un componente sin datos muestra esa ausencia; no hereda indicadores de otro componente.
8. Las imágenes cargan en Desktop y en el entorno de publicación previsto.
9. Los accesos incluyen etiquetas legibles y texto alternativo.
10. Los recursos visuales no ocultan fuente, período ni limitaciones de los indicadores.

No usaré marcadores que capturen filtros sin revisar sus opciones de datos.
Un acceso de navegación no debe restablecer inadvertidamente el componente seleccionado.

## Prototipo HTML ya comprobado

Preparé cinco vistas: Inicio, General, Programación, Red y Calidad.
La selección cambia imágenes e indicadores y conserva el componente entre páginas.
El calendario, búsqueda, fichas, tema oscuro y estados vacíos responden a sus controles.
Pasaron 28 comprobaciones de interacción y adaptación a escritorio, tableta y móvil.

Las rutas DEMO, sus viajes y mapas son fixtures ilustrativos.
La ventana de 30 segundos pertenece al fixture, no al GTFS real.
Los conteos reales documentados aparecen separados en el detalle de fuentes.
Las ilustraciones SVG son propias y no constituyen evidencia de flota o infraestructura.
Usé rojo #DD212C, rosa #E86970 y azul #004499, con verde #258146 propuesto para Alimentación.
Reservé los códigos de líneas para una correspondencia real de corredores todavía pendiente.

El prototipo local permanece fuera del repositorio como artefacto de revisión.
No publiqué un sitio ni convertí el HTML en un archivo PBIX.
Los controles del HTML no demuestran funcionamiento de visuales nativos ni de Image Grid.

## Siguiente paso

Cerraré nombres y correspondencias de componentes antes de calcular sus indicadores.
Completaré las fichas de métricas y su reparto entre Databricks y medidas DAX.
Después probaré las interacciones en el entorno Power BI elegido.
Las [historias de negocio](power_bi_user_stories.md) conservan las preguntas y límites del reporte.
