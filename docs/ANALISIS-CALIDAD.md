# Calidad, transformación y conclusiones

## Alcance y método

Fuente: los 12 originales USGS del manifiesto
`evidence/002-ingesta-usgs-persistencia/historical/2025-minmag4-earthquake-manifest.json`.
Periodo UTC `[2025-01-01, 2026-01-01)`, ámbito mundial, `minmagnitude=4`,
`eventtype=earthquake`. El manifiesto anterior de 140.559 registros responde a
otros filtros y **no** entra en esta comparación. `python tools/quality_2025.py`
contó el original (antes); las consultas siguientes cuentan las filas preparadas
de `event_current` con `load_type='historical_initial'` (después).

```sql
SELECT count(*) AS n,
 count(*) FILTER (WHERE mag IS NULL) AS null_mag,
 count(*) FILTER (WHERE depth_km IS NULL) AS null_depth,
 count(*) FILTER (WHERE country_id IS NULL) AS no_country,
 count(*) FILTER (WHERE mag<4) AS below4,
 count(*) FILTER (WHERE longitude NOT BETWEEN -180 AND 180
                  OR latitude NOT BETWEEN -90 AND 90) AS invalid_geo
FROM event_current WHERE load_type='historical_initial';
```

| Dimensión (denominador 18.302) | Original, antes | Preparado, después | Acción y límite |
|---|---:|---:|---|
| Registros / versiones únicas | 18.302 / 18.302 | 18.302 / 18.302 | Clave `(event_id,updated)`; cero duplicados en estos originales. |
| Magnitud presente y ≥4 | 18.302 | 18.302 | No imputar magnitudes; el filtro de fuente explica la completitud de este conjunto. |
| Profundidad presente | 18.302 | 18.302 | Conservar nulos cuando existan en live; no convertirlos a cero. |
| Tipo terremoto | 18.302 | 18.302 | Excluir otros tipos en origen; el original permanece. |
| Coordenadas en rango | 18.302 | 18.302 | Rechazar las inválidas a cuarentena. Rango válido no demuestra ubicación física exacta. |
| País sin asignar | No disponible en USGS | 14.350 (78,41 %) | Mantener nulo, principalmente mar o cobertura ausente; no atribuir país próximo. |

Los 18.302 registros aceptados representan el 100 % del original corregido;
no hubo limpieza que redujera este conjunto. En live se observaron 430 versiones,
422 eventos únicos y dos versiones sintéticas marcadas; `quarantine_record`
contiene dos casos controlados. Esos casos no se suman al histórico. La
consistencia se comprueba con límites WGS84 y país por polígono; la exactitud
física de magnitud, posición y fronteras requiere fuentes externas y no está
demostrada por estas reglas. La actualidad del feed se evalúa con
`ingestion_run.finished_at`; una revisión tardía puede llegar mucho después
del terremoto, por lo que latencia de recepción no equivale a frescura del
tiempo de ocurrencia. La API distingue generación de respuesta y última ingesta.

El run histórico heredado registraba `records_accepted=16.302`, aunque
versiones, eventos actuales y manifiesto daban 18.302. La migración reconcilia
solo ese contador del run completo desde `event_version`: consulta posterior,
`records_seen=18.302` y `records_accepted=18.302`. No modifica los originales
ni los eventos. El batch revisado calcula futuros contadores desde checkpoints.

## Tres conclusiones defendibles

Capturas reproducibles de Chrome headless: **2026-11-18 12:34 UTC**, con
filtros, periodo, recuento y fecha por imagen en
`evidence/002-ingesta-usgs-persistencia/visual-depth-night-20261118/manifest.json`.
Los recuentos live pueden variar al actualizarse USGS. Todas las conclusiones
excluyen sintéticos y replay.

1. En 2025 UTC, mundo, magnitud ≥4 y tipo terremoto, **14.350 de 18.302
   eventos (78,41 %)** carecen de país asignado por el catálogo Natural Earth.
   Esto justifica una categoría «Sin país asignado» en lugar de perderlos.
