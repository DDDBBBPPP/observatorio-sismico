# Aceptación observada — 2026-11-15

## Revisión local de la rama 002 (18-11-2026, Europe/Madrid)

Se verificó primero que Docker tenía los cinco servicios `running/healthy` y
que el proceso ngrok estaba activo. Se reconstruyeron y recrearon solo
productor, consumidor y API; Kafka/PostgreSQL conservaron sus volúmenes. No se
descargó ni procesó de nuevo el histórico.

| Caso | Resultado observado |
| --- | --- |
| Manifiesto existente, solo lectura | 12 intervalos, 18.302 registros y 18.302 versiones; run antiguo `completed`, 12 respuestas de 18.302 registros y 0 checkpoints. Cumple la compatibilidad prevista. |
| Kafka controlado | `controlled-kafka-f1fb375d49fe4b25bdf6d125abc3953a`: versión inicial 1000, posterior 3000 y antigua 2000; actual 3000, tres versiones; repetición de 2000 sin cuarta versión. |
| Reinicio y mensaje defectuoso | Consumidor reiniciado entre versión inicial y posteriores; JSON roto registrado una vez en cuarentena; consumidor sano después. |
| Muestra del comprobador | 23:45:25 UTC del 17-11: cinco servicios sanos, última consulta correcta 23:44:26 UTC, live 24 h 236, live acumulado 1.047, histórico 18.302, replay 10, cuarentena 3, errores de consulta 0, retraso Kafka 0. |
| Pruebas | `tests/acceptance.py`, `tests/filter_contract.py`, prueba fuera de orden con rollback, `tests/consumer_integration.py`, dos pruebas Node y `ng build`: exit 0. Build local Angular con advertencia CommonJS conocida de Leaflet. |

La ejecución acotada final repitió la secuencia Kafka con
`controlled-kafka-e9b242d1c9b24c7d9d4b814e19dc1c70` y terminó con código 0.
Una lectura independiente del topic live observó el mensaje real
`nc75467792` en offset 1202: la clave Kafka era `nc75467792`, el sobre
compacto no incluía `provenance.original` y el original referenciado pasó
la verificación SHA-256. En la muestra sintética de 100 eventos, el sobre
compacto ocupó 691 bytes frente a 22.139 bytes del formato anterior (96,9 %
menos); es una medición de esa muestra, no una media de producción.
La muestra posterior de las 23:50:06 UTC registró cinco servicios sanos,
235 eventos live en 24 horas, 1.048 live acumulados, 18.302 históricos,
10 replay, 4 cuarentenas, 0 errores de consulta y retraso Kafka 0.

El navegador integrado devolvió `[]`; no hay capturas verificadas de
antes/después. La web pública de Netlify aún no incorpora este build local.
La prueba aislada `tests/manifest_validation.py` aceptó un manifiesto válido
de un solo intervalo con cero registros y rechazó un recuento falso; confirma
que el batch ya no presupone los valores del histórico guardado.
La prueba de 24 horas queda **preparada, no superada**; la muestra breve solo
comprueba que el script escribe datos correctos. Permanecen pendientes la
comprobación visual en navegador, un nuevo despliegue Netlify si se quiere
publicar el frontend, la prueba desde otro dispositivo y la observación
completa de 24 horas.

