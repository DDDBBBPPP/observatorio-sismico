# Evidencias de calidad del hito 002

## Alcance y procedencia

- Feed live observado: `all_day.geojson`, respuesta HTTP 200.
- Run live principal: `run-f8fdaf7e716a4eb9a00093502254d117`.
- Original: `evidence/002-ingesta-usgs-persistencia/originals/<run_id>/response.json`.
- Histórico comparable: manifiesto `2025-minmag4-earthquake-manifest.json`, 12 intervalos mensuales. Las cifras finales están en `docs/ANALISIS-CALIDAD.md`.
- Los casos controlados se identifican con `controlled-*` y no se mezclan con
  el análisis del feed real.

## Completitud y unicidad

En la misma respuesta live se observaron 205 features:

| Tipo USGS | Registros |
|---|---:|
| `earthquake` | 203 |
| `explosion` | 1 |
| `quarry blast` | 1 |
| Total | 205 |

El productor publicó 203 eventos sísmicos y conservó dos exclusiones. La cifra
204+2 procedía de otra respuesta posterior, no de la misma descarga.

La secuencia controlada del evento `ci41361719` produjo dos versiones distintas,
una omisión `duplicate_version` y un `event_current` con el `updated` posterior.

## Validez, consistencia y geografía

- Coordenadas fuera de rango: cuarentena con
  `reason_code=coordinates_out_of_range`.
- Tipo no sísmico: cuarentena controlada con `reason_code=non_earthquake`.
- Magnitud nula: persistida como nula, sin imputación.
- Punto marítimo `[0, 0]`: conservado con `unassigned` y
  `no_catalog_match`.
- Punto terrestre real: asignado mediante GeoPandas/Shapely al catálogo
  entregado, con `country_id=USA`.

## Rendimiento de transformación

Medición ejecutada dentro del contenedor productor sobre el mismo original,
antes de publicar:

| Entrada | Tiempo observado |
|---:|---:|
| 1 feature | 0,027 ms |
| 10 features | 0,021 ms |
| 100 features | 0,138 ms |

Son medidas de filtrado/deduplicación local, no de extremo a extremo Kafka,
HTTP o PostgreSQL; no deben interpretarse como throughput del sistema completo.

## Histórico 2025

El manifiesto corregido conserva 12 intervalos mensuales, 18.302 registros
mundiales de magnitud ≥4 y `eventtype=earthquake`. El manifiesto previo de
140.559 registros no aplica a la comparación histórica por filtros distintos.
Los originales se conservan y el batch revisado reanuda por checkpoint.

La persistencia batch se ejecuta con `mode=replay` y
`load_type=historical_initial`; nunca usa `mode=historical`.

## Límites

- La carga batch completa puede tardar varios minutos y requiere Docker,
  PostgreSQL, catálogo montado y acceso a USGS.
- La evidencia histórica local está ignorada por Git por su tamaño.
- No se implementan todavía API sísmica, Angular, Netlify, ngrok ni replay
  como topología Kafka independiente.
