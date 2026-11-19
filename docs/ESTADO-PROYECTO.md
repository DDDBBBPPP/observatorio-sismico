# Estado del proyecto

## Estado vigente — 19-11-2026: medición local completada

- La medición iniciada el **18-11 a las 15:03:04 UTC** terminó el **19-11 a
  las 15:03:04 UTC**. El evaluador confirmó **24,0 horas**, **289/289**
  muestras, ningún hueco >450 s, ninguna muestra no saludable o con error,
  antigüedad máxima de consulta USGS **79,6 s**, ninguna muestra >10 min,
  lag Kafka máximo **0** y `complete_24h=true`. Se contrastaron primer y
  último registro. El [JSONL íntegro y sus límites](ACEPTACION.md)
  están publicados como evidencia; no se reinició el monitor ni se recargó
  el histórico para este cierre.
- El muestreo es **local y cada cinco minutos**: no mide disponibilidad
  pública continua de Netlify/ngrok ni cada segundo entre muestras. T006 de
  segundo dispositivo y caída/recuperación del túnel sigue pendiente.
  REPRODUCCIÓN filtra los diez eventos históricos ya reenviados por Kafka a
  tablas separadas; elegir otras fechas no ejecuta otro replay.
- Las secciones posteriores conservan lo observado en sus fechas anteriores
  como cronología. El PR #1 permanece en borrador, sin fusionar.

## Auditoría de procedencia y modelo sin interrumpir el monitor — 18-11-2026

- Rama `002-ingesta-usgs-persistencia`, punto inicial `d2195e399d08cbf5efcfa6fff2fffb4dc445f7a1`.
  La muestra de **17:23:04 UTC** anotó última descarga de 191 features y
  API live_24h=192. El [informe](AUDITORIA-PROCEDENCIA-1723.md) y su JSON
  contrastan original con SHA-256, pares `(ID, updated)`, versiones/estado
  PostgreSQL, API paginada y estadísticas en ventana UTC fija. Resultado:
  188 terremotos en la fuente; reconstrucción SQL al corte 192 con cuatro
  IDs de respuestas anteriores verificadas; la API original de las 17:23
  guardó solo el recuento, no sus IDs. A las 20:12 UTC el conjunto fijo daba
  199 en `event_current`, API y estadísticas, por siete llegadas posteriores.
- [Modelo ampliado](MODELO-DATOS.md) con Mermaid, grano/PK/FK/índices y
  revisión SQL. Dos índices reales cubren `(event_id, updated)`; el explícito
  redundante en columnas ocupaba 1.269.760 bytes. No se cambió DDL ni índices.
  El arranque del consumidor reejecuta el SQL de esquema; migraciones de una
  sola aplicación y revisión de índices son propuestas **posteriores**.
- Monitor PID **13216** comprobado activo. A las **20:08:04 UTC** había
  **62 muestras**, última con cinco servicios sanos, sin errores de muestra
  y lag Kafka 0. Esta observación no completa 24 horas. No se detuvieron ni
  recrearon servicios, ni se hizo carga histórica. Próximo paso: continuar
  la medición hasta después de 19-11 15:03:04 UTC y evaluar huecos, salud,
  frescura y lag con `tools/evaluate_monitor.py`. T006 externo sigue abierto;
  PR #1 en borrador, sin merge.

## Punto de reanudación: cierre documental y nueva medición — 18-11-2026

- Rama `002-ingesta-usgs-persistencia`; base al empezar este cierre
  `1b99ff3dc797a5de683e8d597b8e52083892067e`. Se sustituyó el README
  cronológico por uno final y se añadieron `docs/GUIA-INSTALACION.md` y
  `docs/GUIA-DEFENSA.md`. `ENUNCIADO.md`, contrato API, guía de entregables,
  dos copias idénticas de la FAQ y validación inicial se movieron a
  `docs/material-profesor/`; `FUENTES-Y-LICENCIAS.md` sigue en la raíz.
- Autorizada una nueva medición de 24 h. Antes del inicio se comprobaron cinco
  servicios `running/healthy` y ausencia de otro `tools/monitor_24h.py`.
  Muestra breve a **2026-11-18 15:02:46.921596 UTC** sin errores, cinco
  servicios sanos y lag Kafka 0. Ejecución en segundo plano PID **13216**,
  comprobado como `tools/monitor_24h.py`, primera muestra
  **2026-11-18 15:03:04.098498 UTC** en
  `evidence/002-ingesta-usgs-persistencia/monitor-entrega-20261118.jsonl`.
  Primera muestra: cinco sanos, cero errores de muestra, consulta USGS
  correcta a 15:02:20.877343 UTC, histórico 18.302, lag 0. El contador
  acumulado `live_fetch_errors_total=11` incluye errores previos al inicio;
  no implica once fallos de esta medición. **24 h aún no completadas**.