| Caso | Resultado observado | Evidencia repetible |
|---|---|---|
| Cinco servicios | Los cinco `healthy` tras `docker compose up --build -d`; también tras reiniciar consumidor. | `docker compose ps` |
| Live periódico | Dos runs completos a 00:58:46 y 00:59:46 UTC, intervalo de 60 s; último run visible en `/api/salud`. | SQL sobre `ingestion_run`, `load_type='live_feed'` |
| Recuperación de fuente | Un proceso de prueba con URL local cerrada reintentó 2 veces y terminó con error explícito; el servicio periódico siguió saludable. La recuperación dentro del mismo proceso tras un fallo real de USGS no se provocó. | `docker compose run --rm --no-deps -e USGS_FEED_URL=http://127.0.0.1:9 -e USGS_MAX_ATTEMPTS=2 producer python /app/src/main.py ingest-live` |
| Histórico | 12 originales, 18.302 versiones y 18.302 actuales; run completo con `records_seen=records_accepted=18.302`. Enero de prueba confirmó 1.413 duplicados; repetirlo omitió el checkpoint. | `python tools/quality_2025.py`; SQL de `docs/ANALISIS-CALIDAD.md`; comando de README |
| Versiones | 430 versiones live para 422 IDs; 423 estados actuales live incluidos sintéticos, y en todos `current_updated=max(updated)`. | SQL `event_version` y `event_current` |
| Cuarentena y geografía | Dos rechazos controlados: `non_earthquake` y `coordinates_out_of_range`; 14.350 históricos sin país, 0 coordenadas fuera de rango en histórico corregido. | `quarantine_record`; análisis de calidad |
| API | Salud 200; eventos GeoJSON, páginas de 7 sin IDs repetidos y total 18.302; estadísticas con mismo total y divisor 365; fechas invertidas 400 y preflight CORS 200. | `python tests/acceptance.py` (exit 0) |
| Replay Kafka | 10 publicados por `observatorio-usgs-replay`; 10 versiones y 10 actuales en tablas replay, con `replay_at`; segunda publicación dejó ambos recuentos en 10. No cambió el histórico (18.302). | Comando de README; SQL replay; API `mode=replay` |
| Angular | `npm run build` exit 0, con advertencia CommonJS de Leaflet. El navegador de pruebas no estaba disponible (`agent.browsers.list()` devolvió `[]`); interacción visual, fallo de API y captura del panel pendientes. | Build local |
| Persistencia | Reinicio del consumidor; histórico 18.302 y replay 10 permanecieron, y el script de aceptación pasó después. | `docker compose restart consumer`; SQL; script |

## Pendientes manuales

David ya observó la versión nueva, el filtro live USA y el filtro aplicado en
REPRODUCCIÓN; los resultados comunicados figuran al final de este documento.
David aportó después capturas en incógnito del sitio público con mapa,
indicador, gráficos por país/hora y tabla. La URL principal, configuración,
túnel y CORS respondieron en esta sesión. Quedan la revisión visual completa
de distribuciones y aviso durante caída/recuperación, y la prueba desde otro
dispositivo. Las casillas T005 y T006 de
`specs/003-entrega-completa/tasks.md` siguen abiertas por esas comprobaciones.

## Cierre local 16-11-2026 (sin repetir la carga histórica)

- Manifiesto corregido: mundo, `[2025-01-01, 2026-01-01)` UTC,
  `minmagnitude=4`, `eventtype=earthquake`, 12 intervalos, 18.302 registros y
  18.302 claves de versión. SQL: 18.302 versiones/IDs `historical_initial`,
  cero fuera de periodo, bajo magnitud 4 o sintéticos. Hay cero IDs históricos
  cuyo estado actual sea live; el replay permanece en otras tablas (10 IDs).
- Los cinco servicios Compose se observaron `running/healthy`. El build Angular
  pasó, con advertencia CommonJS de Leaflet; `dist/observatorio/browser`
  contiene `index.html`, `_redirects` y `config.json`. `docker compose config
  --quiet` y `git diff --check` pasaron. La aceptación HTTP volvió a pasar.
- Se corrigió una comparación no equivalente: el umbral mínimo efectivo es 4
  en la ventana actual y en 2025. En una consulta de 24 horas durante el cierre
  hubo 23 eventos comparables frente a 50,14 de media histórica; el dato live
  cambia con el feed. La API ahora entrega `last_ingestion` en ms Unix y
  distribuciones por intervalos que suman el total filtrado.
