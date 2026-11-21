# Mi primer panel: Panorama de oferta

**Actualización del cierre — 20 de noviembre de 2026:** navegación nativa confirmada; cuatro paneles y cuatro Gold disponibles. [Estado vigente](project_status.md) y [menú y componentes](power_bi_navigation_images.md).

**Estado:** diseño revisado y aprobado; guardado en PBIP. Revisión del renderizado dentro de Desktop pendiente.

## Para quién lo construí

Lo preparé para una persona de planeación o gerencia que necesita orientarse antes de revisar una ruta.
Los roles son escenarios de portafolio; no corresponden a entrevistas con TransMilenio.

La pregunta principal es: **¿qué cambia en la programación publicada entre dos fechas y dónde se concentra esa diferencia?**
La acción siguiente consiste en elegir un componente o una ruta y abrir Programación.

## Qué muestra y qué responde

| Elemento | Pregunta | Cómo lo interpreto |
| --- | --- | --- |
| Rutas con programación | ¿Cuántas rutas tienen calendario habilitado en A? | Cuento claves de ruta distintas, conservando la identidad del feed. |
| Viajes sin frecuencias | ¿Cuántos viajes declara la programación sin usar plantillas de frecuencia? | No representan buses, pasajeros ni viajes realmente operados. |
| Plantillas por frecuencia | ¿Cuántas plantillas están activas en A? | Una plantilla no equivale a una salida individual. |
| Micrográficos | ¿Cómo cambia esa cantidad durante la semana de A? | Cada tarjeta usa su propia escala y siete días reales del calendario. |
| Lectura central | ¿Cuánto difieren A y B? | Diferencia absoluta y relativa; B es el denominador del porcentaje. |
| Mayor diferencia del contexto | ¿Qué componente aporta la mayor diferencia absoluta de la selección? | Describe un aporte numérico; no identifica causas operativas. |
| Rutas en ambas, solo A y solo B | ¿Cambia el conjunto de rutas con programación? | No representan aperturas o cierres físicos de rutas. |
| Mapa | ¿Qué ubicaciones del catálogo se relacionan con rutas programadas en A? | No garantiza visitas a cada punto ese día. |
| Perfil de cuatro semanas | ¿Qué patrón publica el calendario alrededor de A? | Son 28 días hasta el domingo de la semana analizada. |
| Ranking de rutas | ¿Qué tres rutas tienen la mayor diferencia absoluta? | Mantengo una sola unidad y muestro el signo de A menos B. |
| Puntos conectados | ¿Cómo difieren los cinco componentes? | Comparten escala; el gráfico conserva ruta y elimina solo componente como referencia. |

## Filtros e identidad

A es la fecha analizada. B es la fecha comparada.
Fecha de servicio y versión del feed representan conceptos diferentes.
La primera entrega utiliza el calendario de 2026 y el feed del 29 de septiembre de 2026.
Conservo versión, hash e ID en las relaciones y filtros de ámbito.
Las fechas y los filtros no mezclan identidades históricas.

## Reglas que evitan conclusiones incorrectas

- Comparo cantidades del mismo ámbito y la misma unidad.
- Cuando solo hay plantillas, las comparaciones usan plantillas explícitamente.
- No interpreto una caída de plantillas como caída de capacidad o aumento de espera.
- Con B igual a cero muestro cantidades y evito porcentajes indefinidos.
- Con una fecha ausente pido una selección; no la convierto en cero.
- El mapa cuenta ubicaciones relacionadas con coordenadas, sin sumar puntos repetidos por ruta.
- El puente ruta–ubicación corresponde al catálogo del snapshot, no a visitas diarias.
- No deduzco demanda, ocupación, puntualidad, cancelaciones ni déficit de flota.

## Ejemplo comprobado

Comparé el domingo 22 con el jueves 19 de noviembre de 2026.
Obtuve 789 frente a 863 rutas y 40.227 frente a 80.201 viajes sin frecuencias.
La diferencia de viajes es −49,8%.
Encontré 610 rutas comunes, 179 solo en A y 253 solo en B.
El mapa relaciona 7.834 ubicaciones con rutas programadas en A.

Esto es como revisar dos hojas del horario publicado.
Una hoja puede tener menos viajes porque corresponde a otro patrón de calendario.
Para revisar las horas y las ventanas concretas continúo en Programación.

[Abro el panel](../BI/imagenes/panorama/panorama_v2_preview.html).
[Consulto las medidas](../BI/medidas/panorama/README.md).
[Reviso el alcance técnico](../BI/imagenes/panorama/README.md).


## Paso a Programación

Añadí navegación nativa hacia Programación y grupos de filtros sincronizados en el PBIP.
El selector ahora distingue cada ruta por código e ID.
La [definición del segundo panel](power_bi_programacion_plan.md) profundiza en días, horas y ventanas publicadas.
La verificación de la navegación dentro de Desktop queda pendiente.
