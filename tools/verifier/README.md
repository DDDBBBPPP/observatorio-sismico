# Verificador del flujo sintético

El productor conserva el JSON exacto y el acuse `send_confirmed`. El
consumidor registra todos los mensajes sintéticos que recibe, sin conocer el
`run_id` activo. El verificador selecciona una evidencia por `run_id`, exige
que la recepción ocurra después de `--started-at`, compara el envoltorio y
todos los campos de `event`, y devuelve código distinto de cero ante ausencia,
antigüedad o diferencias.

Desde Windows, con Python 3.14 o compatible:

```powershell
python tools\verifier\verify_event.py --evidence-dir evidence\001-minimal-kafka-flow\$runId --run-id $runId --started-at $startedAt
```

Para una prueba negativa sobre una copia:

```powershell
Copy-Item evidence\001-minimal-kafka-flow\$runId\consumer.json evidence\001-minimal-kafka-flow\$runId\consumer-altered.json
$altered = "evidence\001-minimal-kafka-flow\$runId\consumer-altered.json"
$json = Get-Content $altered -Raw | ConvertFrom-Json
$json[0].message.event.place = "ALTERED-FOR-NEGATIVE-TEST"
$json | ConvertTo-Json -Depth 10 | Set-Content $altered -Encoding utf8
python tools\verifier\verify_event.py --evidence-dir evidence\001-minimal-kafka-flow\$runId --run-id $runId --started-at $startedAt --consumer-json $altered
```