- Frontend local responde HTTP 200 en `http://127.0.0.1:4200/`. El navegador
  automatizado no estuvo disponible (`agent.browsers.list()` devolvió `[]`),
  por lo que mapa, controles, error y recuperación de API siguen sin prueba
  visual superada. David aportará captura. Netlify/ngrok siguen sin URLs
  observables; no se declara publicación.

### Correspondencia con las once pruebas del enunciado

| Caso | Estado al cierre |
|---|---|
| Evento nuevo | Persistencia y API observadas; aparición en mapa pendiente de captura. |
| Misma versión reenviada | Superada: enero repetido y segundo replay no aumentaron versiones. |
| Versión posterior | Se observan versiones live y `current_updated=max(updated)`; cambio visual y recálculo puntual no provocados. |
| Versión antigua posterior | Superada con secuencia 1000→3000→2000 y duplicado 2000 en transacción revertida: actual 3000. |
| Magnitud nula | Regla `null`/ND implementada; caso visual no observado. |
| Coordenadas inválidas | Superada en cuarentena controlada con motivo. |
| Evento marítimo | Superada: 14.350 históricos sin país permanecen. |
| Reinicio del consumidor | Superada en la sesión de aceptación del 15-11. |
| Cerrar túnel | Pendiente: no hay túnel ni prueba visual. |
| Reabrir túnel | Pendiente: no hay túnel ni prueba visual. |
| Replay histórico | Superado en Kafka, PostgreSQL y API; etiqueta visual pendiente. |

## Integración de filtros y recuperación — 16-11-2026

La captura descrita con `USA` escrito y 188 eventos globales es compatible con
un filtro aún sin aplicar: el campo anterior solo cambiaba el valor de edición
y la petición se lanzaba al pulsar «Aplicar filtros». La descripción no permite
saber si se había pulsado el botón; las pruebas de API y del estado del
componente no reprodujeron un fallo al aplicarlo. No existía un indicador de
qué filtros respaldaban los datos visibles.
El panel ahora muestra «Filtros aplicados», avisa de cambios sin aplicar y
conserva la selección aplicada para los refrescos periódicos. Mapa, métricas,
gráficos y tabla se actualizan juntos después de recibir ambos endpoints.

`python tests/filter_contract.py` pasó con un periodo UTC fijo de 24 horas,
compartido por `/api/eventos` y `/api/estadisticas`. Recuentos observados en
esa ejecución (el live varía con USGS):

| Filtro | Actual | Histórico comparable 2025 |
|---|---:|---:|
| `country_id=USA` | 146 | 71 |
| `country_id=ESP` | 0 | 1 |
| `min_mag=4` | 24 | 18.302 |
| `country_id=USA&min_mag=4` | 0 | 71 |
| `country_id=UNASSIGNED` | 30 | 14.350 |

Para cada caso se comprobó igualdad del total de GeoJSON y estadísticas,
filtros declarados, unicidad de IDs, pertenencia al país, sumas de países,
horas e histogramas, y comparación histórica contra la consulta de 2025 con
el mismo país y umbral efectivo. Replay devolvió 10 IDs con `mode=replay` y
`replay_at`, fuera de la consulta live. `node tests/filter-query.mjs` verificó
el mapeo UTC/código/modo; `node tests/component-state.mjs` verificó el camino
del botón, limpieza, conservación de la lectura ante fallo, recuperación y
selección replay mediante red simulada. El build Angular pasó; conserva la
advertencia CommonJS de Leaflet.

`tests/out_of_order.py`, ejecutado dentro del consumidor y con rollback,
insertó `updated=1000`, luego `3000`, después `2000` y repitió `2000`:
estado actual `3000`, tres versiones, repetición sin efecto. La consulta
posterior confirmó cero IDs `controlled-out-of-order-*` persistidos.

