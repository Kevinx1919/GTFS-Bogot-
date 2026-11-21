# Mi comprobación de acceso a demanda y GTFS-Realtime

**Fecha local:** 19 de noviembre de 2026, America/Bogota.
**Capturas UTC:** 20 de noviembre de 2026, aproximadamente 00:11–00:14.
**Resultado:** no conseguí descargar un archivo de datos válido en esta comprobación.
No publiqué tablas ni modifiqué el pipeline o el modelo BI.

## Qué quería comprobar

Quería distinguir la existencia de un catálogo de la posibilidad real de descargar sus archivos.
Consulté los recursos públicos sin credenciales.
Probé una muestra pequeña de TransMiCable para evitar una descarga masiva de Zonal.

| Recurso | Prueba realizada | Resultado desde este entorno |
| --- | --- | --- |
| Portal de validaciones diarias | GET directo de la página. | HTTP 429 Too Many Requests. |
| Portal de validaciones mensuales | GET directo de la página. | HTTP 429 Too Many Requests. |
| validacionCable20261116.zip | GET de un enlace publicado, con límite de lectura de 16 MiB. | HTTP 429; no recibí un ZIP válido. |
| Portal actual GTFS | GET directo de la página. | HTTP 200 con aviso de mantenimiento; no equivale a un feed disponible. |
| Portal anterior GTFS | GET directo. | HTTP 500 Internal Server Error. |
| Catálogo alternativo Bogotá | API package_show del conjunto mensual. | HTTP 200, success=true; pude consultar metadatos. |
| Almacenamiento enlazado por ese catálogo | GET de la URL publicada en sus recursos. | HTTP 403 Forbidden. |

Las respuestas 429 no incluyeron Retry-After en los intentos registrados.
No repetí automáticamente las solicitudes rechazadas ni probé credenciales o rutas alternativas dentro del almacenamiento restringido.
No desactivé TLS ni intenté eludir controles del proveedor.

## Qué información sí encontré

La consulta web del listado de Cable muestra archivos diarios hasta el 17 de noviembre de 2026.
El listado anuncia validacionCable20261116.zip con 584,1 KiB.
Zonal anuncia archivos diarios más grandes; el del 17 de noviembre figura con 125,8 MiB.
Esos tamaños proceden del listado consultado, no de archivos descargados.
El acceso directo local devolvió 429, por lo que no confirmé contenidos, filas ni esquema real.

El listado de Cable declara licencia CC-BY 4.0.
Conservo esa referencia como metadata del portal; no inspeccioné términos incrustados en el ZIP.

El catálogo de Bogotá apunta a una página HTML en Google Cloud Storage.
Uno de sus recursos utiliza la etiqueta XLSX, pero su URL corresponde a la página HTML.
No trato esa etiqueta como prueba de un Excel descargable.
La respuesta directa de esa URL fue 403.

## Qué significa para el proyecto

La prueba inicial ya registraba errores 500 en los endpoints antiguos de GTFS-Realtime.
La comprobación actual conserva ese resultado y encuentra el portal nuevo en mantenimiento.
No puedo afirmar que la fuente operativa haya vuelto a funcionar.

Las validaciones tienen publicaciones anunciadas, pero falta confirmar un canal de descarga utilizable.
El 429 identifica una solicitud limitada; no demuestra que el archivo no exista.
Tampoco permite concluir si el límite depende de la IP, del cliente o de una condición temporal.
El 403 del enlace de almacenamiento requiere aclarar acceso con el proveedor; no presupongo que necesite una API key.

Conservo el cierre estático del proyecto y registro esta integración como ampliación pendiente de acceso.
Una conexión de Databricks o Power BI no resuelve por sí sola el rechazo del servidor de origen.

## Próximo paso viable

Puedo probar la descarga normal del archivo pequeño desde el navegador habitual del equipo.
Esa descarga manual no está comprobada en esta revisión.
Si consigo el archivo, conservaré el original con URL, fecha UTC y SHA-256.
Después comprobaré firma ZIP, integridad CRC, nombres internos, encabezados y cantidad de filas.
La descarga manual permitiría un piloto; no demostraría que la extracción automática está resuelta.

Para automatizar necesitaré un enlace público estable o una aclaración de acceso del proveedor.
Si recibo un límite temporal, respetaré el plazo indicado y usaré reintentos acotados.
GTFS-Realtime seguirá condicionado a la disponibilidad efectiva y frescura de sus mensajes.

## Evidencia y referencias

Mi corrida local tiene run_id=3b830a61-92c3-4bf0-b554-dacf26377f8e.
Conservé el manifiesto y las respuestas de prueba fuera del repositorio.
Solo guardé el HTML de GTFS que respondió correctamente; no lo registré como archivo de datos.
No guardé cuerpos de errores como snapshots Raw ni descargué registros de tarjetas.

- [Validaciones diarias](https://validaciones.datosabiertos.transmilenio.gov.co/validaciones_diarias.html).
- [Listado de Cable](https://validaciones.datosabiertos.transmilenio.gov.co/ValidacionCable.html).
- [Archivo pequeño probado](https://validaciones.datosabiertos.transmilenio.gov.co/ValidacionCable/validacionCable20261116.zip).
- [Listado Zonal](https://validaciones.datosabiertos.transmilenio.gov.co/ValidacionZonal.html).
- [Validaciones mensuales](https://validaciones.datosabiertos.transmilenio.gov.co/validaciones_mensuales.html).
- [Portal actual GTFS](https://gtfs.transmilenio.gov.co/).
- [Portal anterior GTFS](https://gis.transmilenio.gov.co/gtfs/).
- [API del catálogo mensual de Bogotá](https://datosabiertos.bogota.gov.co/api/3/action/package_show?id=validaciones-mensuales-del-sitp-por-franja-horaria).
- [Página de almacenamiento publicada por el catálogo](https://storage.googleapis.com/validaciones_tmsa/validaciones_mensuales.html?).
- [Estrategia de fuentes](source_strategy.md).