- Para consultar: `Get-Content evidence/002-ingesta-usgs-persistencia/monitor-entrega-20261118.jsonl | Select-Object -Last 1`.
  Para evaluar después de **2026-11-19 15:03:04 UTC**:
  `python tools/evaluate_monitor.py evidence/002-ingesta-usgs-persistencia/monitor-entrega-20261118.jsonl`.
  Verificar además PID/comando, huecos, salud, frescura, lag y errores. Esta
  medición local no mide por sí sola disponibilidad externa de Netlify/ngrok.
  No ejecutar pruebas que detengan API o consumidor mientras mide.
- Pendiente antes de la entrega final: T006 desde un segundo dispositivo con
  caída y recuperación del túnel. PR #1 debe permanecer en borrador, sin merge.

## Incremento de profundidad y tema azul noche — 18-11-2026

- Rama `002-ingesta-usgs-persistencia` desde `b1613977`; diez archivos de
  código/pruebas modificados al reanudar, sin reset ni cambio de rama.
- Monitor PID 15204 verificado como `tools/monitor_24h.py` y detenido. JSONL
  exploratorio intacto: seis muestras de 00:50:16 a 01:15:16 UTC (25 min), sin
  huecos, servicios no sanos, errores ni lag observado; no es prueba de 24 h.
- Cinco servicios Docker sanos tras reconstruir solo la API y ejecutar la
  batería completa `tools/run_checks.py` con límites, incluida integración
  Kafka. El contraste SQL fijo dio 200/179/15/6 eventos live para sin rango,
  0–70, 70–300 y −20–0 km; API, estadísticas y BD coincidieron. Replay dio
  10/8/2/0 y comparación 2025 18.302/13.690/3.511/0. Prueba SQL con tabla
  temporal cubrió NULL y límites inclusivos sin tocar datos persistentes.
- Chrome headless 157 capturó 16 vistas locales y manifiesto UTC a las
  12:34 UTC: 375/768/1440 px sin desbordamiento, tres conclusiones, USA con
  polígono, CAN con 0 eventos y polígono, «Sin país asignado» sin polígono,
  replay y caída/recuperación real de API. El navegador integrado devolvió
  `[]`. T005 queda comprobada; T006 aún requiere otro dispositivo/túnel.
- Trazabilidad SQL/API comprobada: 374 revisiones live guardadas, cuarentena
  real 0 al excluir dos casos controlados, marcas distintas de consulta USGS,
  primer evento nuevo y última persistencia. Duplicados descartados y lag se
  muestran «no medido». Cinco criterios literales de rúbrica cuentan con
  evidencia; la medición de 24 h sigue pendiente. El incremento se subió en
  `ca067aa` y el build `main-GIBIKXGC.js` se publicó en Netlify como
  `6afd9c835bbf58fb34663797`. La URL pública pasó assets, API y CORS por
  HTTP y Chrome headless a 1440/375 px: 31 eventos ≥4 coincidieron con API,
  sin desbordamiento. Capturas públicas y manifiesto UTC conservados. No
  iniciar monitor sin aprobación; T006 de segundo dispositivo/túnel pendiente.

## Estado anterior: vista mundial inicial y monitor después detenido — 18-11-2026

- Rama `002-ingesta-usgs-persistencia`, PR #1 en borrador. Se conservaron
  PostgreSQL, volúmenes y los 18.302 registros históricos; no se fusionó.
- Instantánea USGS recibida a las 00:43:00 UTC, SHA-256
  `3af89c8c6dea29e5202a544a165f1d84505ac25032be4a6f212e219b0a0bef3b`.
  En la ventana fija de 24 horas hubo 235 IDs `earthquake` originales y 236
  en API, estadísticas y PostgreSQL. El ID extra persistía de un feed anterior;
  no faltó ninguno del original. La suma de países fue 236. USA: 189/236;
  magnitud ≥4: 22 en todas las fuentes y USA 0. El feed móvil ya había subido
  a 237 al comenzar la nueva medición. Los terremotos pequeños tienen cobertura
  desigual y este reparto no estima actividad mundial ni riesgo.
- Nuevo panel publicado en Netlify, despliegue `6afcf624552b6cba53bcfec2`:
  cabecera compacta, periodo UTC y consulta USGS arriba, vista inicial mundial
  con magnitud ≥4 y vista de todos los registros. Conserva filtros, mapa,
  gráficos, tabla y replay. Pruebas Angular y build acotado superados; assets
  públicos, API y CORS comprobados. El navegador integrado no ofreció sesión
  (`[]`); quedan pendientes capturas y revisión visual escritorio/móvil.
- Monitor anterior detenido después de seis muestras y 25 minutos para separar
  versiones. Nuevo monitor iniciado **18-11-2026 00:50:16 UTC**, PID 15204.
  Primera muestra: cinco servicios sanos, cero errores, consulta USGS de 58,9 s,
  lag 0. La prueba definitiva de 24 h sigue **pendiente**. Evaluar mañana
  `monitor-final-20261118.jsonl` con `tools/evaluate_monitor.py`.
- Cobertura de evidencias de la rúbrica: cuatro de cinco criterios completos
  (80 %), análisis parcialmente verificado por ausencia de navegador. No es
  una calificación ni sustituye la observación de 24 horas.

## Auditoría y publicación del panel — 18-11-2026