Caída real: antes de `docker compose stop api`, `/api/eventos` respondió y el
frontend local devolvió 200. Con la API detenida se observó `WebException`
al consultarla y el frontend siguió devolviendo 200. Tras `docker compose
start api`, `/api/eventos` respondió de nuevo y los cinco servicios quedaron
`healthy`. El estado del componente conservó `lastRead` y la tabla durante
una caída simulada, mostrando el aviso y recuperándose al siguiente intento.
La presentación visual en navegador sigue pendiente: el navegador automatizado
de esta sesión devolvió `[]`; se necesita captura de David para cerrar T005.

## Versión servida y observación de David — 16-11-2026

David comprobó **visualmente la versión anterior**: con USA aplicado vio 142
eventos y puntos concentrados en Estados Unidos. En REPRODUCCIÓN, el
16-11-2026 devolvió cero y `[2025-01-01, 2025-02-01)` devolvió diez puntos
globales. USA no estaba aplicado en esta última consulta; esos diez puntos
no son una incidencia de filtrado.

El proceso Angular que escuchaba en `127.0.0.1:4200` pertenecía a este
repositorio, pero el `main.js` servido (79.425 bytes) contenía el antiguo
`applyFilters()` y carecía de `countryOptions` y `appliedLabel`. Se detuvo
solo ese proceso identificado y se arrancó `ng serve --host 127.0.0.1 --poll
2000`. El nuevo `main.js` (139.024 bytes al primer GET) contiene el selector,
«Filtros aplicados» y el botón que pasa la selección al refresco. Un cambio
posterior en el texto de REPRODUCCIÓN apareció en el servidor sin reiniciarlo:
el sondeo de archivos funciona. Esta comprobación es HTTP de recursos, no una
inspección visual de la nueva pantalla.

La API y la prueba de estado del componente verificaron REPRODUCCIÓN con el
botón «Aplicar filtros»: enero de 2025 sin país, 10; enero con USA aplicado,
0 en `/api/eventos` y `/api/estadisticas`; noviembre de 2026, 0. Los diez de
enero son 7 sin país, 2 `ETH` y 1 `ARG`, con recuentos concordantes en ambos
endpoints. El filtro temporal actúa sobre `event_time` original, no sobre
`replay_at`. El panel ahora explica estos dos tiempos y oculta el aviso de
ingesta live atrasada en REPRODUCCIÓN; `frontend/tests/component-state.mjs`
comprobó ese estado con red simulada. El navegador automatizado seguía sin
estar disponible (`agent.browsers.list()` = `[]`), por lo que el aspecto y la
interacción real de la nueva versión requieren otra revisión de David.

## Cierre de entrega local — observación comunicada por David (16-11-2026)

David comunica que **vio en su navegador** `http://127.0.0.1:4200/` la versión
nueva con «País», «Filtros aplicados» y la explicación de fecha original y
fecha de reenvío. En REPRODUCCIÓN de enero de 2025, **USA aplicado mostró 0**
y **Todos los países aplicado mostró 10**. Esta es una comprobación visual
comunicada por David; el agente no la observó en navegador. Complementa los
tests HTTP y de componente, pero no acredita todavía el aspecto de todos los
gráficos y la tabla ni el aviso visual durante una caída de API/túnel.

Auditoría Git local: 55 archivos modificados o nuevos candidatos, ninguno
preparado en el índice; el mayor candidato mide 17.087 bytes. `.env`,
`frontend/node_modules`, `frontend/dist` y las descargas históricas bajo
`evidence/002-ingesta-usgs-persistencia/` están excluidos; no aparecen en la
lista de candidatos. La búsqueda de patrones de secretos no devolvió rutas.
`frontend/public/config.json` contiene la URL de API local, que habrá que
cambiar por la URL HTTPS pública del túnel antes de compilar para Netlify.
ngrok no está instalado en `PATH`; ambas URL públicas están pendientes. No se
ha hecho commit ni push y no se ha repetido la carga histórica.

