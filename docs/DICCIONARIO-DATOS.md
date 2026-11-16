# Diccionario y procedencia

## Fuentes

- **USGS live**: `all_day.geojson`, ventana móvil de 24 horas, consulta cada
  60 segundos.
- **USGS histórico**: catálogo FDSN, 2025 completo, mundial, magnitud mínima
  4 y `eventtype=earthquake`.
- **Natural Earth**: `frontend/public/datos/paises.geojson`, WGS84.

## Campos principales

| Campo | Grano | Significado | Unidad |
|---|---|---|---|
| `event_id` | evento | Identificador USGS | texto |
| `updated` | versión | Revisión USGS | milisegundos UTC |
| `event_time` | evento | Momento del terremoto | milisegundos UTC |
| `mag` | evento | Magnitud original | escala USGS, puede ser nula |
| `depth_km` | evento | Profundidad | km, puede ser nula |
| `longitude`, `latitude` | evento | Coordenadas | grados WGS84 |
| `country_id` | evento | `ADM0_A3` del catálogo | texto o nulo |
| `mode` | flujo | `live`, `historical` o `replay`; replay usa tablas propias | catálogo |
| `load_type` | ejecución | `live_feed`, `historical_initial` o `historical_replay` | catálogo |
| `original_jsonb` | respuesta/evento | Copia sin transformar | JSONB |
| `is_synthetic` | evento | Marca de datos controlados | booleano |

Las versiones se identifican por `(event_id, updated)`. El estado actual tiene
una fila por `event_id`. Los originales y sus metadatos de URL, tiempos, HTTP y
recuento se conservan bajo `evidence/`, excluidos de Git.
El replay conserva `event_time` original y `replay_at` en
`replay_event_version`/`replay_event_current`; el original mensual sigue en
`evidence/` y el mensaje Kafka incluye su referencia.
