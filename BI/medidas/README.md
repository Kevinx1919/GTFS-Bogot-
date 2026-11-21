# Mis medidas de Power BI

## Estado vigente — 20 de noviembre de 2026

Trabajo con cuatro tablas Gold importadas y cuatro paneles: Panorama, Programación, Red publicada y Revisión.
La navegación usa botones nativos con texto propio, estado activo rojo y efecto al pasar el cursor.
Retiré Laboratorio y sus accesos del menú principal.
Las tarjetas ilustradas filtran Panorama; los desplegables conservan la sincronización entre páginas.
La navegación ya funciona; la revisión integral del informe y su actualización completa siguen pendientes.
[Estado general](../../docs/project_status.md) y [navegación](../../docs/power_bi_navigation_images.md).

## Recorrido y referencias de implementación

Organizo las medidas por entidad: `medidas/<entidad>/`.
Empiezo por [agency](agency/README.md).
Crearé las carpetas de las demás entidades cuando incorpore sus medidas.

Guardo una medida completa por archivo `.dax`.
Mantengo los cálculos numéricos separados de la presentación HTML.
Los archivos documentan y permiten reproducir las medidas; Power BI no los importa automáticamente.
El modelo ejecutable del proyecto reside en `GFTS_BI.SemanticModel/definition/`.
Sincronizaré ambas representaciones cuando cambie una medida.

## Catálogos conectados

Añadí [routes](routes/README.md), [trips](trips/README.md) y [frequencies](frequencies/README.md).
Las medidas numéricas ya reciben filtros por las nuevas claves del modelo.

## Cobertura Gold incorporada — 19 de noviembre de 2026

Verifiqué e importé gold_gtfs_trip_coverage para 2026.
Añadí su relación por trip_key desde trips y comprobé los filtros de agencia y snapshot.
Las [medidas de cobertura](trip_coverage/README.md) documentan diez medidas, incluidos porcentajes y estado de cobertura.
El diagrama Consumo GTFS contiene ahora doce tablas de negocio; la definición completa conserva diecinueve tablas y diecisiete relaciones, incluidos los objetos automáticos de fechas.
