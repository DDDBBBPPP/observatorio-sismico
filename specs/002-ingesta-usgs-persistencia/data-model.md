# Modelo de datos: Ingesta USGS y persistencia trazable

## Entidades y grano

### `ingestion_run`

Una fila por ejecución de feed o carga batch.

- `run_id`: identificador único.
- `source`: `usgs`.
- `load_type`: `live_feed` o `historical_initial`.
- `mode`: `live` solo para publicaciones del feed; `replay` queda reservado.
- `period_start`, `period_end`, `interval_start`, `interval_end`.
- `started_at`, `finished_at`, `status`, `error`.
- `records_seen`, `records_accepted`, `records_rejected`, `records_skipped`.

### `source_response`

Una fila por respuesta HTTP conservada.

- `response_id`, `run_id`, URL y parámetros.
- `requested_at`, `received_at`, `http_status`, duración y hash.
- `payload_jsonb`: respuesta original exacta.
- `record_count`, `error_type`, `error_detail`.

Restricción recomendada: `(url, parameters_hash, response_hash, received_at)`
para no confundir respuestas distintas con una descarga repetida.

### `event_version`

Una fila por versión observada de un terremoto.

- `event_id`, `updated`: clave única de versión.
- `event_time`, `mag`, `mag_type`, `event_type`, `place`.
- `longitude`, `latitude`, `depth_km`, valores originales y unidades.
- `source_response_id`, `run_id`, `mode`, `ingested_at`, `processed_at`.
- `original_jsonb`, `normalized_jsonb`, `validation_status`.

### `event_current`

Una fila por `event_id`, siempre con la versión más reciente aceptada.

- Campos consultables del evento y `current_updated`.
- `event_version_id` de la versión vigente.
- `country_id`, `country_name`, `continent`, `subregion`.
- `country_assignment_status` y `country_assignment_reason`.
- `original_jsonb` y `normalized_jsonb`.

### `quarantine_record`

Una fila por rechazo o exclusión que deba conservarse.

- `quarantine_id`, `run_id`, `source_response_id`, `event_id` opcional.
- `stage`, `reason_code`, `reason_detail`, `created_at`.
- `original_jsonb`, `payload_reference`, `resolved_at` opcional.

### Catálogo geográfico

El catálogo entregado sigue siendo la fuente de geometrías. La persistencia
puede mantener una referencia de catálogo (`country_id`, nombre, atributos y
versión del archivo) sin duplicar la geometría completa en cada evento.

## Reglas y transiciones

1. `received` → `validated` o `quarantined`.
2. `validated` → `published` después del acuse Kafka en live.
3. `published` → `persisted` después de la transacción del consumidor.
4. Una versión repetida permanece sin nuevo efecto.
5. Una versión posterior actualiza `event_current`; una versión antigua no lo
   reemplaza.
6. Una cuarentena se confirma como procesada solo después de conservar el
   original y su motivo.

## Índices justificados

- `event_current(event_time)` para intervalos temporales posteriores de API.
- `event_current(country_id, event_time)` para filtros geográficos y temporales.
- `event_version(event_id, updated)` para deduplicación y revisión.
- `event_version(updated)` para inspección temporal de versiones.
- `ingestion_run(status, started_at)` para estado y últimas ejecuciones.
- `quarantine_record(reason_code, created_at)` para análisis de calidad.

Los índices se medirán con las consultas reales antes de afirmar una mejora.