Esta descripción corresponde al cierre local anterior; la comprobación del
túnel y el nuevo build figuran en la sección siguiente.

Comprobación final breve (16-11-2026): `npm run build`,
`python tests/filter_contract.py`, `node frontend/tests/component-state.mjs`,
`python tests/acceptance.py` y `git diff --check` terminaron con código 0.
`docker compose ps` mostró los cinco servicios `running` y `healthy`.
`/api/salud` y `http://127.0.0.1:4200/` respondieron HTTP 200 con límite
de 5 segundos. El build contiene `index.html`, `config.json` y `_redirects`.

## Túnel HTTPS y build preparado — 16-11-2026

| Prueba | Resultado observado |
|---|---|
| Configuración de origen | `frontend/public/config.json`: `mode=api`, base `https://sapling-unlearned-blush.ngrok-free.dev`, `skipNgrokWarning=true`. El código fuente y el JS compilado incluyen `ngrok-skip-browser-warning: 1` para los dos GET de datos. |
| Build con tiempo máximo | `npm run build`: exit 0; Angular informó 3,716 s de generación bajo un límite de 120 s. Advertencia de optimización CommonJS de Leaflet. |
| Artefacto | En `frontend/dist/observatorio/browser`: `config.json` igual a la fuente, `index.html` con los recursos generados y `_redirects` con `/* /index.html 200`. Sin coincidencias de `localhost` ni `127.0.0.1` en configuración y redirección publicables. |
| Salud por ngrok | GET con `ngrok-skip-browser-warning: 1`: HTTP 200, `service=api`, `state=ready`, ingesta `2026-11-16T17:00:15.751758+00:00`. |
| Eventos por ngrok | GET con el mismo encabezado: HTTP 200, GeoJSON `FeatureCollection` live, 178 features de 178 totales. |
| Estadísticas por ngrok | GET con el mismo encabezado: HTTP 200, `count=178`, 24 horas, 8 países, comparación histórica de 18.302 eventos. Recuento live variable. |
| Preflight CORS de prueba | OPTIONS por el túnel desde `https://observatorio-sismico.netlify.app` (origen de prueba, no sitio confirmado): HTTP 400. El contenedor API permite actualmente solo los dos orígenes locales. |

La carpeta exacta para subir manualmente es `frontend/dist/observatorio/browser`.
Antes de comprobar el panel publicado, añadir a `CORS_ORIGINS` el origen HTTPS
exacto del sitio que asigne Netlify, reiniciar la API y repetir el preflight.
Quedan pendientes publicación, prueba desde Netlify y otro dispositivo, y
revisión visual de gráficos, tabla y aviso de error/recuperación. No se
declara Netlify operativo; no hubo commit, push ni recarga histórica.

## Diagnóstico de Netlify y CORS — 16-11-2026

| Prueba | Antes | Después |
|---|---|---|
| Despliegue y configuración | API autenticada de Netlify: despliegue `6afb43dd955ba50ee86baace` publicado y `ready`. SHA-1 de `/config.json` y `/index.html` idénticos a los archivos locales del build; el JSON publicado usa la base HTTPS de ngrok, `mode=api` y `skipNgrokWarning=true`. | No se modificó el despliegue. |
| Acceso sin sesión | URL principal y URL del despliegue: HTTP 401 en `/` y `/config.json`; cuerpo `Login Redirect` hacia Netlify Edge Access. | Sigue en 401 sin sesión. No se verificó el panel público. |
| Túnel y API | ngrok HTTPS → `http://localhost:8000`; puerto local 8000 HTTP 200. GET por túnel con `ngrok-skip-browser-warning: 1`: salud 200/`ready`, eventos 200 con 200 features, estadísticas 200 con 200 eventos. | API `healthy`; túnel sigue en puerto 8000. GET de eventos y estadísticas con ambos orígenes exactos de Netlify y el encabezado de ngrok: HTTP 200, con `Access-Control-Allow-Origin` exacto. |
| Preflight CORS | Para `/api/eventos` y `/api/estadisticas`, OPTIONS con `Access-Control-Request-Headers: ngrok-skip-browser-warning` desde la URL principal y la del despliegue: HTTP 400 `Disallowed CORS origin`. | Las cuatro combinaciones: HTTP 200, `Access-Control-Allow-Origin` igual al origen solicitado. Origen local `http://localhost:4200` sigue en HTTP 200. |
| Concordancia de datos | El navegador no podía superar el preflight y por ello no podía recibir los datos de la API. | En una muestra, `metadata.total=200`, 200 features con 200 IDs únicos y coordenadas válidas, `estadisticas.count=200`; sumas por país, hora, magnitud y profundidad, todas 200. El componente dibuja los puntos válidos y usa `summary.count` en indicadores; la tabla muestra las primeras 100 filas. Un GET posterior dio 199 por variación live. |

