# Mi cuarto panel: Revisión de información

> **Estado vigente — 20 de noviembre de 2026:** las cuatro Gold de 2026 están publicadas e importadas y los cuatro paneles están implementados. La navegación nativa funciona; la revisión integral y la actualización completa siguen pendientes. [Estado actual](project_status.md).

## Registro de diseño e implementación

Conservo a continuación las decisiones y comprobaciones de cada etapa. Los pendientes de esas fechas describen su momento; el estado vigente anterior los sustituye.

**Estado:** implementación guardada y comprobada en DAX y la vista previa. Desktop permanece pendiente.

Quiero responder qué viajes necesitan aclaración y cómo limitan los indicadores publicados.
Utilizo cobertura y extremos horarios Gold del catálogo 2026.
Mantengo componente y ruta sincronizados con las otras páginas.
No aplico A ni B a estos conteos de catálogo.

## Recorrido

Primero leo los viajes evaluados y las cantidades excluidas del perfil horario.
Después selecciono un motivo y localizo las rutas con más casos.
Finalmente consulto un viaje en la tabla nativa y leo su explicación.
La selección de una fila solo cambia la ficha; no altera los totales del contexto.

## Preguntas y cálculos

| Bloque | Pregunta | Cálculo |
| --- | --- | --- |
| Indicadores | ¿Qué dimensión tienen estos casos? | Cantidades del contexto de componente/ruta antes del filtro de motivo. |
| Clasificación | ¿Por qué quedan fuera del perfil horario? | Categorías excluyentes de timing_status y denominador de viajes evaluados. |
| Rutas | ¿Dónde concentro la revisión? | Casos del motivo por ruta, porcentaje y denominador completo de cada ruta. |
| Tabla nativa | ¿Qué viaje puedo investigar? | Viajes con timing_status distinto de eligible, filtrados por motivo. |
| Ficha | ¿Qué significa y qué reviso después? | ID, ruta, visitas, ventanas y explicación correspondiente al motivo. |

El motivo filtra el ranking y el detalle.
La clasificación general conserva el contexto anterior al motivo para evitar perder el denominador.
El ranking muestra hasta cinco rutas; una barra usa longitud relativa al máximo, no porcentaje del sistema.

## Reglas

Conservo claves por versión, hash e ID.
No sumo cobertura y elegibilidad como si fueran problemas independientes.
Una plantilla utiliza ventanas de frecuencia y no constituye por sí misma un dato inválido.
Varias visitas o extremos elegibles tampoco certifican un recorrido completo.
Un cero necesita fuentes disponibles; ausencia de Gold permanece sin evaluación.
No asigno prioridades contractuales ni umbrales de riesgo inventados.

## Resultado comprobado

Concilié 181.060 viajes, 180.246 elegibles y 814 excluidos del perfil horario.
Los excluidos publicados son 739 sin visitas, 61 con una visita y 14 plantillas.
Contrasté cobertura, fuente ausente, fechas y la consulta de los 814 viajes del detalle nativo.
Comprobé setenta contextos y 210 combinaciones de selección y tamaño.
Guardé veinte medidas, dos columnas de presentación y la página PBIP.
Conservé las 23 tablas y 21 relaciones físicas.
La selección de fila solo filtra la ficha; los demás visuales conservan el contexto.

[Definición de negocio](power_bi_revision_negocio.md).
[Vista previa y evidencia](../BI/imagenes/revision_informacion/README.md).
