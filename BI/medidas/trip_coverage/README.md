# Mis medidas de cobertura Gold

**Estado:** publicadas en el modelo local de Power BI y comprobadas con DAX el 19 de noviembre de 2026.
La tabla de consumo contiene una fila por viaje declarado dentro de un snapshot.
Importé once columnas de negocio y añadí dos claves calculadas de consumo.
Conservo la auditoría completa de publicación en Databricks.

## Medidas

| Medida | Definición y límite |
| --- | --- |
| Viajes evaluados | Viajes declarados con evaluación Gold en el contexto. BLANK indica ausencia de filas Gold; no equivale a cero viajes declarados. |
| Viajes sin visitas | Viajes evaluados sin visitas publicadas. Conserva filtros de snapshot, agencia, ruta y contexto de programación. BLANK si falta cobertura Gold. |
| Viajes con una visita | Viajes evaluados con una visita publicada; no demuestra recorrido entre ubicaciones. Conserva filtros de snapshot, agencia, ruta y contexto de programación. BLANK si falta cobertura Gold. |
| Viajes con varias visitas | Viajes evaluados con dos o más visitas. No certifica recorrido completo. Conserva filtros de snapshot, agencia, ruta y contexto de programación. BLANK si falta cobertura Gold. |
| Porcentaje de viajes sin visitas | Viajes sin visitas entre todos los viajes evaluados del mismo contexto. Retira solo el filtro de categoría del denominador; conserva snapshot/agencia/ruta/contexto de programación. |
| Visitas publicadas | Visitas publicadas en los viajes evaluados del contexto. No cuenta usuarios ni vehículos. |
| Visitas con horas completas | Visitas con arrival y departure presentes. Mide presencia de horas, no exactitud ni puntualidad. |
| Porcentaje de visitas con horas completas | Proporción de visitas con llegada y salida presentes. Denominador de visitas, no viajes. BLANK si no hay visitas. |
| Ventanas evaluadas | Ventanas publicadas agregadas por viaje y snapshot. No representa salidas exactas ni operación observada. |
| Estado cobertura Gold | Indica qué versiones sostienen la evaluación y avisa de cobertura parcial frente al catálogo de viajes del contexto. |

Cada archivo `.dax` conserva una medida completa.
La definición ejecutable también reside en `GFTS_BI.SemanticModel/definition/tables/gold_gtfs_trip_coverage.tmdl`.
Las medidas de cobertura no sustituyen el conteo histórico de viajes declarados de Silver.

## Relación

```text
Snapshot → Agency → Routes → Trips → Gold trip_coverage
```

Relacioné Gold mediante trip_key, conservando versión, hash e ID.
La dirección del filtro permanece desde trips hacia Gold.
No añadí relaciones directas adicionales con route o snapshot para evitar caminos ambiguos.
Comprobé 181060 filas y 181060 claves únicas en Gold importado.

## Resultados de aceptación

| Contexto | Evaluados | Sin visitas | Una visita | Varias visitas | Porcentaje sin visitas |
| --- | ---: | ---: | ---: | ---: | ---: |
| Snapshot 2026 | 181060 | 739 | 61 | 180260 | 0,4081519938 % |
| Troncal 2026 | 40599 | 0 | 0 | 40599 | 0 % |
| TransMiCable 2026 | 14 | 0 | 0 | 14 | 0 % |
| Snapshot 2025 | BLANK | BLANK | BLANK | BLANK | BLANK |

Las visitas publicadas y con horas completas suman 9408893.
Las ventanas evaluadas suman catorce.
Una pareja completa de horas prueba su presencia, no exactitud ni puntualidad.

Comprobé que seleccionar coverage_status=sin_visitas conserva el porcentaje 739/181060.
No convierte el denominador en 739 ni produce un 100 % incorrecto.
Cuando no hay visitas, la proporción de horas completas devuelve BLANK.

## Alcance visible

Gold solo está publicado para 2026-09-29.
Para 2025 muestro ausencia de cobertura, sin convertirla en cero casos.
Si el catálogo incluye ambos snapshots, Estado cobertura Gold indica cobertura parcial.
Las tarjetas deben acompañar sus cifras con ese estado o con el snapshot seleccionado.
No presentaré estas cifras como viajes operados, vehículos o cancelaciones.
