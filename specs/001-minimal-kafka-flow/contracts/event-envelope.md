# Contrato del evento sintético

El productor de prueba publicará un objeto JSON con este envoltorio conceptual:

```json
{
  "schema": "observatorio.test-envelope.v1",
  "run_id": "run-<identificador-unico>",
  "source": "synthetic-test",
  "mode": "test",
  "created_at": "<timestamp-utc>",
  "event": {
    "event_id": "test-<identificador-unico>",
    "event_type": "test-earthquake",
    "time": 1793109600000,
    "updated": 1793109900000,
    "mag": 4.2,
    "mag_type": "mw-test",
    "place": "Localizacion ficticia de prueba",
    "coordinates": [-3.7, 40.4, 12.0]
  }
}
```

El productor debe conservar el JSON exacto enviado y el acuse de Kafka. El
consumidor debe registrar el JSON exacto recibido junto con su `run_id`; no se
le atribuye comparar con un original que no tiene. Un verificador de la prueba
debe seleccionar el JSON del productor y el del consumidor por `run_id` y
comparar `schema`, `run_id`, `source`, `mode`, `created_at` y todos los campos
de `event`. Las fechas y coordenadas del ejemplo son sintéticas y no
representan actividad real.

Las evidencias se escriben en un bind mount común:

```text
./evidence/001-minimal-kafka-flow:/evidence
/evidence/<run_id>/producer.json
/evidence/<run_id>/consumer.json
```

El consumidor registra todos los mensajes sintéticos recibidos y no necesita
conocer de antemano el `run_id` actual. El verificador ejecutado desde Windows
selecciona el `run_id` solicitado, comprueba la ventana temporal y rechaza
evidencias antiguas, ausentes o alteradas.

La publicación confirmada por Kafka se registra separadamente de la recepción
confirmada por el consumidor. Un mensaje que no coincida debe producir
`receive_failed`.
