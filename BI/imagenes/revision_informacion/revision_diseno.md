# Revisión del diseño de mi cuarto panel

Conservé la identidad aprobada de las otras páginas: rojo #DD212C, amarillo #FFC928 y superficies neutras.
Usé un ranking para localizar rutas y una clasificación oscura para conservar el denominador.
La ficha amarilla explica el siguiente paso del viaje consultado.

ROUND 2
Seen in one second: rutas con casos y 814 viajes fuera del perfil horario.
Idea (one sentence): paso del motivo a una ruta y un viaje sin confundir exclusión analítica con fallo operativo.
Live thing: componente, ruta y motivo cambian resultados reales; el detalle consulta un viaje sin alterar el contexto.
Layout words by section: navegación=columna / filtros=fila / cantidades=franja / rutas=ranking / clasificación=desglose / viajes=tabla / ficha=acción.
Scores: design 7.5 · usability 7.5 · creativity 7 · content 9 → overall 7.5.
Caps applied: aplico criterios de aplicación analítica; las cantidades y el detalle sustituyen fotografías sin función analítica.
Top three problems (most visible first), each with the screenshot it shows in and the fix:
1. La ficha inicial deja espacio antes de consultar un viaje; reservo ese espacio para ID, ruta, visitas y ventanas.
2. Los textos secundarios son densos; mantengo 11–12 píxeles en notas y tablas y cantidades principales de 28–40 píxeles.
3. El amarillo claro del botón genera una advertencia de paleta; conservo la referencia amarilla solicitada para la identidad de TransMilenio.

El inspector terminó sin fallos y con esas tres advertencias.
Revisé escritorio, tablet y móvil en capturas de un navegador aislado.
También revisé TransMiCable, una ruta con casos y una selección sin casos.
Las 210 combinaciones de contexto y tamaño no recortaron paneles ni generaron desbordamiento horizontal.
La tabla del prototipo utiliza desplazamiento deliberado para conservar los IDs completos.

Corregí los conteos vacíos del encabezado para mostrar ceros explícitos.
Ajusté las leyendas de visitas y ventanas para conservar una lectura natural con cantidades de uno.
Contrasté tres fichas finales con las salidas del motor.

La composición de escritorio cierra en 1264 píxeles: 780 + 16 + 468.
Ambas columnas suman 576 de alto: 286 + 16 + 274 y 332 + 16 + 228.
Mantengo selección y navegación nativas dentro de Power BI.
La vista previa usa JavaScript únicamente para elegir resultados DAX y mostrar la ficha de ejemplo.
No incorporé scripts dentro de los visuales HTML del informe.

Conservo pendiente la revisión real de Desktop.
La comprobación del navegador no sustituye el renderizado de HTML Content ni la interacción nativa de la tabla.
No controlé ni capturé la pantalla del equipo.
