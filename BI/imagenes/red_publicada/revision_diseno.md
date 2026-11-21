# Revisión de Red publicada

Conservé el marco aprobado de Panorama y Programación.
Usé la distribución geográfica real como elemento principal y una ficha oscura para interpretar la selección.
La comparación inferior cambia de pregunta cuando elijo una ruta única.

ROUND 3
Seen in one second: ubicaciones de Bogotá y una proporción de ubicaciones compartidas.
Idea (one sentence): paso de la red completa a un ID y explico qué relaciones publica sin deducir transbordos.
Live thing: componente, ruta y ubicación cambian resultados DAX reales; el PBIP añade selección de fila nativa.
Layout words by section: navegación=columna / filtros=fila / indicadores=franja / mapa=campo geográfico / ficha=interpretación / rutas=ranking / ubicaciones=tabla.
Scores: design 7.5 · usability 7.5 · creativity 7 · content 9 → overall 7.5.
Caps applied: aplico los criterios de una aplicación analítica; el mapa usa coordenadas y no necesita fotografías decorativas.
Top three problems (most visible first), each with the screenshot it shows in and the fix:
1. La primera revisión detectó IDs de tabla de 10 píxeles; los subí a 11 en escritorio, tablet y móvil.
2. El chequeo de contexto completo detectó contenido de indicadores mayor que sus 88 píxeles; reduje relleno y tamaño numérico.
3. El mapa ocupa una franja estrecha dentro de su campo horizontal; conservé proporciones geográficas para no ensanchar artificialmente Bogotá.

El inspector final terminó con cero fallos y una advertencia por densidad de texto pequeño.
Conservé 11–12 píxeles para ejes, notas, referencias y detalles de tabla.
Las cantidades principales usan 28 píxeles y la interpretación usa 40.
No detecté recortes de paneles ni desbordamiento horizontal en 45 combinaciones de selección y tamaño.
La tabla conserva desplazamiento vertical deliberado.

Revisé capturas de 1440, 768 y 390 píxeles de un navegador aislado.
También revisé una ubicación compartida, una estación padre y TransMiCable.
La composición de escritorio cierra en 1264 píxeles: 780 + 16 + 468.
Ambas columnas suman 576 de altura: 378 + 16 + 182 y 332 + 16 + 228.

El HTML usa SVG y CSS sin scripts externos en Power BI.
La vista previa usa JavaScript solamente para elegir estados DAX ya calculados.
La tabla de HTML y la tabla nativa de Power BI cumplen funciones distintas.
Configuré interacciones de filtro explícitas desde la tabla nativa hacia los visuales HTML.
La prueba del motor confirma los mismos resultados al filtrar su etiqueta que al filtrar stops.

El renderizado y la interacción reales dentro de Desktop permanecen pendientes.
No controlé ni capturé la pantalla del equipo.
