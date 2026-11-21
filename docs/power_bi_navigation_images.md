# Mi navegación y selección visual en Power BI

**Actualización:** 20 de noviembre de 2026.
La navegación entre los cuatro paneles ya funciona en la revisión del informe.

## Una acción para cada control

| Control | Acción | Alcance |
| --- | --- | --- |
| Menú lateral nativo | Cambio de panel. | Panorama, Programación, Red publicada y Revisión. |
| Tarjeta ilustrada | Filtro por componente mediante HTML Content. | Panorama; no sincroniza su selección entre páginas. |
| Desplegable de componente | Filtro por componente. | Sincronizado entre los cuatro paneles. |
| Desplegable de ruta | Filtro por etiqueta única de código e ID. | Sincronizado entre los cuatro paneles. |
| Fechas A y B | Elijo fechas para comparar. | Panorama y Programación. |

Cambiar de página no equivale a cambiar de componente.
Para ver las cinco tarjetas dejo el desplegable de componente en todos los componentes.
Los filtros de ruta y componente pueden combinarse; una selección vacía no indica un fallo del pipeline.

## Texto y acción dentro del mismo botón

Encontré etiquetas HTML que no coincidían con los botones transparentes superpuestos.
Los saltos de línea desplazaban los textos, pero no desplazaban las áreas de clic.
Sustituí esa composición por cuatro botones nativos con etiquetas propias y filas iguales en todas las páginas.
Cada botón ocupa 104 × 44 unidades del lienzo.
Conservo un solo nombre visible por destino y retiro Laboratorio, Agency y Control del menú principal.

El HTML del lateral conserva la marca y la nota inferior, sin nombres de páginas.
Un resguardo CSS oculta nav, lab-label, nav-lab y lab-links dentro del lateral.
Ese resguardo evita duplicados si reaparece contenido HTML de una versión anterior.

## Cómo reconozco la página actual

La página actual utiliza texto rojo oscuro #A7141D y fondo rojo suave #FBE4E5.
Las demás opciones muestran texto neutro y un cambio de fondo al pasar el cursor.
Defino los estados del botón explícitamente para que el tema no añada cuadros azules por defecto.
El destino y el texto pertenecen al mismo objeto nativo.
No necesito una medida DAX para recordar la página activa: cada página define su propio botón resaltado.

En Power BI Desktop pruebo la navegación con Ctrl + clic.
En modo lectura utilizo un clic.
La [documentación oficial de botones](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-buttons) explica esta diferencia.

## Los cinco componentes

Troncal usa la ilustración roja; Zonal (SITP), azul; Alimentación, verde.
Dual conserva su ilustración propia y TransMiCable muestra una cabina.
Agrupo por report_component para obtener cinco tarjetas aunque Zonal contenga varias agencias.
Los nombres e IDs publicados cambian entre snapshots; el componente es una clasificación de presentación.
No utilizo esa clasificación como clave física de relación ni como correspondencia contractual con operadores.

Las ilustraciones SVG son propias y no dependen de Image Grid ni de imágenes externas.
No representan flota disponible, ocupación ni posiciones de vehículos.
El [filtrado cruzado de HTML Content](https://html-content.com/docs/interactivity) gestiona la selección del visual.
El gráfico de referencia por componente conserva el alcance definido en su medida DAX.

## Qué comprobé y qué queda abierto

Validé 69 archivos PBIR, 16 botones con etiquetas nativas y un destino activo por menú.
Comprobé por MCP de lectura que las cuatro medidas del lateral ya no devuelven nombres de páginas ni Laboratorio.
La revisión del informe confirmó que la navegación funciona.
Las vistas previas del selector pasaron las cinco selecciones en 1440, 768 y 390 píxeles.
Esas pruebas no sustituyen la revisión completa del rendimiento y de todos los filtros combinados en Desktop.

El PBIP conserva las definiciones ejecutables; los .dax documentan las medidas.
Los HTML de vista previa utilizan JavaScript propio para recorrer resultados DAX precalculados.
HTML Content dentro de Power BI utiliza HTML, CSS y SVG; no reutiliza ese JavaScript.
El [estado actual](project_status.md) y el [cierre](power_bi_cierre_v1.md) concentran los pendientes vigentes.