- Instantánea USGS `all_day.geojson` de las 00:13:46 UTC preservada con
  SHA-256; ventana fija del 17-11 12:00–23:00 UTC. Original 112 IDs de
  terremoto, API/estadísticas/BD 113 (uno persistido de respuesta anterior),
  suma de países 113. Con magnitud ≥4, todos coinciden en 15.
- USA 88/113 sin filtro y 0/15 con magnitud ≥4; «Sin país asignado» 17/113
  y 7/15, respectivamente. Muestras de coordenadas verificadas contra
  polígonos; Canadá se comprobó con ejemplos históricos fuera de la ventana.
  La desigualdad de cobertura de magnitudes pequeñas limita la lectura del
  gráfico.
- Frontend con nombres españoles y códigos en gráfico/tabla/mapa, porcentajes
  por país, desglose de «Otros», periodo aplicado visible, estados de error
  y aclaraciones de cobertura. Build y pruebas acotadas pasan.
- **Nuevo despliegue Netlify realizado**: `6afcef8a47d80fa7d8a964ed`;
  URL pública, bundle, API por ngrok y CORS comprobados. Navegador integrado
  no disponible (`[]`), sin capturas ni inspección visual escritorio/móvil.
- Monitor de 24 horas en segundo plano desde las 00:13:39 UTC, PID 20256.
  Primeras dos muestras sanas y sin huecos, errores o lag; evaluación completa
  **pendiente** hasta transcurridas 24 horas reales.

## Revisión de PR #1 — 18-11-2026

- Rama `002-ingesta-usgs-persistencia`. Cinco servicios sanos y ngrok activo
  al inicio. PR #1 permanece abierto en borrador; no se fusionó.
- Kafka live y replay publican con clave `event_id`. Live referencia el
  original completo mediante ruta y SHA-256, y el consumidor verifica el
  contenido antes de guardarlo una vez; los mensajes antiguos siguen siendo
  legibles. El batch valida el manifiesto real sin fijar 12/18.302; el run
  antiguo completado se reconoce por 12 respuestas y recuento 18.302 aun sin
  checkpoints. No se repitió el histórico.
- Prueba controlada Kafka: inicial, nueva, antigua, duplicada, reinicio y JSON
  roto en cuarentena; consumidor sano. Aceptación, filtros, dos pruebas Node,
  prueba transaccional y build local Angular pasan. Cinco servicios sanos
  después de recrear productor/consumidor/API.
- Panel local rediseñado con marcas temporales separadas, filtros, mapa,
  indicadores, vista móvil y explicación de «Sin país asignado». El build
  local **no** actualiza Netlify; queda pendiente nuevo despliegue si se
  decide publicar.
- Comprobador de 24 horas preparado. Dos muestras breves sin errores, con
  retraso Kafka 0; **no** han transcurrido 24 horas. Navegador integrado no
  disponible (`[]`), por lo que faltan capturas antes/después y validación
  visual. También quedan pendientes prueba de túnel desde otro dispositivo
  y observación visual de pérdida/recuperación de la API.

## Bloque 1 — entorno e histórico (15-11-2026)

- Rama local `002-ingesta-usgs-persistencia`; cambios 002/003 sin commit conservados.
- `docker ps` mostró solo Kafka y PostgreSQL saludables. No había proceso batch residual en Windows ni contenedor batch; `pg_stat_activity` no mostró bloqueos ni transacciones ajenas a la consulta. Por ello no se detuvo ningún proceso.
- Consulta PostgreSQL observada: run `historical-2025-minmag4-earthquake` completo, 12 respuestas, 18.302 versiones históricas y 18.302 eventos actuales históricos, cuarentena 0. El contador `records_accepted=16.302` del run discrepa y requiere aclaración; no se usará como denominador.
- Archivos cambiados: `consumer/src/batch.py`, `consumer/src/main.py`, `consumer/src/migrations/001_ingestion_schema.sql`. El batch nuevo usa bloqueo de sesión, checkpoint por intervalo y commit por intervalo, sin borrar runs ni originales. `docker compose build consumer` terminó correctamente.
- Primera prueba de enero detenida tras observar tráfico JSON repetido, antes de confirmar intervalo; solo se detuvo su contenedor identificado. La corrección guarda el original grande una vez por intervalo.
- Segunda prueba de enero: checkpoint con 1.413 registros, 0 aceptados y 1.413 duplicados porque las versiones ya estaban cargadas. Repetición: `skipped_checkpoint`, estado `partial`, exit 0. Run principal: `already_completed`, 12 intervalos, exit 0. No se reconstruyó el año.
- Decisión técnica cerrada: replay en tablas `replay_event_version` y `replay_event_current`, separado de `event_version`/`event_current`; cambios en migración, consumidor, productor, API y Angular. Falta comprobarlo en ejecución.
- Pendientes: servicios, replay, aceptación y documentación de resultados. Decisiones de transformación: se mantienen las de specs y FAQ; ninguna nueva abierta detectada. Siguiente comando: `docker compose up --build -d`.

## Bloque 2 — servicios y replay (15-11-2026)