Corrección: `.env` conserva los dos orígenes locales y añade
`https://stellar-basbousa-cee41b.netlify.app` y
`https://6afb43dd955ba50ee86baace--stellar-basbousa-cee41b.netlify.app`.
Se recreó solo la API mediante `docker compose up -d --no-deps --force-recreate api`.
La causa comprobada del mapa sin datos era el rechazo CORS del preflight.
El navegador de pruebas no estuvo disponible (`agent.browsers.list()` = `[]`),
de modo que falta confirmar visualmente mapa, indicadores y tabla tras iniciar
sesión en Netlify Edge Access. No se alteró el despliegue, no se repitió la
carga histórica y no hubo commit ni push.

## Verificación final y corrección de frescura — 16-11-2026

Las comprobaciones siguientes se ejecutaron en esta sesión con timeout por
petición o proceso. No se descargó ni cargó de nuevo el histórico.

| Caso | Resultado ejecutado |
|---|---|
| Servicios y túnel | `docker compose ps`: cinco servicios `running/healthy`; `docker compose config --quiet` exit 0. El administrador local de ngrok respondió 200 y confirmó `https://sapling-unlearned-blush.ngrok-free.dev` → `http://localhost:8000`. |
| API local y pública | Salud, eventos y estadísticas: HTTP 200 en `127.0.0.1:8000` y por ngrok con `ngrok-skip-browser-warning: 1`; una instantánea devolvió 195 features y 195 en estadísticas. |
| Netlify sin sesión | URL principal y permalink del despliegue: `/` HTTP 200; ambos `/config.json` HTTP 200 con `mode=api`, URL HTTPS correcta y `skipNgrokWarning=true`. Ruta SPA inexistente en la principal: HTTP 200 con `index.html`. El SHA-1 público de `config.json` coincide con el build local. Los 401 de la observación anterior ya no se reprodujeron. |
| CORS | OPTIONS desde `https://stellar-basbousa-cee41b.netlify.app` hacia eventos y estadísticas con `Access-Control-Request-Headers: ngrok-skip-browser-warning`: HTTP 200, origen y encabezado permitidos. |
| Filtros equivalentes por túnel | Ventana UTC fija de 24 h, `mode=live`, `min_mag=4`: eventos 13, estadísticas 13, suma de país y horas 13, filtros declarados iguales; comparación histórica 18.302. Replay enero 2025: 10 solo en `mode=replay`. Los recuentos live cambian con el feed. |
| Frescura sin novedades | Antes, salud mostraba último run del consumidor a las 20:44 UTC aunque el productor guardaba respuestas correctas recientes con `published=0`. Se corrigió: productor guarda atómicamente la última consulta correcta y API lee esa marca desde un mount de solo lectura. Tras recrear solo productor y API, a las 21:13 UTC salud y `metadata.last_ingestion` reflejaban la consulta de 21:12:46 UTC, con último run del consumidor todavía a las 20:44 UTC. Más tarde una consulta de 21:15:53 UTC avanzó la marca con `published=0`; el último run procesado permanecía a las 21:14:53 UTC. |
| Build y pruebas | `npm run build` exit 0, generación 3,975 s dentro de 120 s; advertencia CommonJS de Leaflet. `tests/acceptance.py`, `tests/filter_contract.py`, `frontend/tests/filter-query.mjs`, `frontend/tests/component-state.mjs` y `tests/out_of_order.py` terminaron con exit 0; esta última hizo rollback. |
| Aislamiento | SQL de solo lectura: 18.302 filas actuales `historical_initial`, 783 filas live reales acumuladas y 10 filas/10 versiones replay en tablas separadas. No se reenvió replay. |

