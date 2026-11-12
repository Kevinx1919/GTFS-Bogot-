# Mi recorrido del Job Silver

Actualicé las dos vistas el 12 de noviembre de 2026.

1. [Orden del Job](recorrido_job.html): nueve tareas, parámetros por snapshot y un ejemplo de recuperación.
2. [Una iteración](iteracion_snapshot.html): entradas, validación, cuarentena, publicación, auditoría y errores.

## Cómo sigo el Job

Las flechas avanzan hacia abajo y a la derecha:

```text
agency → routes → stops → calendar → calendar_dates
→ service_dates → shape_points → trips → frequencies
```

Cada bloque representa un For each. Las nueve tareas utilizan notebook 10.
Ocho tareas fuente contemplan 2025 y 2026. Service_dates calcula solamente el horizonte 2026.
Cada bucle usa concurrencia 1. La plantilla mantiene un reintento con un intervalo mínimo de 60 segundos.

El orden también protege la auditoría compartida. Una dependencia entre tareas no implica siempre una relación entre tablas.
Por ejemplo, stops espera a routes en el Job, pero valida su propia jerarquía.
Routes sí consulta agency. Frequencies sí consulta trips.

La rama de errores ejemplifica un fallo de trips. Frequencies espera mientras su dependencia no termina correctamente.
Las otras etapas conservan la misma política de reintentos.
Abro el error de la iteración, reviso la causa y reparo las tareas afectadas.

## Qué ocurre dentro de una iteración

Las entidades fuente leen Bronze y el encabezado TXT del mismo snapshot.
El procesador añade las dependencias requeridas por su contrato.
Service_dates recibe calendarios Silver y una ventana explícita; no simula otro TXT.

La vista interior representa mode=publish. Mode=validate devuelve el resumen antes de escribir auditoría, cuarentena o Silver.
Un rechazo conserva originales y motivos. El escritor bloquea la publicación parcial del snapshot.
Un error anterior a la preparación puede quedar solamente en el Job.

Los commits de auditoría, cuarentena y Silver son independientes.
Un fallo posterior a la escritura puede dejar silver_committed=true. Reviso ese estado antes de reintentar.

## Estado y evidencia

Las nueve entidades tienen despliegue funcional confirmado durante el desarrollo.
El [cierre de frequencies](../../silver_execution.md#cierre-de-la-ejecución-de-frequencies) conserva el alcance de esa confirmación.
Los diagramas enlazan el código de 34e3769e1d6eaebca950161f4f47f0bf38f7bc40. No muestran telemetría ni verifican cambios externos de la interfaz.
Las listas de snapshots siguen siendo manuales. El planificador automático permanece pendiente 8b.

Las fuentes son [el recorrido](recorrido_job.workflow.json) y [la iteración](iteracion_snapshot.workflow.json).
Ambas vistas pasaron controles automáticos de estructura, referencias, HTML y navegador.
El [resumen público](verificacion.json) identifica los hashes y las medidas de navegador de esta revisión.
No hice una nueva revisión de capturas. Los recibos detallados permanecen fuera de Git.
Genero fuera de OneDrive y copio los HTML comprobados sin cambiar sus bytes.