- `docker compose up --build -d` finalizó con exactamente cinco servicios; `docker compose ps` mostró los cinco saludables. `/api/salud` devolvió 200 y un run live reciente con 14 aceptados. `npm run build` en `frontend/` finalizó con éxito; advirtió solo que Leaflet es CommonJS.
- Archivos cambiados: migración SQL, `consumer/src/persistence.py`, `consumer/src/main.py`, `producer/src/main.py`, `api/src/main.py`, `frontend/src/app/app.component.{ts,html,css}`. El replay está en tablas y filtro API propios; el panel tiene selector REPRODUCCIÓN y gráficos de barras por país y hora.
- Primer envío replay falló por límite de mensaje Kafka (1.087.398 bytes): el sobre incluía el original mensual completo. Se cambió a original del evento y referencia al archivo mensual intacto. Segundo envío publicó 10 mensajes, exit 0. PostgreSQL: 10 filas en `replay_event_current`; `/api/eventos?mode=replay` devolvió 10, con `replay_at`; `/api/estadisticas?mode=replay` devolvió 10 y cuatro ventanas horarias.
- Pendientes: demostrar idempotencia del replay, comportamiento de errores, panel en navegador, calidad con cifras, conclusiones y rendimiento. Siguiente comando: repetir replay limitado a 10 y comparar contadores.

## Bloque 3 — aceptación, análisis y entrega (15-11-2026)

- Reenviar replay dejó 10 versiones y 10 eventos replay; histórico permaneció en 18.302. `tests/acceptance.py` pasó antes y después de reiniciar consumidor. Los cinco servicios están saludables tras `docker compose up --build -d consumer`.
- Periodicidad observada: runs live a 00:58:46 y 00:59:46 UTC. Un proceso aislado con URL cerrada reintentó dos veces y terminó con error explícito; la recuperación dentro del mismo proceso ante un fallo USGS real no se provocó.
- Calidad: `python tools/quality_2025.py` dio 18.302 originales, cero duplicados, magnitudes/profundidades nulas, tipos no sísmicos o coordenadas inválidas en el conjunto filtrado. SQL preparado: 18.302 eventos, 14.350 sin país y 13.689 de profundidad <70 km. Tres conclusiones y comparación 19 recientes ≥4 frente a 18.302/365 en `docs/ANALISIS-CALIDAD.md`.
- Rendimiento observado con 100/500/1.000 features: 0,034/0,175/0,381 ms y 1,3/4,4/8,9 KiB de pico Python. Índice temporal 0,070 ms frente a recorrido secuencial forzado 6,622 ms en una consulta horaria. Detalles y costes supuestos en `docs/ANALISIS-COMPLEJIDAD-COSTES.md`.
- Migración nueva corrigió solo el contador heredado del run histórico completo: 16.302 → 18.302, derivado de sus versiones persistidas. Consulta posterior confirmó `records_seen=records_accepted=18.302`.
- Archivos de este bloque: `.env.example`, `compose.yaml`, `producer/src/main.py`, `producer/src/measure_transform.py`, `consumer/src/batch.py`, migración, frontend, `tests/acceptance.py`, `tools/quality_2025.py`, `README.md`, documentos de `docs/` y tareas Spec Kit. `npm run build` pasó; `git diff --check` sin errores de espacios.
- Comprobación visual bloqueada: el navegador de pruebas no estaba disponible (`agent.browsers.list()` = `[]`). Netlify/ngrok requieren URL y cuenta de David. La publicación y la prueba desde otro dispositivo quedan pendientes. No se marcan T005/T006 de 003 como comprobadas.
- Decisiones: se mantuvieron filtros y tratamientos de specs/FAQ; replay separado en tablas para cumplir aislamiento. Ninguna decisión nueva de transformación abierta. Siguiente comando local: `docker compose ps`; para aceptación reproducible: `python tests/acceptance.py`; para publicación, seguir `README.md` y `docs/ACEPTACION.md`.

## Resumen por hito

| Hito | Estado verificado | Pendiente |
|---|---|---|
| 001 | Evidencias sintéticas previas publicadas en `main`; no se rehizo. | Nada de este hito en esta tarea. |
| 002 | Live, geografía, versiones, cuarentena e histórico corregido de 18.302. Batch reanudable probado con enero. | Casillas de pruebas específicas aún abiertas en `tasks.md`; no inferirlas de la aceptación general. |
| 003 | Cinco servicios, API, replay aislado, build Angular, análisis, pruebas automáticas y comprobación visual parcial comunicada por David. | Resto de revisión visual, Netlify/ngrok y acceso desde otro dispositivo. |

Las casillas de `specs/002-ingesta-usgs-persistencia/tasks.md` y
`specs/003-entrega-completa/tasks.md` indican el trabajo aún abierto. La
evidencia de aceptación y los pasos manuales están en `docs/ACEPTACION.md`.

## Bloque 4 — cierre técnico local y publicación preparada (16-11-2026)

- Los 18.302 corresponden al manifiesto corregido de 12 meses, mundo,
  magnitud ≥4, tipo `earthquake`, año 2025 UTC: 18.302 versiones y 18.302 IDs,
  sin sintéticos ni valores fuera de filtros. El estado live tenía 601 IDs al
  consultar la base y cero IDs históricos sustituidos por live; replay, 10 IDs
  en tablas propias. No se repitió la descarga ni el batch anual.
