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
