# Selección de evidencias versionable

Esta selección conserva una ejecución correcta y los tres fallos deliberados
del hito 001. Las copias JSON del flujo correcto corresponden al mismo
`run_id` y mantienen todos sus campos.

## Flujo correcto

- `correct-run-1b33326097f74ee5a0863afcc2d28688/producer.json`
- `correct-run-1b33326097f74ee5a0863afcc2d28688/consumer.json`
- `correct-run-1b33326097f74ee5a0863afcc2d28688/verification.json`
- Fecha: 2026-11-12.
- Comando: `docker compose exec -T producer python /app/src/main.py publish-test`.
- Resultado: código 0, `send_confirmed`, Kafka confirmó partición 0 y offset 3.
- Verificador: `python services\verifier\verify_event.py ...`, código 0,
  `receive_confirmed`.

## Fallos deliberados

- `failures/producer-stopped.txt`: `docker compose exec` código 1; el
  productor no estaba ejecutándose, no se generó `run_id` ni hubo envío;
  restauración posterior a `running/healthy`.
- `failures/kafka-stopped.txt`: `publish-test` código 1,
  `KafkaConnectionError` con timeout limitado de 10 segundos; run_id
  `run-6439064508e847efa82ae71d1c7c1d67`; Kafka y productor restaurados a
  `running/healthy`.
- `failures/consumer-stopped.txt`: productor código 0 y verificador código 1
  durante 5 segundos; run_id
  `run-d43c3cc4372949aaa24f2f85855b6e27`; no hubo recepción durante la
  ventana, Kafka entregó el mensaje después de restaurar el consumidor y el
  resultado negativo no se reescribió.

Los registros completos de origen permanecen en la evidencia local ignorada.