- Comparación corregida: magnitud efectiva ≥4 en ambos conjuntos, live actual
  sin sintéticos frente a instantánea `historical_initial`; al comprobar la
  ventana de 24 horas había 23 eventos comparables. Se corrigió la interpretación
  UTC de los campos del panel y el formato en ms de `last_ingestion`.
- Se añadieron distribuciones de magnitud y profundidad, con nulos visibles.
  `npm run build`, sintaxis Python, `docker compose config --quiet`, aceptación
  HTTP y cinco servicios `healthy` pasaron durante el cierre.
- David eligió menor `ADM0_A3` con marca de ambigüedad, retención live de 30
  días y aviso de ingesta tras 10 minutos. Implementación y motivos en
  `docs/ANALISIS-CALIDAD.md`; no hubo coincidencias geográficas múltiples en
  las filas actuales.
- Frontend local iniciado en `http://127.0.0.1:4200/`; API en
  `http://127.0.0.1:8000`. Navegador no disponible (`[]`): captura visual,
  fallo/recuperación de API y revisión desde otro dispositivo siguen pendientes.
  ngrok no está instalado en PATH y faltan sus URL HTTPS y la URL de Netlify;
  no se ha publicado ni hecho commit/push.

## Rúbrica y aceptación al cierre

| Criterio | Evidencia local | Pendiente real |
|---|---|---|
| Extracción | Histórico filtrado y manifestado; feed periódico y catálogo geográfico; tipos, unidades y errores documentados. | Ninguno local de la rúbrica. |
| Calidad | Seis dimensiones, antes/después, reglas y rechazos controlados en `ANALISIS-CALIDAD.md`. | Captura de filtros para la defensa. |
| Modelado | Grano actual/versión, claves, índices, unión por polígono, idempotencia y replay separado en `MODELO-DATOS.md`. | Ninguno local de la rúbrica. |
| Análisis | País/hora, distribuciones, comparación ≥4 equivalente y tres conclusiones fechadas. | Inspección visual de gráficos y mapa. |
| Reflexión | Tres tamaños de medición, índice frente a secuencial, costes y escalado en `ANALISIS-COMPLEJIDAD-COSTES.md`. | Ninguno local de la rúbrica. |

La aceptación automática y los escenarios ya observados constan en
`ACEPTACION.md`. Quedan sin observar visualmente el panel, el aviso y la
recuperación al fallar la API/túnel; también el acceso remoto a Netlify/ngrok.
No se elevan esas pruebas a superadas por el build o por respuestas HTTP.

## Bloque 5 — filtros, panel y recuperación (16-11-2026)

- La captura descrita con `USA` y 188 eventos globales es compatible con un
  valor escrito sin aplicar; no se sabe si se pulsó el botón. El código anterior
  no lanzaba la consulta al editar y las pruebas no reprodujeron un fallo al
  aplicarla. Se corrigió la falta de claridad: valores editados y
  aplicados separados, aviso de cambios pendientes, limpieza, selector de país
  por nombre/código, categoría sin país y ventana UTC compartida por endpoints.
- El panel conserva Leaflet, recuadra resultados al aplicar, muestra carga
  discreta, cuatro gráficos compactos con unidades y horas UTC, tabla más
  legible y explicación/tiempos de REPRODUCCIÓN. API: `UNASSIGNED` filtra
  `country_id IS NULL` en live e histórico.
- HTTP con ventana fija: USA 146 actuales/71 históricos, ESP 0/1, magnitud ≥4
  24/18.302, USA+≥4 0/71, sin país 30/14.350. Los totales, filtros,
  distribuciones y comparación coincidieron. Son recuentos de una ejecución;
  el feed live cambia. `tests/filter_contract.py`, aceptación previa,
  `frontend/tests/filter-query.mjs` y `frontend/tests/component-state.mjs`
  pasaron, igual que el build Angular.
- Versión fuera de orden probada en transacción revertida: 1000→3000→2000,
  repetición de 2000; estado 3000 y tres versiones. Sin registros de prueba
  persistidos. API detenida y arrancada: fallo HTTP observado, frontend 200,
  recuperación HTTP y cinco servicios `healthy` al terminar. La prueba de
  estado del componente observó aviso y `lastRead` conservado con red simulada.
  Falta confirmar la presentación visual con captura; no se marcó T005 como
  superada ni se repitió el histórico. Sin commit ni push.

## Bloque 6 — versión servida y REPRODUCCIÓN (16-11-2026)

- David observó en la versión antigua USA **aplicado** con 142 eventos y
  puntos en Estados Unidos. Su consulta REPRODUCCIÓN de noviembre de 2026 dio
  cero y la de enero de 2025 dio diez globales; USA no estaba aplicado en esa
  última vista. No se atribuye a esos diez puntos un fallo del filtro.
