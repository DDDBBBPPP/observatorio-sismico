# Índice de evidencias del hito 001

Las evidencias son locales y no contienen credenciales. Cada ejecución tiene
un `run_id` independiente. Los cinco servicios de infraestructura y proceso
se comprobaron con `docker compose ps`; la API se comprobó con
`curl.exe -fsS http://localhost:8000/api/salud`.

## Repetición correcta

| Evidencia | run_id | Resultado |
|---|---|---|
| `repeat/run-32247e05ad464b3395adbd28657d27d4/` | `run-32247e05ad464b3395adbd28657d27d4` | `send_confirmed`, `receive_confirmed`, código del verificador `0` |

Incluye `repeat.txt`, `producer.json`, `consumer.json` y
`verification.json`. Kafka confirmó partición `0`, offset `1`.

## Pruebas negativas

| Caso | Evidencia | run_id | Código | Resultado observado |
|---|---|---|---:|---|
| Productor detenido | `failures/producer-stopped.txt` | ninguno | 1 | `docker compose exec` indicó que el servicio no estaba ejecutándose; no hubo envío |
| Kafka detenido | `failures/kafka-stopped.txt` | `run-6439064508e847efa82ae71d1c7c1d67` | 1 | `send_failed`, `KafkaConnectionError`, timeout limitado de 10 s |
| Consumidor detenido | `failures/consumer-stopped.txt` | `run-d43c3cc4372949aaa24f2f85855b6e27` | productor 0; verificador 1 | `receive_failed` por ausencia durante 5 s; tras restaurarlo Kafka entregó el mensaje pendiente |

En el caso del consumidor, `verification.json` conserva el resultado negativo.
La entrega posterior se registra únicamente como comprobación de recuperación:
no convierte retrospectivamente la ventana negativa en `receive_confirmed`.

## Restauraciones

Tras cada caso se restauró el componente fuera de la prueba y se comprobó que
Kafka, PostgreSQL, API, productor y consumidor volvieron a `running (healthy)`.

## Validación final Polish

Se hicieron dos intentos el 2026-11-12 desde Windows PowerShell, con Docker
Desktop y Python 3.14.7 disponible localmente. El primer intento no permite
atribuir un código de salida a `docker compose up`: PowerShell terminó el
script con código 1 al tratar el texto `producer Built` emitido por Compose
como `NativeCommandError`. La salida observada fue:
`docker : observatorio-sismico-producer Built`; por tanto,
`compose_up_build_exit` queda como `no_observado`, no como 1.

El segundo intento ejecutó de nuevo el comando sin ese tratamiento de stderr y
sí observó código 0:

| Comprobación | Código | Resultado |
|---|---:|---|
| `docker compose config --quiet` (segundo intento) | 0 | Configuración válida; cinco servicios |
| `docker compose up --build -d` (segundo intento) | 0 | Imágenes construidas y servicios arrancados |
| `docker compose ps` | 0 | `api`, `consumer`, `kafka`, `postgres` y `producer` `running (healthy)` |
| `curl.exe -fsS http://localhost:8000/api/salud` | 0 | `state=ready`, `ingestion=not_started` |
| `kafka-topics.sh --describe --topic observatorio-test` | 0 | 1 partición, 1 réplica, retención `604800000` ms |
| `publish-test` | 0 | `send_confirmed`, partición 0, offset 3 |
| `verify_event.py` (segunda verificación, sin redirección) | 0 | `receive_confirmed` |

El `run_id` nuevo fue
`run-1b33326097f74ee5a0863afcc2d28688` y el `event_id` fue
`test-1b33326097f74ee5a0863afcc2d28688`. El evento conserva
`mag=4.2`, `place="Localizacion ficticia de prueba"` y
`coordinates=[-3.7, 40.4, 12.0]`. El productor registró el acuse en
`run-1b33326097f74ee5a0863afcc2d28688/producer.json`; el consumidor registró
la recepción en `.../consumer.json`, y el resultado completo del verificador
está en `.../verification.json`. La salida de esta validación, incluidos
estados y tiempos, se conserva en
`run-1b33326097f74ee5a0863afcc2d28688/polish-validation.txt`.

No se ejecutaron USGS, persistencia de terremotos, endpoints de consulta,
Angular integrado, replay ni nuevas pruebas negativas. Las evidencias de las
pruebas negativas anteriores siguen identificables: el primer intento de Kafka
(`run-73ada47247d44f088dc3514de0652909`) no se presenta como oficial ni
exitoso, mientras que la repetición oficial es
`run-6439064508e847efa82ae71d1c7c1d67`.

## Selección para versionar

La selección pequeña y reproducible está en `selected/`: contiene los tres
JSON del flujo correcto `run-1b33326097f74ee5a0863afcc2d28688` y una copia de
cada fallo deliberado con su comando, código, síntoma y restauración. Las
carpetas `repeat/`, `failures/` y los demás `run-*` son evidencias locales
regenerables y permanecen ignoradas.
