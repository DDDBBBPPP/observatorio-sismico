# Modelo de datos del primer hito

Este modelo describe solo los datos necesarios para comprobar el recorrido
controlado. No define todavía el modelo persistente de terremotos.

## Evento sintético de prueba

Representa un único evento ficticio, claramente separado de USGS.

| Campo | Tipo | Regla |
|---|---|---|
| `event_id` | string | Obligatorio, único dentro de la ejecución y no vacío |
| `event_type` | string | Debe ser `test-earthquake` o equivalente explícitamente marcado |
| `time` | integer | Timestamp sintético en milisegundos UTC |
| `updated` | integer | Timestamp sintético en milisegundos UTC |
| `mag` | number o null | Valor controlado, no usado para conclusiones sísmicas |
| `mag_type` | string | Tipo de magnitud sintético |
| `place` | string | Texto que indique que es una prueba |
| `coordinates` | array de tres números | Orden `[longitud, latitud, profundidad_km]` |

El productor conserva este JSON como parte de la evidencia de envío. La
comprobación externa compara todos los campos presentes, no solo `event_id`,
contra el JSON que el consumidor registra como recibido.

## Envoltorio de prueba

| Campo | Tipo | Regla |
|---|---|---|
| `schema` | string | Identifica el formato del envoltorio |
| `run_id` | string | Identifica la ejecución reproducible |
| `source` | string | Debe indicar `synthetic-test` |
| `mode` | string | Debe indicar el modo de prueba, no `live` |
| `created_at` | string | Timestamp UTC de creación |
| `event` | objeto | Contiene el Evento sintético de prueba completo |

El topic de prueba tiene una partición. El plan no convierte este modelo en el
esquema de los futuros mensajes live/replay.

## Resultado de envío

| Estado | Significado |
|---|---|
| `send_attempted` | Se intentó publicar |
| `send_confirmed` | Kafka confirmó el registro |
| `send_failed` | No hubo confirmación |

Un `send_confirmed` no implica consumo.

## Resultado de recepción

| Estado | Significado |
|---|---|
| `receive_pending` | Se espera al consumidor |
| `receive_confirmed` | Un verificador comparó, por `run_id`, el JSON del productor con el JSON del consumidor y todos los campos coinciden |
| `receive_failed` | No se recibió, expiró la espera o el contenido difiere |

## Estado de servicio

| Estado | Aplicación |
|---|---|
| `starting` | Contenedor iniciado, dependencias aún no listas |
| `ready` | Proceso persistente preparado |
| `completed` | Activación controlada finalizada correctamente; no es `ready` |
| `failed` | El proceso o su comprobación falló |
| `unavailable` | No se puede verificar o contactar el servicio |

PostgreSQL y API pueden estar `ready` sin que exista persistencia de eventos ni
endpoint de consulta funcional en este hito. En particular, `GET /api/salud`
solo comprueba el estado técnico de FastAPI; no demuestra ingesta.

## Evidencia y correlación

Productor y consumidor comparten el bind mount
`./evidence/001-minimal-kafka-flow:/evidence`. El productor escribe
`/evidence/<run_id>/producer.json` y el consumidor
`/evidence/<run_id>/consumer.json`. El consumidor registra cada mensaje
sintético recibido con su `run_id`; no intenta identificar por sí mismo cuál es
la ejecución actual ni descarta mensajes por comparación con un identificador
que no conoce.

El verificador, ejecutado desde Windows, selecciona el `run_id` solicitado,
exige que ambas evidencias pertenezcan a esa ejecución y rechaza registros
anteriores, ausentes o alterados antes de emitir `receive_confirmed`.