- Causa de los controles antiguos: `ng serve` seguía entregando un `main.js`
  anterior pese a que los fuentes y el build nuevos existían. Se identificó
  por PID/comando y se reinició solo ese servidor con `--poll 2000`. El nuevo
  recurso HTTP contiene `countryOptions`, `appliedLabel` y la ruta de botón
  actual; una edición posterior se publicó sin reiniciar. README actualizado
  para instalación limpia en Windows y para recarga forzada de pestaña.
- REPRODUCCIÓN: texto en pantalla aclara terremotos reales antiguos,
  separación por Kafka, filtro por fecha original y fecha de reenvío UTC.
  El aviso de ingesta live atrasada queda reservado a «Datos reales».
  API y estado del componente verificaron filtro USA **aplicado** en replay:
  0 eventos frente a diez globales; reparto global `UNASSIGNED` 7, `ETH` 2,
  `ARG` 1. Noviembre de 2026 devuelve cero por usar tiempo original.
- Build y pruebas HTTP/componente pasaron; los cinco servicios permanecen
  saludables. No hubo navegador automatizado para inspeccionar visualmente la
  nueva versión. No se descargó ni procesó de nuevo el histórico; sin commit
  ni push.

## Bloque 7 — cierre de entrega local (16-11-2026)

- David comunica que **observó en navegador** la versión nueva en
  `http://127.0.0.1:4200/`: «País», «Filtros aplicados» y explicación de las
  dos fechas. En REPRODUCCIÓN de enero de 2025, USA aplicado mostró 0 y Todos
  los países aplicado mostró 10. No lo observó el agente en navegador; las
  pruebas de HTTP/componente se documentan por separado.
- README revisado para una instalación Windows nueva: dos ventanas de
  PowerShell, cinco servicios Compose, comprobación `/api/salud`, `npm ci`,
  `ng serve` con sondeo, y distinción entre live y replay. Los originales
  históricos no se incluyen en Git, por lo que una instalación nueva requiere
  su carga separada para la comparación.
- Auditoría Git: 55 candidatos locales, cero staged, tamaño máximo 17.087
  bytes. `.env`, credenciales reales detectables por patrones, originales
  históricos, `node_modules` y builds no figuran entre candidatos. La ruta
  SPA, el build y `config.json` local están preparados; faltan la URL HTTPS de
  ngrok y el origen HTTPS exacto de Netlify. ngrok no está en `PATH`.
- Pendientes: revisar visualmente gráficos, tabla y aviso al fallar la API;
  activar túnel y publicar/verificar ambas URLs. No se hizo commit ni push ni
  se repitió la carga histórica.
- Comprobación final breve: build Angular, contrato de filtros, estado del
  componente, aceptación y `git diff --check` con exit 0; cinco servicios
  `running` y `healthy`. Se corrigió una sección antigua de pendientes en
  `docs/ACEPTACION.md` que aún pedía la prueba visual ya comunicada por David.
  Salud API y frontend local respondieron HTTP 200 en menos de 5 segundos; el
  build contiene `index.html`, `config.json` y `_redirects`.

## Bloque 8 — túnel HTTPS y artefacto para Netlify (16-11-2026)

- `frontend/public/config.json` usa `mode=api`,
  `apiUrl=https://sapling-unlearned-blush.ngrok-free.dev` y
  `skipNgrokWarning=true`. El componente envía
  `ngrok-skip-browser-warning: 1` a eventos y estadísticas; el encabezado
  también aparece en el JavaScript compilado.
- `npm run build` terminó con exit 0 bajo un límite de 120 s; Angular informó
  3,716 s de generación. Persiste la advertencia CommonJS de Leaflet. En
  `frontend/dist/observatorio/browser` se comprobaron el `config.json` con
  la misma URL HTTPS, `index.html` con recursos del build y `_redirects` con
  `/* /index.html 200`. No hubo coincidencias de `localhost` ni `127.0.0.1`
  en la configuración y redirección que se subirían.
- Consultas GET por el túnel con el encabezado de ngrok: `/api/salud` HTTP 200,
  `service=api`, `state=ready`, última ingesta
  `2026-11-16T17:00:15.751758+00:00`; `/api/eventos` HTTP 200,
  `FeatureCollection` live, 178 features y total 178; `/api/estadisticas`
  HTTP 200, 178 eventos, 24 horas, 8 países y 18.302 eventos históricos
  comparables. Los recuentos live son una instantánea y pueden variar.
- Incidencia previa a la prueba desde Netlify: `CORS_ORIGINS` del contenedor
  API contiene solo `http://localhost:4200,http://127.0.0.1:4200`.
  Un preflight por el túnel desde un origen Netlify de prueba recibió HTTP 400.
  Falta añadir el origen HTTPS exacto que asigne Netlify y reiniciar la API;
  después hay que verificar preflight y panel desde el sitio publicado.
  No se ha comprobado Netlify ni se ha hecho commit o push. No se repitió
  la ingesta histórica.

## Bloque 9 — diagnóstico y corrección de mapa vacío en Netlify (16-11-2026)

