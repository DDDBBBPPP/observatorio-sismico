# Auditoría de procedencia de la muestra 17:23 UTC

**Corte del monitor:** 2026-11-18 **17:23:04.112254 UTC**. El monitor anotó
última respuesta `run-69a12a1cd6594e70abf0483afaf3bcc2`, 191 features
descargadas y 192 eventos en `live_24h`, sin errores de muestra. Los dos
contadores no describen el mismo conjunto. El [informe JSON reproducible](../evidence/002-ingesta-usgs-persistencia/audit-monitor-1723-20261118.json)
conserva IDs, versiones, hashes, respuestas de procedencia, marcas de consulta
e índices; se generó con `python tools/audit_monitor_provenance.py` mediante
consultas **solo lectura**. No se incorporó el GeoJSON a Git.

## Original y filtros comparables

Archivo local conservado:
`evidence/002-ingesta-usgs-persistencia/originals/run-69a12a1cd6594e70abf0483afaf3bcc2/response.json`.
SHA-256 del archivo: `6b6655ddad52759db491b82e3f8a813a06f90d8e0e9501b08b33e6f4b3075114`.
Metadatos: GET de `all_day.geojson` solicitado **17:22:26.170184 UTC**,
recibido **17:22:26.313169 UTC**, HTTP 200, 142 ms, un intento, 191
features. PostgreSQL relaciona el run con
`response-8608271cbad14ad09003dc689fc6ec3c` y repite `record_count=191`;
el run registró 191 vistos, **una versión aceptada** y cero rechazadas.

Ventana fija aplicada a **todas** las comparaciones:
`[2026-11-17T17:23:04.112254Z, 2026-11-18T17:23:04.112254Z)`.
Filtros: `mode=live`, `type=earthquake`, sin mínimo de magnitud, país ni rango
de profundidad; sintéticos excluidos; inicio inclusivo y fin exclusivo.
Los 191 IDs del original son únicos y todos caen en esa ventana. Tres no son
terremotos: `uw714140061` (`explosion`) y `ci41363095`/
`ci41363087` (`quarry blast`). Quedan **188 terremotos únicos**.

| Conjunto para esa ventana | Resultado | Momento y límite |
| --- | ---: | --- |
| Original: features / terremotos | 191 / **188** | Respuesta 17:22:26 UTC |
| `event_version`: filas / IDs reconstruidos hasta el corte | 545 / **192** | `ingested_at <= 17:23:04.112254 UTC` |
| Estado reconstruido desde versiones al corte | **192 IDs** | No es una respuesta API guardada |
| Monitor `live_24h` | **192** | Solo guardó recuento, no IDs |
| `event_version`: filas / IDs a la auditoría | 592 / **199** | SQL a las 20:12 UTC |
| `event_current` a la auditoría | **199 IDs** | Estado actual, no el de las 17:23 |
| `/api/eventos` paginado | **100 + 99 = 199 IDs únicos** | GET a las 20:12 UTC |
| `/api/estadisticas` y suma de países | **199 / 199** | Mismo filtro a las 20:12 UTC |

Los 199 IDs y sus valores `updated` coincidieron entre `event_current` y
las dos páginas de `/api/eventos` en la auditoría. Las estadísticas no
exponen IDs, pero su recuento y suma por países coincidieron.

Los **188 pares `(event_id, updated)`** de terremotos del original ya estaban
en `event_version` al corte. En el estado reconstruido, ninguno faltaba ni
tenía otra `updated`. Había **cuatro IDs adicionales** que no aparecen en esa
respuesta, pero sí en respuestas USGS **anteriores** preservadas:

| ID adicional al corte | Run de la primera versión conservada | Respuesta recibida (UTC) |
| --- | --- | --- |
| `pt26322050` | `run-2c1934b0cb574f25a1ee9c8f9c6f8d15` | 18-11 02:32:45 |
| `us7000tywm` | `run-5e137259c8c8447bbdfd9fba8668541e` | 18-11 03:03:08 |
| `us7000tyx8` | `run-2c8de7ff8d624d7da466a8ce02963bdb` | 18-11 04:24:15 |
| `us7000tyzn` | `run-a267ecf1d9b2454ebf0d19f6bde0f58b` | 18-11 16:07:54 |

Para cada uno se comprobó **ID y `updated`** dentro del archivo original de
su run; el JSON auditado incluye ruta, `response_id` y SHA-256 de los cuatro.
Esta evidencia explica cómo **188 terremotos del último archivo + cuatro
persistidos antes = 192** puede ser coherente. No demuestra que esa fuera la
lista exacta devuelta por la API a las 17:23: el monitor no guardó sus IDs ni
el instante de inicio de aquella consulta.

A las 20:12 UTC, el conjunto fijo había crecido a 199. No faltaba ningún ID
de los 188 del original; los once IDs presentes solo en BD/API eran los cuatro
anteriores y siete llegados **después** del corte:
`aka2026wvvyxt`, `hv75071942`, `us7000tz1f`, `us7000tz1n`,
`uw714140221`, `uw714140241`, `uw714140301`. Sus runs y hashes constan en
el JSON. Doce IDs compartidos tenían ya una `updated` posterior a la del
original de las 17:22; se enumeran allí. La llegada tardía y las revisiones
impiden usar una lectura actual de `event_current` como fotografía exacta del
momento del monitor.
