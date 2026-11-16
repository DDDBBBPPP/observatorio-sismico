# Modelo conceptual, lógico y físico

## Conceptual

Una ejecución obtiene respuestas de una fuente y produce versiones de eventos.
Una versión puede sustituir al estado actual si su `updated` es posterior. Cada
evento puede relacionarse espacialmente con cero, uno o varios países. Los
rechazos se conservan en cuarentena.

## Lógico

- `ingestion_run`: ejecución, modo, filtros, contadores y estado.
- `source_response`: respuesta original y procedencia; relación N:1 con una
  ejecución.
- `event_version`: historial por `(event_id, updated)`.
- `event_current`: última versión por evento, con país y marca sintética.
- `quarantine_record`: evento no tratable, motivo y original.
- `historical_interval_checkpoint`: un intervalo confirmado por run; permite reanudar sin repetir el commit.
- `replay_event_version` / `replay_event_current`: versiones y estado de demostración aislados de las tablas reales.

## Físico e índices

Las tablas usan PostgreSQL y `JSONB` para originales. Las restricciones únicas
evitan duplicados. `event_version(event_id, updated)` acelera idempotencia;
`event_current(event_time)` acelera ventanas; `(country_id, event_time)` acelera
filtros del mapa y estadísticas; `ingestion_run(status, started_at)` facilita
salud y operación; `source_response(run_id, received_at)` facilita auditoría;
`quarantine_record(reason_code, created_at)` facilita calidad.
`replay_event_current(event_time)` permite filtrar la demostración. El índice
temporal real se observó en una consulta horaria de 2025: 0,070 ms y 3 bloques,
frente a 6,622 ms y 2.688 bloques en recorrido secuencial forzado; véase
`docs/ANALISIS-COMPLEJIDAD-COSTES.md` para el límite de esta medición.
