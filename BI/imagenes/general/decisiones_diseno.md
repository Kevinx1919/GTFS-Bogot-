# Mi rediseño de General

Retomé el boceto original y las referencias de paneles con una ficha central del objeto analizado.
Elegí General para explorar componentes; no añadí otra página que repita sus cifras.
La pregunta principal sigue siendo qué oferta publica cada componente y qué casos necesitan revisión.

Conservé framed-sheet, seed 218730137, y Segoe UI.
Cambié la paleta y la jerarquía para seguir la petición de rojo y amarillo del bus.
La firma visual es la ficha del transporte: escena de integración, bus o cabina según el contexto.
Usé ilustraciones vectoriales propias con recursos incrustados.
Conservé el menú sobre un fondo neutral para que el color destaque en la ficha y en los gráficos.
El anillo amarillo representa varias visitas; el rojo identifica casos sin visitas.
El gris representa una visita; las etiquetas explican cada categoría sin depender solo del color.

La cuadrícula cierra: 1440 = 176 + 24 + 1216 + 24.
La fila central cierra: 1216 = 220 + 16 + 588 + 16 + 376.
La fila inferior cierra: 1216 = 588 + 16 + 612.
Usé alturas explícitas para evitar el crecimiento intrínseco dentro del iframe del visual.
Conservé 900 píxeles de altura en la página Power BI.

El primer rediseño tenía etiquetas pequeñas y bloques que crecían sobre la fila siguiente.
Corregí las alturas, aumenté etiquetas y mostré el denominador del anillo.
La segunda revisión eliminó los solapamientos y dejó una advertencia de texto pequeño en móvil.
Aumenté también los textos principales del diseño móvil antes de la revisión final.
Las comparaciones antes/después y las capturas pertenecen a Chrome aislado, no al escritorio personal.

No inventé tendencias, metas, coordenadas ni indicadores de operación.
La vista previa usa 31 resultados DAX reales.
Las páginas futuras conservan la etiqueta En preparación.
El renderizado final y la selección cruzada dentro de Desktop requieren reabrir el PBIP.

## Resultado final

El inspector y el linter terminaron con cero fallos y cero advertencias.
Comprobé escritorio, tableta y móvil en un navegador aislado.
La página pasó selección por componente, selección por teclado, rutas y estados de 2025.
Eliminé el desbordamiento vertical de la cobertura en la vista previa de tableta y móvil.
Las comprobaciones numéricas del modelo conciliaron sin diferencias.