**Observación de David, distinta de las pruebas del agente:** en incógnito
David aportó [captura del mapa con círculos](https://gyazo.com/a5d2b4ab2753c958e0a5c9cc6c7d2359),
[captura de indicadores y gráficos por país/hora](https://gyazo.com/030a62608d74f26b6362eef494dc3a32)
y [captura de la tabla con filas](https://gyazo.com/6d7f102fb89adec31a730d9a00b7e50e).
La captura de indicadores muestra 192 eventos, magnitud/profundidad ND 0,
USA 163 y «Sin país asignado» 20; coincide con la ejecución de filtros de
esta sesión para USA y sin país. La tabla indica 100 primeras filas. El agente
inspeccionó las capturas, pero no controló el navegador (`agent.browsers.list()`
devolvió `[]`). Quedan por observar visualmente las distribuciones completas,
el aviso durante caída y recuperación del túnel, y el acceso desde otro
dispositivo. El sitio y la API respondieron mientras el PC, Docker y ngrok
estaban activos; no se afirma disponibilidad con alguno de ellos apagado.

## Revisión previa a PR — 16-11-2026

| Comprobación nueva | Resultado |
|---|---|
| Rama inicial | `002-ingesta-usgs-persistencia`, commit `2847ce1` en local y `origin`; árbol limpio antes de esta revisión. |
| Servicios/Compose | Cinco servicios `running/healthy`; `docker compose config --quiet` exit 0, con timeout de 15 s. |
| API/túnel | ngrok administra `https://sapling-unlearned-blush.ngrok-free.dev` → `http://localhost:8000`. Salud, eventos y estadísticas HTTP 200 en local y por túnel con `ngrok-skip-browser-warning: 1`; instantánea live 199 eventos en ambos endpoints. |
| Netlify/CORS | Página principal y `config.json` públicos sin sesión: HTTP 200. JSON: `mode=api`, base HTTPS correcta y `skipNgrokWarning=true`. OPTIONS desde el origen principal hacia eventos y estadísticas con el encabezado de ngrok: HTTP 200 y origen permitido. |
| Build | `npm run build` exit 0; Angular informó 2,887 s de generación bajo límite de 120 s. Advertencia CommonJS de Leaflet. |
| Pruebas existentes | `tests/acceptance.py`, `tests/filter_contract.py`, `frontend/tests/filter-query.mjs` y `frontend/tests/component-state.mjs`: exit 0 con límites individuales. Aceptación: histórico 18.302, replay 10. Filtros live de esa ejecución: USA 167, sin país 24, magnitud ≥4 13; números variables. |
| Observación visual | No hubo navegador del agente (`[]`). Siguen vigentes las capturas aportadas por David del mapa, indicador y tabla; no se ejecutó una prueba visual nueva de distribuciones ni de pérdida/recuperación de API. |

El README revisado separa el arranque live mediante `docker compose up --build
-d` de la descarga y procesamiento adicionales necesarios para reconstruir
el histórico de 18.302 en un Windows nuevo. No se probaron esos comandos en
esta sesión ni se hizo una instalación limpia en otro equipo. T005/T006
permanecen abiertas por las comprobaciones visuales y desde otro dispositivo.