- La API autenticada de Netlify confirmó que el despliegue
  `6afb43dd955ba50ee86baace` es el publicado y está `ready`. Sus archivos
  `/config.json` y `/index.html` tienen SHA-1 `62919ca0d7911685a67ce6752676520c6db0a7a1`
  y `4a9e073e0e4a0286a63b37a0ea69a7a0787fe989`, respectivamente;
  coinciden con los archivos locales del build. Por ello el `config.json`
  publicado usa `mode=api`, el túnel HTTPS indicado y
  `skipNgrokWarning=true`. Sin sesión, tanto la URL principal como la del
  despliegue devolvieron HTTP 401 para `/` y `/config.json`, con una página
  `Login Redirect` de Netlify Edge Access. La publicación está lista, pero
  el acceso público no quedó verificado.
- Antes de la corrección, ngrok mostraba
  `https://sapling-unlearned-blush.ngrok-free.dev` → `http://localhost:8000`;
  el puerto local 8000 respondía HTTP 200. Por el túnel y con
  `ngrok-skip-browser-warning: 1`, salud devolvió 200/`ready`, eventos 200
  con 200 features y estadísticas 200 con recuento 200. Los preflights
  OPTIONS de los dos endpoints desde ambos orígenes exactos de Netlify
  devolvieron HTTP 400 `Disallowed CORS origin`: causa concreta que impedía
  al navegador cargar los datos.
- Se añadió a `.env` ambos orígenes HTTPS de Netlify, conservando
  `http://localhost:4200` y `http://127.0.0.1:4200`, y se recreó solo
  `api` con `docker compose up -d --no-deps --force-recreate api`. La API
  quedó `healthy`; ngrok siguió apuntando al puerto 8000. Después, los
  preflights de eventos y estadísticas desde ambos orígenes dieron HTTP 200
  con `Access-Control-Allow-Origin` exacto. Los GET con origen y encabezado
  de ngrok dieron HTTP 200 y el mismo encabezado CORS. El preflight del
  origen local también siguió en 200.
- En una muestra tras la corrección: 200 features, 200 IDs únicos y 200
  coordenadas aptas para dibujar; `metadata.total=200`,
  `estadisticas.count=200`, suma por país/hora/magnitud/profundidad=200.
  El componente usa ese recuento para puntos e indicador y limita la tabla
  a las primeras 100 filas. Una consulta posterior devolvió 199, coherente
  con el feed live y la ventana móvil. No hubo navegador disponible (`[]`),
  así que la concordancia visual del panel queda para David. El acceso
  sin sesión a Netlify sigue dando 401; no se cambió el despliegue ni sus
  ajustes de acceso. No se repitió el histórico ni se hizo commit o push.

## Punto de reanudación para otro agente (16-11-2026)

- **Rama y Git.** Trabajar en `002-ingesta-usgs-persistencia`; `main` no se ha
  fusionado. Al iniciar la revisión para PR, el commit local y remoto era
  `2847ce1` y el árbol estaba limpio. La auditoría previa de 56 candidatos encontró cero archivos binarios,
  cero archivos mayores de 1 MiB y cero coincidencias de patrones de
  secretos de alta confianza. `.env`, `.netlify/`, originales históricos, volúmenes locales,
  `node_modules` y builds quedan fuera de Git. Comprobar `git status` y el
  hash final del cierre al retomar.
- **Arquitectura y arranque.** `compose.yaml` define cinco servicios:
  `producer` (USGS → Kafka), `kafka`, `consumer` (validación/geografía →
  PostgreSQL), `postgres` y `api` (FastAPI). Angular/Leaflet se sirve por
  Netlify; ngrok en el PC lleva HTTPS a `127.0.0.1:8000`. En Windows nuevo:
  copiar `.env.example` a `.env`, configurar el origen Netlify real, ejecutar
  `docker compose config --quiet`, `docker compose up --build -d`,
  `docker compose ps`; en `frontend/`, `npm ci` y `npm run build` o `npm start
  -- --host 127.0.0.1 --poll 2000`. Los originales históricos están fuera de
  Git; no lanzar `load-historical` ni `process-historical` para esta revisión.
  La guía se contrastó con Compose y build, pero no se ejecutó una instalación
  limpia en otro equipo Windows.
- **URLs y configuración.** Panel principal público
  `https://stellar-basbousa-cee41b.netlify.app/`, despliegue
  `https://6afb43dd955ba50ee86baace--stellar-basbousa-cee41b.netlify.app/`,
  API `https://sapling-unlearned-blush.ngrok-free.dev`, salud `/api/salud`.
  Ambas páginas y ambos `config.json` respondieron HTTP 200 sin sesión; el
  JSON público usa esa base HTTPS. La ruta SPA de prueba respondió 200.
  El `.env` **local** conserva los dos orígenes de desarrollo y autoriza el
  principal y el del despliegue; nunca incluir `.env` en Git. ngrok confirmó
  destino `http://localhost:8000`. El sitio sirve el HTML aun si el backend
  local se apaga, pero los datos requieren PC, Docker y túnel activos.
- **Decisiones de David.** Varias coincidencias geográficas: menor
  `ADM0_A3` y marca de ambigüedad; originales live: retención de 30 días;
  aviso de frescura: 10 minutos. El replay usa topic y tablas separados,
  conserva fecha original y fecha de reenvío. David comunicó la revisión
  anterior de filtros USA/replay y aportó ahora capturas en incógnito de mapa
  con círculos, indicador 192, gráficos por país/hora y tabla con filas;
  enlaces y atribución en `docs/ACEPTACION.md`.
