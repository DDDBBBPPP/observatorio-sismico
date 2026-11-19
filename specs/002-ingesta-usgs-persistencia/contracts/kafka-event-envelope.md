# Contrato de mensaje Kafka

## Sobre de datos reales

```json
{
  "schema": "observatorio.event-envelope.v1",
  "event_id": "usgs-id",
  "source": "usgs",
  "mode": "live",
  "ingested_at": "2026-11-13T12:00:00Z",
  "event": {
    "id": "usgs-id",
    "updated": 1790000000000,
    "properties": {},
    "geometry": {}
  },
  "provenance": {
    "run_id": "run-id",
    "source_response_id": "response-id"
  }
}
```

`mode` solo admite `live` y `replay`. La carga histórica inicial no se publica
como `mode=historical`; sus metadatos batch viven en `provenance` y en el
registro de ingesta. El topic live es distinto del topic sintético del hito
001. La topología de replay queda fuera de este plan.

La clave Kafka es `event_id`. El consumidor no confirma la posición hasta
persistir el evento válido o la cuarentena.

En live, el productor envía el `event` original y la procedencia de la
respuesta, pero no repite la respuesta GeoJSON completa en cada mensaje.
`provenance.original_reference` señala el archivo de respuesta preservado en
`/evidence/002-ingesta-usgs-persistencia/originals/` y
`provenance.original_sha256` verifica sus bytes. El consumidor comprueba el
hash y que el evento figure en esa respuesta antes de almacenarla una vez en
`source_response`; cada versión conserva también su Feature original. El
replay incluye referencia y hash del original histórico. Se siguen leyendo
sobres live anteriores que llevan `provenance.original` completo.

Los mensajes inválidos se guardan en `quarantine_record` con referencia
`topic:partition:offset` y se confirma su offset. Los fallos transitorios de
PostgreSQL interrumpen el consumidor para reintentar tras reinicio; no se
confirman como si fueran errores de datos.
