# Mis medidas de agency

| Archivo | Medida | Resultado sin filtros |
| --- | --- | --- |
| `01_registros_de_agencia.dax` | Registros de agencia | 14 registros |
| `02_snapshots_cargados.dax` | Snapshots cargados | 2 snapshots |
| `03_tarjeta_agency_html.dax` | Tarjeta agency HTML | Texto HTML dinámico |

Las tres medidas pertenecen a `silver_gtfs_agency`.
Las dos medidas numéricas conservan la carpeta de presentación `Comprobación`.
La nueva medida utiliza la carpeta de presentación `Agency/HTML`.
Esta carpeta del repositorio organiza el código; la carpeta de presentación organiza el panel de campos de Power BI.

## Mi prueba

La página **Agency · HTML** del PBIP contiene la tarjeta y un filtro de versión.
Usé HTML Content Secure, identificado por su GUID de AppSource.
El reporte declara ese visual en `publicCustomVisuals`; Desktop deberá obtenerlo de AppSource al abrirlo.
El componente utiliza HTML y estilos internos, sin JavaScript ni recursos externos.
La tarjeta recibe los filtros. Sus bloques internos no envían filtros a otros visuales.

Comprobé la expresión con el motor DAX del modelo abierto:

| Filtro | Registros | Snapshots |
| --- | ---: | ---: |
| Sin filtro de versión | 14 | 2 |
| 2025-10-28 | 7 | 1 |
| 2026-09-29 | 7 | 1 |
| Versión sin registros | 0 | 0 |

Mantengo versión y SHA-256 para identificar cada snapshot.
Con varias identidades seleccionadas, evito mostrar una lista mezclada de IDs y nombres.
Con un snapshot seleccionado, muestro los nombres e IDs de ese snapshot.
No presento estos registros como empresas legales, contratos o vehículos.

## Cómo abrir la prueba

1. Vuelvo a abrir `BI/GFTS_BI.pbip` para cargar los cambios externos.
2. Evito guardar una sesión anterior encima de los archivos modificados externamente.
3. Abro **Agency · HTML**.
4. Selecciono una versión en el filtro lateral y compruebo siete registros.
5. Quito el filtro y compruebo catorce registros y dos snapshots.

Si Desktop indica que falta el visual, agrego **HTML Content Secure** desde AppSource.
No abro el antiguo `.pbix` para revisar esta prueba: el cambio está en el proyecto `.pbip`.
Guardé una vista previa HTML con los resultados reales en `BI/imagenes/agency/`.
Esa vista previa es estática; el filtro interactivo pertenece al reporte de Power BI.

Validé los archivos de página, visuales y registro de AppSource contra sus esquemas JSON públicos.
Comprobé que las cuatro salidas HTML tienen etiquetas equilibradas y no incluyen scripts ni recursos externos.
La expresión DAX está comprobada. La verificación del renderizado dentro de Desktop queda pendiente de abrir el PBIP.