2. Con los mismos periodo y filtros históricos y profundidad **0–70 km
   inclusiva**, **13.690 de 18.302 (74,80 %)** cumplen el rango. El
   denominador incluye todos los eventos porque no hubo profundidad nula en
   este conjunto. Un evento exactamente a 70 km explica la diferencia con el
   recuento anterior de 13.689 para profundidad estrictamente menor de 70 km.
3. En la ventana fija **2026-11-17 00:43–2026-11-18 00:43 UTC**, mundo,
   magnitud ≥4 y terremotos reales, la API mostró **24 eventos** a las
   12:34 UTC frente a **18.302/365 = 50,14 por día** en 2025 con los mismos
   filtros. La diferencia es −26,14 (−52,1 %) respecto a esa media histórica,
   cuyo denominador incluye días con cero eventos. La instantánea `all_day`
   conservada a las 00:43 UTC contenía 22 para esa ventana; dos registros
   adicionales aparecieron después en el estado persistido. La ventana puede
   recibir eventos tardíos y no permite predecir actividad.

Las capturas de cada conclusión están en escritorio (1440 px) y móvil (375 px):
`conclusion-1-historico-paises-*`, `conclusion-2-historico-profundidad-*` y
`conclusion-3-reciente-mag4-*`. El mapa de 2025 dibuja la primera página de
1.000 puntos y avisa de ello; indicadores y porcentajes usan los 18.302.

La geografía proviene de un catálogo simplificado y una coincidencia sobre
fronteras puede ser ambigua. Las conclusiones describen solo los filtros,
periodos y originales señalados.

## Transformaciones aplicadas y decisiones para la defensa (16-11-2026)

| Original → regla → resultado | Afectados observados | Carácter y motivo |
|---|---:|---|
| Tipo USGS → solo `earthquake` → otros tipos excluidos o en cuarentena | 0 en los 18.302; 1 rechazo controlado | Obligatoria: no contar explosiones como terremotos. |
| Coordenadas `[lon, lat, profundidad]` → rango WGS84 y polígono → país o sin país | 18.302 válidos; 14.350 sin país; 1 rechazo controlado por rango | Obligatoria: no inventar puntos ni atribuir el mar al país próximo. |
| `(event_id, updated)` → unicidad y máximo `updated` → estado actual | 18.302 versiones/IDs históricos; enero repetido detectó 1.413 duplicados | Obligatoria: reintentos y revisiones no deben inflar recuentos. |
| Magnitud y profundidad nulas → conservar `null` → ND en panel | 0 en el histórico filtrado | Obligatoria: no convertir ausencias a cero. |
| Replay histórico → conservar tiempo original y añadir `replay_at` → tablas propias | 10 eventos de prueba | Obligatorio el aislamiento; las tablas separadas son la opción técnica usada. |

David eligió estas políticas el 16-11-2026:

- **Varias coincidencias geográficas:** menor `ADM0_A3` y estado `multiple_matches`. Motivo: mantener el evento en los recuentos por país y hacer visible la ambigüedad. En el estado actual no hay filas con varias coincidencias; la regla no alteró los 18.302.
- **Originales live:** conservar 30 días. Motivo: permitir auditoría reciente y acotar espacio. Se eliminan los archivos live vencidos y se vacía solo el payload completo de respuestas live antiguas en PostgreSQL; se conservan metadatos de consulta y originales por evento. El histórico mensual se conserva por separado.
- **Aviso de antigüedad:** 10 minutos desde la última ingesta completada. Motivo: tolerar algunos reintentos transitorios con sondeo de 60 segundos. Es una alerta de operación, no una transformación de datos.

La comparación interactiva usa magnitud mínima efectiva `max(4, filtro solicitado)` en ambos conjuntos. El histórico es la instantánea `historical_initial` de 2025; la ventana actual usa eventos únicos del estado live sin sintéticos y no suma replay. Para filtros de duración distinta de 24 horas se muestra la media histórica escalada a esa duración, con el número de días indicado; no se afirma equivalencia estacional.