- **Pruebas de esta sesión.** Cinco servicios `healthy`, Compose válido, API
  local/túnel con salud/eventos/estadísticas HTTP 200; CORS OPTIONS desde el
  origen principal HTTP 200 para ambos endpoints y encabezado de ngrok.
  Ventana UTC compartida `min_mag=4`: eventos=estadísticas=13, histórico
  comparable=18.302; replay enero 2025=10. SQL confirmó 18.302 históricos,
  783 live reales acumulados y 10 replay separados. `npm run build` (límite
  120 s), aceptación, contrato de filtros, dos pruebas Node y secuencia fuera
  de orden con rollback: exit 0. La captura de David coincide con los
  recuentos de la ejecución local (USA 163, sin país 20). El navegador del
  agente no estuvo disponible (`[]`); no atribuirle la prueba visual.
- **Corrección durante el cierre.** El productor consultaba USGS cada minuto,
  pero la API confundía última consulta correcta con último run del
  consumidor. Cuando `published=0` mostraba falsa antigüedad. El productor
  guarda ahora atómicamente `latest-live-fetch.json` (ignorado por Git); la
  API lo lee mediante mount de solo lectura. Se reconstruyeron únicamente
  productor y API; salud separa `source_last_fetch` e `ingestion`, y eventos
  publica `last_ingestion` desde la consulta USGS. Se observó avance de la
  marca con `published=0`. No se repitió ninguna carga histórica.
- **Rúbrica.** Extracción: fuentes, automatización, tipos y unidades en
  README/diccionario y manifestación previa de 12 meses. Calidad: seis
  dimensiones, antes/después, reglas y límites en `ANALISIS-CALIDAD.md`.
  Modelado: grano, claves, unión por polígono, índices e idempotencia en
  `MODELO-DATOS.md` y prueba fuera de orden. Análisis: ventana, distribuciones,
  comparación equivalente y tres conclusiones fechadas; HTTP y capturas de
  David confirman parte del panel. Reflexión: tres tamaños, índice frente a
  secuencial, costes supuestos y límites en
  `ANALISIS-COMPLEJIDAD-COSTES.md`. Las mediciones históricas y de rendimiento
  se revisaron como evidencia previa, sin repetir las cargas.
- **Pendientes y siguiente acción exacta.** T005/T006 siguen abiertos solo
  para ver completas las distribuciones y el aviso visual al cerrar/reabrir
  ngrok, y probar el sitio desde otro dispositivo. David debe abrir la URL
  principal en otro dispositivo con el PC, los cinco servicios y ngrok activos,
  comprobar mapa/indicador/tabla y guardar una captura; después provocar una
  caída controlada del túnel, observar aviso y recuperación, y reabrirlo.
  No instalar Hugo ni modificar el despliegue por fallos antiguos. No hay
  evidencia de disponibilidad permanente fuera del equipo local.

### Revisión acotada para PR (16-11-2026)

- `docker compose ps` mostró los cinco servicios `running/healthy`; `docker
  compose config --quiet` terminó con exit 0. ngrok local confirmó el túnel
  HTTPS hacia `http://localhost:8000`.
- `/api/salud`, `/api/eventos` y `/api/estadisticas` respondieron HTTP 200
  tanto en `127.0.0.1:8000` como por ngrok con el encabezado exigido; una
  instantánea dio 199 eventos y 199 en estadísticas. Salud mostró
  `source_last_fetch=2026-11-16T22:07:50.800256+00:00`.
- Netlify principal sin sesión: `/` HTTP 200 con Angular y `/config.json`
  HTTP 200 con `mode=api`, URL HTTPS del túnel y `skipNgrokWarning=true`.
  Preflight OPTIONS desde ese origen hacia eventos y estadísticas: HTTP 200,
  `Access-Control-Allow-Origin` exacto.
- Tras aclarar el README, `npm run build` terminó con exit 0 (generación
  2,887 s, límite 120 s; advertencia CommonJS de Leaflet). `tests/acceptance.py`,
  `tests/filter_contract.py`, `frontend/tests/filter-query.mjs` y
  `frontend/tests/component-state.mjs` terminaron con exit 0 y límites de
  30–90 s. La aceptación confirmó histórico 18.302 y replay 10; los filtros
  mostraron 167 USA, 24 sin país y 13 con magnitud ≥4 en una ventana live
  móvil. No se ejecutó ninguna descarga ni carga histórica.
- La guía Windows explica ahora explícitamente que `docker compose up
  --build -d` arranca live y que un equipo nuevo necesita los comandos
  adicionales de descarga y procesamiento para reconstruir el histórico.
  No se simuló una instalación limpia en otro equipo.
- El navegador del agente siguió sin estar disponible (`[]`). Las capturas
  anteriores de David acreditan mapa, indicador y tabla en incógnito, pero
  no distribuciones completas ni aviso visual de caída/recuperación. T005 y
  T006 permanecen abiertos; tampoco se ha probado otro dispositivo.
