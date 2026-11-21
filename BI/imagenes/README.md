# Mis recursos visuales de Power BI

## Estado vigente — 20 de noviembre de 2026

Trabajo con cuatro tablas Gold importadas y cuatro paneles: Panorama, Programación, Red publicada y Revisión.
La navegación usa botones nativos con texto propio, estado activo rojo y efecto al pasar el cursor.
Retiré Laboratorio y sus accesos del menú principal.
Las tarjetas ilustradas filtran Panorama; los desplegables conservan la sincronización entre páginas.
La navegación ya funciona; la revisión integral del informe y su actualización completa siguen pendientes.
[Estado general](../../docs/project_status.md) y [navegación](../../docs/power_bi_navigation_images.md).

## Recorrido y referencias de implementación

Esta carpeta conserva recursos para gráficos HTML y las imágenes que los acompañan.
Puedo guardar fuentes HTML/CSS, SVG, imágenes y notas de integración.
Mantendré nombres descriptivos y recursos pequeños, sin credenciales ni datos privados.

Un gráfico nativo de Power BI usa sus visuales y medidas DAX.
Un gráfico HTML requiere un visual personalizado compatible, como un renderizador HTML.
Un archivo HTML autónomo no se convierte automáticamente en un gráfico nativo.
No asumiré que ese visual puede ejecutar JavaScript; revisaré sus restricciones antes de integrarlo.

La carpeta BI ya existe en Windows; utilizo BI/imagenes para mantener una sola ubicación.
El archivo PBIX queda fuera de los recursos de esta carpeta.

## Páginas actuales

- [Panorama de oferta](panorama/panorama_v2_preview.html): compara oferta publicada entre dos fechas.
- [Programación](programacion/programacion_preview.html): explora calendario, primeras salidas y ventanas.
- [Red publicada](red_publicada/red_publicada_preview.html): consulta ubicaciones, padres y relaciones por ID.

Las vistas previas usan resultados DAX reales precalculados.
El proyecto PBIP conserva los filtros y la navegación nativa del informe.
[Revisión de información](revision_informacion/revision_preview.html) completa las cuatro páginas implementadas.
La revisión real dentro de Desktop permanece pendiente.
