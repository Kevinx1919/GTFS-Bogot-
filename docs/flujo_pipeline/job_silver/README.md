# Mi recorrido del Job Silver

Ya preparé dos vistas interactivas. Las abro en el navegador y sigo este orden:

1. [Orden del Job](recorrido_job.html): Run now, agency, routes y recuperación cuando una etapa falla.
2. [Una iteración por snapshot](iteracion_snapshot.html): lectura, reglas, cuarentena, decisión, publicación y auditoría final.

## Cómo las exploro

Empiezo por la fila superior del mapa del Job. La conexión All succeeded explica por qué routes espera a agency. Abro un bloque para consultar sus referencias al código; puedo usar RUTA para explorar un recorrido y la búsqueda para localizar un componente. Las ramas inferiores describen errores y recuperación.

Después abro la vista de una iteración. Sigo el camino hasta publicar y comparo las salidas Error previo, Snapshot rechazado y Fallo de publicación. Las tarjetas inferiores explican los detalles que no caben en el dibujo. La interfaz está en español; conservo los nombres técnicos que aparecen en el código.

## Qué está representado

Las vistas documentan el código y la definición del Job en el commit 598bc0de6b65b25ffa2ef13b628ab0966fd41dcd. Representan mode=publish y listas versionadas para 2025 y 2026. Las animaciones explican relaciones del diagrama; no muestran telemetría ni verifican la configuración actual de la interfaz de Databricks.

Ambos For each llaman al notebook 10. El pipeline selecciona reglas por entidad y snapshot; routes exige agency_v1 del mismo snapshot. Si hay rechazos no publico un subconjunto. Un fallo posterior a la escritura puede dejar silver_committed=true y requiere revisar el intento. No represento mode=validate ni la ingesta Bronze en estos recorridos.

## Fuentes y verificación

Conservo [la fuente del mapa](recorrido_job.workflow.json) y [la fuente de la iteración](iteracion_snapshot.workflow.json), con referencias de archivos y líneas vinculadas al commit. Los contratos y procedimientos completos siguen en la [guía Silver](../../silver_execution.md) y el [runbook](../../notebook_runbook.md).

Ambas vistas pasaron los controles de Archify, incluidos los de navegador. Revisé capturas en claro y oscuro a 1440×900 y 2048×1320. El [resumen público](verificacion.json) registra los hashes, el commit y el alcance de estas comprobaciones; los recibos completos y capturas locales quedan fuera de Git.

OneDrive impidió restaurar un archivo de control al reemplazar una versión durante el primer render. Recuperé la evidencia previa y generé las versiones finales en una carpeta temporal local. Copié los HTML comprobados y verifiqué igualdad de hashes. Para regenerar usaré una carpeta temporal fuera de OneDrive, las fuentes de esta carpeta y el repositorio como repo-root; después copiaré los resultados comprobados. No traslado recibos de Archify como si hubieran sido emitidos para otra ruta: el resumen público distingue la copia final de la ubicación de validación.

## Qué sigue

Ya revisé la interactividad y los enlaces de este recorrido. Puedo continuar con el [mapa del lakehouse](../mapa_lakehouse/README.md) y el [modelo GTFS](../modelo_gtfs/README.md), que crecerá con las demás entidades. Conservo la documentación visual en el repositorio; todavía no fue publicada en un sitio web.
