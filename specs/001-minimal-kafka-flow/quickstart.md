# Comprobación reproducible en Windows

Esta guía valida la implementación actual del primer hito descrita en el plan.
No contiene código de servicios.

## Prerrequisitos

- Windows con Docker Desktop iniciado y soporte de Linux containers.
- Docker Compose v2 disponible como `docker compose`.
- Repositorio clonado y configuración local creada desde `.env.example`, sin
  subir secretos.
- Docker e imágenes del proyecto ya disponibles localmente, o una fase previa
  de construcción completada. El objetivo de diez minutos empieza cuando el
  entorno está preparado; no incluye clonar, descargar imágenes ni el primer
  `docker compose build`.
- El topic `observatorio-test` de este hito está fijado a una partición y una
  réplica. Si `KAFKA_TEST_PARTITIONS` o `KAFKA_TEST_REPLICATION_FACTOR` tienen
  otro valor, el productor falla antes de crear el topic o publicar.

  Para comprobar la restricción sin tocar el topic ni los volúmenes, ejecutar
  cada caso por separado; ambos deben terminar con código 1 y mostrar la
  variable divergente:

  ```powershell
  docker compose run --rm --no-deps -e KAFKA_TEST_PARTITIONS=2 producer python /app/src/main.py publish-test
  docker compose run --rm --no-deps -e KAFKA_TEST_REPLICATION_FACTOR=2 producer python /app/src/main.py publish-test
  ```

## Arranque

Desde la raíz del repositorio:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --no-log-prefix --tail=100 kafka postgres api producer consumer
```

Registrar una captura o salida de `docker compose ps` y los logs de cada
servicio. El resultado debe distinguir `starting`, `ready`, `failed` o
`unavailable`. Un contenedor productor persistente terminado no puede contarse
como `ready`. Para el productor, `ready` exige que la comprobación del servicio
demuestre proceso vivo, resolución/conexión con Kafka y una operación de cliente
válida; un `sleep` o proceso ocioso no basta. La API se comprueba con
`curl.exe -fsS http://localhost:8000/api/salud`; dentro del contenedor el
healthcheck consulta `http://127.0.0.1:8000/api/salud`. Esto solo demuestra
estado de la API, no ingesta realizada.

## Activación de una ejecución

Esperar a que Kafka, PostgreSQL, API, productor y consumidor informen de su
estado previsto. El productor genera un `run_id` y `event_id` nuevos por
ejecución. Registrar primero la hora de inicio en `$startedAt` y activar
exactamente una ejecución dentro del productor ya iniciado:

```powershell
docker compose exec -T producer python /app/src/main.py publish-test
```

El proceso persistente se inicia por separado con
`python /app/src/main.py serve`. Conservar desde el productor el `run_id`, el
JSON enviado, el acuse de Kafka y la salida. El resultado solo es
`send_confirmed` si Kafka confirmó el registro. El código 0 de la activación
no implica recepción.

## Confirmación de recepción

Consultar los logs del consumidor limitando la ventana a después del inicio de
esta ejecución y buscando el `run_id` actual:

```powershell
docker compose logs --no-log-prefix --since $startedAt consumer
```

Conservar el JSON que el consumidor registra como recibido. La comprobación
externa compara el JSON enviado por el productor y el JSON recibido por el
consumidor por `run_id` y por todos los campos definidos. Solo esa comparación
produce `receive_confirmed`. Si el consumidor no recibe el mensaje, aparece
otro `run_id` o algún campo difiere, registrar `receive_failed`; un log antiguo
no cuenta.

Ejecutar el verificador desde la raíz del repositorio con Python 3.14 o
compatible:

```powershell
python tools\verifier\verify_event.py --evidence-dir evidence\001-minimal-kafka-flow\$runId --run-id $runId --started-at $startedAt
```

El bind mount de Compose hace visibles en Windows
`evidence\001-minimal-kafka-flow\<run_id>\producer.json` y
`consumer.json`; no se añade un sexto servicio.

Para comprobar una alteración sin contaminar la evidencia original, copiar el
JSON del consumidor, modificar solo la copia y pedir al verificador que use
esa copia:

