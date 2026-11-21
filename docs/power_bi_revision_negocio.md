# Qué responde Revisión de información y cómo lo calculo

**Actualización del cierre — 20 de noviembre de 2026:** navegación nativa confirmada; cuatro paneles y cuatro Gold disponibles. [Estado vigente](project_status.md) y [menú y componentes](power_bi_navigation_images.md).

**Estado:** cuarto panel implementado; motor y vista previa comprobados.
La revisión dentro de Desktop sigue pendiente.

Quiero responder: **¿qué viajes necesitan aclaración y cómo limitan las preguntas del informe?**
Trabajo con el catálogo 2026, sin convertir estos casos en viajes activos de una fecha concreta.

| Pregunta | Qué muestro | Cómo lo calculo |
| --- | --- | --- |
| ¿Cuál es el contexto evaluado? | Viajes y cantidades por clasificación. | Cuento viajes Gold del componente y ruta antes del motivo elegido. |
| ¿Cuántos viajes no relacionan visitas? | Cantidad y porcentaje. | no_visits entre todos los evaluados del contexto; contraste con cobertura Gold. |
| ¿Cuántos viajes tienen una sola visita? | Cantidad separada. | one_visit del mismo contexto. |
| ¿Por qué algunos viajes quedan fuera del perfil horario? | Categorías y denominador. | timing_status conserva motivos excluyentes y su precedencia. |
| ¿En qué rutas concentro la revisión? | Hasta cinco rutas, cantidad y proporción. | Casos del motivo por ruta; cada porcentaje utiliza todos los viajes de esa ruta. |
| ¿Qué viaje explica el caso? | Tabla y ficha de revisión. | Selecciono un trip_key del mismo snapshot y consulto ID, visitas, ventanas y motivo. |

## Cómo leo las cantidades

El catálogo evaluado tiene 181.060 viajes.
Son 180.246 elegibles y 814 fuera del perfil horario.
Los 814 representan aproximadamente el 0,45 % del total.

Esos excluidos se distribuyen en 739 sin visitas, 61 con una visita y 14 plantillas.
Las categorías no se superponen.
No sumo nuevamente las cantidades de cobertura como si describieran otros viajes.
En esta publicación no aparecen extremos ausentes ni invertidos.
Mantengo esos motivos en la explicación porque forman parte del contrato.

Esto es como revisar itinerarios antes de compararlos.
Algunos carecen de lista de visitas; otros publican una visita; las plantillas requieren sus ventanas.
Cada caso limita una pregunta distinta.

## Cómo conservo el denominador

Primero selecciono componente y ruta.
Los indicadores superiores y la clasificación muestran ese contexto completo.
Después puedo elegir un motivo para filtrar el ranking y la tabla.
Ese motivo no cambia el total usado como denominador.

Por ejemplo, Sin visitas devuelve 739 casos entre 181.060 evaluados.
No lo convierto en 739 entre 739.
La cifra superior de excluidos sigue incluyendo los demás motivos del contexto.

## Por qué muestro cantidad y porcentaje por ruta

TC30, ID 10571, tiene 89 casos entre 318 viajes del catálogo.
8-10, ID 10575, tiene 77 casos entre 213 viajes.
TC30 tiene más casos; 8-10 tiene una proporción mayor.
El ranking ordena por cantidad y conserva ambos valores para interpretar la diferencia.

No asigno automáticamente mayor riesgo ni incumplimiento contractual a ninguna ruta.
No tengo contratos ni operación observada para demostrar esas conclusiones.
Las barras expresan longitud relativa al máximo del ranking, no participación en todo el sistema.

## Qué significa cada motivo

- Sin visitas: conservo el viaje declarado, pero no encuentro visitas Silver relacionadas.
- Una visita: conservo la fila; no deduzco un recorrido entre dos ubicaciones.
- Plantilla por frecuencia: consulto sus ventanas; no la cuento como una salida individual.
- Sin extremos horarios: conservo la ausencia; no sustituyo el extremo por otra hora intermedia.
- Extremos invertidos: reviso secuencia y publicación; no corrijo silenciosamente las horas.
- Elegible: cumple las reglas del perfil; no certifica puntualidad ni recorrido completo.

TransMiCable tiene catorce plantillas en el catálogo.
Todas quedan fuera de este perfil de extremos de viajes individuales.
Eso no significa que TransMiCable tenga un 100 % de datos inválidos.
Su programación requiere el tratamiento de frecuencias explicado en Programación.

## Cómo investigo un viaje

Selecciono una fila de la tabla nativa.
Solo cambia la ficha Siguiente revisión.
La ficha muestra ID, ruta, visitas, ventanas y una explicación del motivo.
Los totales, el ranking y los selectores conservan su contexto.

Las claves incluyen versión, SHA-256 e ID.
Las etiquetas de presentación no sustituyen esa identidad histórica.
La vista previa permite consultar el primer caso de cada selección.
La tabla del PBIP permite consultar cualquier fila de su contexto.

## Qué significan los ceros

Un componente puede tener cero excluidos con estas reglas.
Eso no certifica calidad completa ni confirma la ejecución del servicio.
Un motivo puede no tener casos dentro de una ruta.
La página conserva ese cero y explica la ausencia de filas.

Si falta alguna fuente Gold del snapshot, muestro ausencia de evaluación.
No convierto una fuente ausente en cero casos.
Las fechas A y B no filtran este catálogo.

## Evidencia y siguiente paso

Contrasté cobertura y clasificación horaria.
Comprobé setenta contextos DAX y los 814 viajes de la consulta nativa.
Concilié categorías, denominadores y porcentajes por ruta.
La vista previa pasó 210 combinaciones de selección y tamaño sin recortes de paneles.
La navegación y el renderizado reales dentro de Desktop requieren su comprobación propia.

Con esta implementación ya existen las cuatro páginas previstas.
El siguiente paso es revisar el informe completo y comprobar su procedimiento de actualización.
No doy por terminada la entrega solo por completar las páginas.

[Abro Revisión de información](../BI/imagenes/revision_informacion/revision_preview.html).
[Consulto las medidas](../BI/medidas/revision_informacion/README.md).
[Reviso el cierre de la primera versión](power_bi_cierre_v1.md).
