# Contrato de fuente USGS

## Feed reciente

- Recurso: `all_day.geojson`.
- Ventana: últimas 24 horas móvil, no día natural.
- Frecuencia objetivo: aproximadamente cada 60 segundos, configurable.
- Filtro sísmico: `properties.type == "earthquake"`.
- Identidad: `properties.id`.
- Versión: `properties.updated`.
- Tiempo de evento: `properties.time`, milisegundos Unix UTC.
- Magnitud: `properties.mag`, puede ser nula.
- Tipo de magnitud: `properties.magType`.
- Coordenadas: `[longitud, latitud, profundidad_km]`.

## Histórico inicial

- Periodo: 2025 completo.
- División: meses, subdividibles si el límite de resultados lo exige.
- Cada solicitud conserva URL, parámetros, fecha, estado, duración, recuento y
  respuesta original.
- Los límites temporales se deduplican por `(id, updated)`.
- Metadatos de carga: `load_type=historical_initial`, `period=2025`,
  intervalo, `run_id` y fecha de extracción.

## Errores

Timeouts, HTTP 429/5xx, respuestas no JSON y respuestas parciales generan
estado fallido explícito, reintento con espera progresiva cuando proceda y no
borran el último estado válido.