```powershell
Copy-Item "evidence\001-minimal-kafka-flow\$runId\consumer.json" "evidence\001-minimal-kafka-flow\$runId\consumer-altered.json"
$altered = "evidence\001-minimal-kafka-flow\$runId\consumer-altered.json"
$json = Get-Content $altered -Raw | ConvertFrom-Json
$json[0].message.event.place = 'ALTERED-FOR-NEGATIVE-TEST'
$json | ConvertTo-Json -Depth 10 | Set-Content $altered -Encoding utf8
python tools\verifier\verify_event.py --evidence-dir "evidence\001-minimal-kafka-flow\$runId" --run-id $runId --started-at $startedAt --consumer-json $altered
```

El resultado esperado es `receive_failed` con la diferencia concreta; el
`consumer.json` original debe seguir intacto y continuar siendo la evidencia
de la ejecución correcta.

## Fallos deliberados

Aplicar estas pruebas, una por vez, sin comandos de recuperación automática:

1. **Productor detenido**: ejecutar `docker compose stop producer` y después
   `docker compose exec -T producer python /app/src/main.py publish-test`. La activación debe fallar porque no
   hay un contenedor productor operativo; no ejecutar `up`, `start` ni
   recrearlo.
2. **Kafka detenido**: ejecutar `docker compose stop kafka` y después la
   activación con `docker compose exec -T producer python /app/src/main.py publish-test`.
   Debe fallar la conexión o el acuse de Kafka;
   la prueba no debe ejecutar `docker compose up`, `start` ni recrear Kafka.
3. **Consumidor detenido**: ejecutar `docker compose stop consumer` y después
   `docker compose exec -T producer python /app/src/main.py publish-test`. Para
   probar la ausencia durante una ventana limitada, ejecutar el verificador con
   `--timeout-seconds 5`. Puede conservarse `send_confirmed`, pero sin JSON recibido de esta ejecución
   no puede existir `receive_confirmed`; el resultado final es fallo. Tras
   restaurar el consumidor, Kafka puede entregar el mensaje pendiente: esa
   entrega posterior se registra aparte y no cambia el resultado negativo.

En cada caso conservar comando, componente, síntoma, salida y resultado.
La política normal `restart: unless-stopped` no sustituye la prueba: después de
`docker compose stop`, no ejecutar `up`, `start` ni recrear el componente dentro
del caso negativo. Restaurarlo solo al terminar y registrar esa acción aparte.

También comprobar el arranque fallido de PostgreSQL o API como estado honesto;
no convertir esas pruebas en afirmaciones de persistencia o endpoints.

## Evidencias mínimas

Para cada ejecución guardar:

1. fecha y hora, `run_id` y `event_id`;
2. estados de los cinco servicios;
3. JSON enviado y acuse conservados por el productor;
4. JSON recibido y salida conservados por el consumidor;
5. comparación por `run_id` y todos los campos;
6. ventana temporal utilizada para excluir logs antiguos;
7. fallo y síntoma, si procede.

El productor y el consumidor escribirán estas evidencias mediante el montaje
`./evidence/001-minimal-kafka-flow:/evidence`:

```text
/evidence/<run_id>/producer.json
/evidence/<run_id>/consumer.json
```

## Limpieza

```powershell
docker compose down
```

No borrar volúmenes durante esta fase sin documentarlo. El hito no exige
persistencia de eventos, pero sí que la limpieza y el estado del entorno sean
reproducibles.

## Repetición US2 observada

En Windows, con Docker Desktop e imágenes disponibles, la repetición ejecutada
el 2026-11-12 generó un `run_id` y `event_id` nuevos, conservó el acuse Kafka,
el JSON del consumidor y una verificación `receive_confirmed`. Los estados
observados fueron `running (healthy)` para los cinco servicios antes y después
de la ejecución. La evidencia está en
`evidence\001-minimal-kafka-flow\repeat\<run_id>\`.

Las tres pruebas negativas se ejecutan una a una: se guarda primero el
resultado de `docker compose stop` y la activación fallida, y solo después se
restaura el componente con `docker compose up -d <servicio>`. Durante cada
ventana negativa no se ejecuta `up`, `start` ni una recreación.
