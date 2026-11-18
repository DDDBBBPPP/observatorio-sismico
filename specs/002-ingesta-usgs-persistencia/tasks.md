---

description: "Tareas de ingesta USGS, validación geográfica y persistencia idempotente"
---

# Tasks: Ingesta USGS y persistencia trazable

**Input**: Design documents from
`/specs/002-ingesta-usgs-persistencia/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/, quickstart.md

**Alcance**: feed USGS reciente, histórico anual 2025, originales,
validación, geografía, persistencia híbrida, versiones, cuarentena y
evidencias de calidad. API sísmica, Angular, Netlify, ngrok y replay quedan
fuera.

## Phase 1: Setup

**Purpose**: preparar dependencias, configuración y directorios sin cambiar el
contrato de los cinco servicios del hito 001.

- [ ] T001 Añadir dependencias reproducibles con versiones fijadas: cliente
  HTTP, PostgreSQL y GeoPandas/Shapely a `producer/requirements.txt` y
  `consumer/requirements.txt`, sin eliminar `aiokafka`.
- [x] T002 [P] Añadir en `.env.example` las variables de USGS, topic live,
  frecuencia, timeouts, reintentos, periodo histórico y rutas locales de
  originales, sin credenciales reales.
- [ ] T003 [P] Crear `tests/unit/`, `tests/integration/`,
  `evidence/002-ingesta-usgs-persistencia/` y las reglas de exclusión para
  descargas USGS, volúmenes y evidencias locales en `.gitignore`.
- [ ] T004 [P] Actualizar `producer/Dockerfile` y `consumer/Dockerfile` para
  incluir las dependencias geográficas y el catálogo montado sin añadir un
  sexto servicio Compose.
- [x] T005 [P] Añadir a `compose.yaml` los volúmenes, variables y mounts
  necesarios para originales y evidencias, manteniendo exactamente
  `producer`, `kafka`, `consumer`, `postgres` y `api`.

## Phase 2: Foundational

**Purpose**: establecer contratos, esquema híbrido y utilidades compartidas
que bloquean los incrementos de ingesta.

- [x] T006 Crear `consumer/src/migrations/001_ingestion_schema.sql` con las
  tablas `ingestion_run`, `source_response`, `event_version`,
  `event_current` y `quarantine_record`, usando JSONB para originales y
  restricciones únicas en `event_id` y `(event_id, updated)`.
- [x] T007 Añadir en `consumer/src/migrations/001_ingestion_schema.sql` los
  índices justificados para intervalos temporales, país y fecha, versiones,
  ejecuciones y motivos de cuarentena, dejando su consulta objetivo
  documentada. Se cubren consultas por evento/versión, fecha y país del
  estado actual, ejecuciones por estado/fecha y respuestas por ejecución.
- [x] T008 [P] Implementar `consumer/src/persistence.py` con transacciones,
  upsert idempotente, actualización solo para `updated` posterior y
  confirmación diferenciada de `accepted`, `duplicate_version`,
  `older_version`, `quarantined` y `failed`.
- [x] T009 [P] Implementar `consumer/src/validation.py` con reglas para
  campos USGS, tipos, fechas, unidades, coordenadas finitas y valores nulos,
  conservando el payload original y un motivo explícito de rechazo.
- [x] T010 [P] Implementar `consumer/src/geography.py` para cargar el catálogo
  `frontend/public/datos/paises.geojson` en WGS84/EPSG:4326 y documentar en
  código la regla de frontera, varias coincidencias y «Sin país asignado».
- [x] T011 Crear `producer/src/ingestion_state.py` para registrar consultas,
  hashes, respuestas, versiones observadas y estados de publicación sin
  depender solo de memoria.
- [ ] T012 [P] Añadir pruebas unitarias en
  `tests/unit/test_validation.py`, `tests/unit/test_persistence_rules.py` y
  `tests/unit/test_geography.py` para las reglas y entidades fundamentales.

**Checkpoint**: la base de datos, los contratos de procesamiento y las reglas
de validación/geografía están listos antes de conectar USGS.

## Phase 3: User Story 1 - Ingerir novedades reales de USGS (Priority: P1) 🎯 MVP

**Goal**: procesar un evento real del feed reciente, publicarlo con
`mode=live` y persistirlo en PostgreSQL.

**Independent Test**: ejecutar una consulta controlada del feed, observar el
original y sus metadatos, verificar el mensaje del topic live y comprobar una
fila actual, una versión y su procedencia en PostgreSQL.

### Tests for User Story 1

- [ ] T013 [P] [US1] Añadir `tests/contract/test_usgs_source.py` para validar
  campos, unidades, ventana móvil, filtro `earthquake` y metadatos de
  respuesta definidos en `contracts/usgs-source.md`.
- [ ] T014 [P] [US1] Añadir
  `tests/integration/test_live_event_to_postgres.py` para comprobar el
  recorrido de un evento USGS real desde el feed hasta `event_current` y
  `event_version`.

### Implementation for User Story 1

- [x] T015 [P] [US1] Implementar `producer/src/usgs_client.py` con consulta
  configurable del feed `all_day.geojson`, timeout, HTTP 429/5xx, JSON
  inválido, reintentos progresivos y registro explícito de errores.
- [x] T016 [P] [US1] Implementar `producer/src/live_ingest.py` para filtrar
  `properties.type == "earthquake"`, conservar exclusiones, comparar
  `(id, updated)` y generar metadatos `load_type=live_feed`.
- [x] T017 [US1] Extender `producer/src/event_model.py` para generar el
  sobre `observatorio.event-envelope.v1` con `source=usgs`, `mode=live`,
  `event_id`, `ingested_at`, evento original y procedencia.
- [x] T018 [US1] Extender `producer/src/main.py` con una activación live
  controlada que publique solo novedades y revisiones confirmadas en el topic
  live separado del topic sintético.
- [x] T019 [US1] Actualizar `compose.yaml` y `producer/src/topic_config.py`
  para declarar y validar el topic live sin alterar la restricción 1/1 del
  topic sintético ni crear un servicio adicional.
- [x] T020 [US1] Extender `consumer/src/main.py` para seleccionar el topic
  live, conservar `run_id` y procedencia y delegar validación/persistencia sin
  mezclar mensajes sintéticos.
- [ ] T021 [US1] Registrar en
  `evidence/002-ingesta-usgs-persistencia/<run_id>/` la respuesta original,
  consulta, mensaje live, estado de Kafka, resultado PostgreSQL y timestamps;
  documentar el resultado observado en `quickstart.md`.

**Checkpoint**: un evento real válido llega a PostgreSQL y se distingue del
topic sintético, sin endpoints de API todavía.

## Phase 4: User Story 3 - Validar, enriquecer y persistir versiones (Priority: P1)

**Goal**: demostrar idempotencia, revisiones, cuarentena y geografía mediante
casos reales y sintéticos separados.

**Independent Test**: procesar una versión inicial, un duplicado, una revisión,
una versión antigua, un nulo, una coordenada inválida y un evento marítimo;
comprobar estado actual, historial, cuarentena y asignación geográfica tras
reiniciar el consumidor.

### Tests for User Story 3

- [ ] T022 [P] [US3] Completar `tests/integration/test_duplicate_versions.py`
  con la secuencia inicial, repetición, revisión posterior y versión antigua,
  verificando una fila actual y dos versiones distintas.
- [ ] T023 [P] [US3] Completar
  `tests/integration/test_quarantine_and_resume.py` con nulos, JSON
  incompleto, coordenadas inválidas y continuación tras cuarentena.
- [ ] T024 [P] [US3] Completar
  `tests/integration/test_geography_assignment.py` con punto en país,
  marítimo, frontera y múltiples coincidencias según la regla documentada.
- [ ] T025 [US3] Añadir una prueba de reinicio en
  `tests/integration/test_offset_after_persist.py` que fuerce reentrega y
  compruebe que no duplica efectos antes de confirmar el offset.

### Implementation for User Story 3

- [x] T026 [US3] Integrar `consumer/src/validation.py` y
  `consumer/src/persistence.py` en `consumer/src/main.py`, confirmando el
  offset solo después de persistir el evento o la cuarentena.
- [x] T027 [US3] Persistir en `consumer/src/persistence.py` los originales,
  transformaciones, tiempos UTC, fuente, `mode`, `run_id` y referencia a
  `source_response` sin sobrescribir versiones anteriores.
- [x] T028 [US3] Implementar en `consumer/src/geography.py` el punto
  `[longitud, latitud]` dentro de polígonos WGS84, conservando país nulo y
  razón observable cuando no haya asignación.
- [x] T029 [US3] Implementar en `consumer/src/persistence.py` la cuarentena
  durable con original JSONB, etapa, `reason_code`, detalle, fecha y
  referencias al mensaje y ejecución.
- [ ] T030 [US3] Añadir en `producer/src/live_ingest.py` el registro separado
  de exclusiones por tipo no `earthquake`, fallos de fuente y versiones
  omitidas, sin borrar el estado válido anterior.
- [ ] T031 [US3] Añadir a `compose.yaml` y a los healthchecks los límites de
  espera, reintentos y disponibilidad de PostgreSQL necesarios para que el
  consumidor no confirme mensajes sin persistencia.
- [ ] T032 [US3] Conservar en
  `evidence/002-ingesta-usgs-persistencia/quality/` los casos sintéticos
  dañados separados de datos reales, con entradas, salidas, motivos y
  resultado observado.

**Checkpoint**: duplicados, revisiones, nulos, cuarentena, geografía y
reinicios tienen pruebas reproducibles y no alteran silenciosamente el estado.

## Phase 5: User Story 2 - Cargar un histórico anual reproducible (Priority: P2)

**Goal**: descargar una vez el histórico completo de 2025 por meses,
reutilizar originales y aplicar las mismas reglas de persistencia.

**Independent Test**: ejecutar la carga mensual, comprobar metadatos e
intervalos, deduplicar límites, reiniciar y reconstruir desde los originales
sin descargar de nuevo.

### Tests for User Story 2

- [ ] T033 [P] [US2] Añadir
  `tests/integration/test_historical_monthly_load.py` para verificar meses,
  subdivisión por límite, deduplicación de límites, `load_type` y recuentos.
- [ ] T034 [P] [US2] Añadir
  `tests/integration/test_historical_rebuild_from_originals.py` para
  reconstruir tras reinicio sin nuevas descargas y conservar procedencia.

### Implementation for User Story 2

- [x] T035 [US2] Implementar `producer/src/historical_loader.py` con consultas
  mensuales de 2025, subdivisión si se supera el límite USGS, conservación de
  respuestas y metadatos `load_type=historical_initial`.
- [x] T036 [US2] Reutilizar en `producer/src/historical_loader.py` las mismas
  reglas de normalización, deduplicación `(event_id, updated)` y persistencia
  de estado que el feed live; identificar el batch fuera de Kafka con
  `mode=historical` y `load_type=historical_initial` en PostgreSQL.
- [x] T037 [US2] Añadir un comando batch documentado en
  `producer/src/main.py` que procese originales conservados y registre
  `period=2025`, intervalo, filtros, `run_id` y recuentos.
- [x] T038 [US2] Añadir en `consumer/src/main.py` el procesamiento de registros
  batch con la misma validación, geografía, cuarentena y persistencia que live.
- [x] T039 [US2] Conservar en
  `evidence/002-ingesta-usgs-persistencia/historical/` consultas, respuestas,
  hashes, intervalos, recuentos, duplicados de frontera y resultado final sin
  incluir descargas grandes en Git.

**Checkpoint**: el histórico 2025 es reproducible, auditable y se identifica
como `mode=historical` en PostgreSQL, sin presentarlo como recepción reciente.

## Phase 6: Polish y comprobación transversal

- [ ] T040 [P] Crear `evidence/002-ingesta-usgs-persistencia/quality/README.md`
  con denominador, código o consulta, resultados antes/después, acciones y
  limitaciones para completitud, unicidad, validez, consistencia, actualidad y
  exactitud; incluir mediciones de rendimiento con al menos tres tamaños de
  entrada.
- [x] T041 [P] Actualizar `README.md` y
  `specs/002-ingesta-usgs-persistencia/quickstart.md` con instalación Windows,
  feed live, carga batch, comprobaciones PostgreSQL, política de retención de
  originales, repetición live desde archivos y limpieza de evidencias.
- [ ] T042 [P] Revisar `compose.yaml`, `.env.example`, Dockerfiles y
  requirements para confirmar cinco servicios, topic live separado, ausencia
  de secretos y exclusión de descargas, volúmenes y cachés.
- [ ] T043 Ejecutar todos los escenarios de
  `specs/002-ingesta-usgs-persistencia/quickstart.md`, registrar códigos y
  resultados observados y no marcar como superada ninguna prueba no ejecutada.
- [ ] T044 Revisar trazabilidad FR/SC y contratos en
  `specs/002-ingesta-usgs-persistencia/` y dejar explícitamente fuera API,
  Angular, Netlify, ngrok y replay.
- [x] T045 [P] Documentar en `specs/002-ingesta-usgs-persistencia/quality.md`
  una medición reproducible con tres tamaños de entrada, métricas, filtros,
  denominadores y limitaciones, conforme a la constitución.
- [ ] T046 [US1] Implementar en `producer/src/live_replay.py` la repetición
  del último original live conservado mediante sus metadatos, sin usar
  `mode=historical` ni fijar la topología futura de replay.
- [ ] T047 [US1] Registrar en
  `evidence/002-ingesta-usgs-persistencia/<run_id>/` el tiempo total de
  quickstart y la política aplicada a los originales conservados.

- [x] T048 Corregir el manifiesto histórico para que cada URL y original
  contenga año completo mundial, `minmagnitude=4` y `eventtype=earthquake`;
  conservar el manifiesto previo sin usarlo para comparar.
- [x] T049 Marcar persistentemente `controlled-*` como sintético y excluirlo
  de API, estadísticas y conclusiones mediante migración reproducible.
- [x] T050 Ejecutar el batch histórico corregido con modo `historical`,
  comprobar contadores finales y conservar su progreso.
- [x] T051 Implementar y comprobar `/api/eventos`, `/api/estadisticas` y
  `/api/salud` con filtros compartidos, paginación, errores y CORS.
- [x] T052 Completar ingesta periódica live y replay Kafka aislado, con
  timestamps, duplicados y revisiones.
- [x] T053 Completar panel Angular, tabla, filtros, indicadores, aviso de
  antigüedad y refresco de 60 segundos.
- [ ] T054 Ejecutar aceptación integrada y completar documentación de entrega.

### Revisión del PR #1 (18-11-2026)

- [x] T055 Usar `event_id` como clave Kafka en live y replay; verificar el
  contrato del mensaje y mantener lectura de sobres anteriores.
- [x] T056 Validar cobertura, originales, recuentos y versiones del manifiesto
  histórico real; reconocer el run antiguo completado sin checkpoints y sin
  repetir sus 18.302 registros.
- [x] T057 Probar versión duplicada, posterior, antigua, reinicio y mensaje
  defectuoso en Kafka; confirmar cuarentena y continuidad del consumidor.
- [x] T058 Referenciar con SHA-256 el GeoJSON original completo para no
  repetirlo en cada mensaje live; conservar Feature y procedencia verificable.
- [x] T059 Mejorar panel Angular y aclarar última consulta USGS frente al
  último terremoto del filtro; build local y pruebas de filtros superados.
- [x] T060 Crear comprobador cada cinco minutos y realizar muestra breve.
- [ ] T061 Observar las 24 horas completas, revisar el archivo JSONL y evaluar
  salud, errores, recuentos y retraso sin declarar éxito antes de tiempo.
- [ ] T062 Capturar y revisar visualmente el antes/después en navegador; el
  navegador integrado no estuvo disponible en esta sesión.
- [x] T063 Publicar el nuevo frontend en el proyecto Netlify existente
  (`6afcef8a47d80fa7d8a964ed`) y comprobar bundle público, configuración,
  API por ngrok y CORS. Un build local posterior sigue requiriendo despliegue.
- [x] T064 Conservar una instantánea `all_day.geojson` con SHA-256 y auditar
  una ventana UTC fija frente a eventos, estadísticas y BD, con y sin magnitud
  ≥4; verificar muestras USA, CAN y marítimas mediante polígonos.
- [x] T065 Mostrar nombres españoles y códigos `ADM0_A3` en gráfico, mapa y
  tabla, porcentaje por país y desglose de «Otros»; probar cambio conjunto
  de mapa, gráficos y tabla al aplicar filtros.
- [x] T066 Iniciar el monitor 24 h en segundo plano y verificar su primera
  muestra; incorporar evaluador de huecos, salud, frescura y lag.
- [x] T067 Revisar visualmente el despliegue actual en escritorio y móvil con
  Chrome headless, capturas públicas y manifiesto UTC; API y panel coincidieron.

### Vista mundial inicial y monitor definitivo (18-11-2026)

- [x] T068 Congelar una nueva instantánea `all_day.geojson` con hash y ventana
  UTC móvil de 24 h; contrastar IDs `earthquake`, API, estadísticas, PostgreSQL
  y suma completa por países en todos los registros y magnitud ≥4.
- [x] T069 Explicar el 189/236 USA observado y 0/22 con magnitud ≥4, el ID
  persistido de una captura anterior, la cobertura desigual de redes y el
  significado de «Sin país asignado» con evidencia reproducible.
- [x] T070 Reducir cabecera y menú; mostrar arriba periodo UTC, última consulta
  USGS y métricas; iniciar en «Comparación mundial · magnitud ≥4» y ofrecer
  «Todos los registros comunicados por USGS» como vista rápida.
- [x] T071 Probar cambio entre vistas, USA, Todos, umbral ≥4, mapa, gráficos,
  tabla, replay y error con pruebas del componente; formatear fechas y
  profundidades sin residuos de coma flotante.
- [x] T072 Construir Angular, publicar el build en Netlify existente
  (`6afcf624552b6cba53bcfec2`) y comprobar assets públicos, API y CORS.
- [x] T073 Cerrar el monitor previo de seis muestras y empezar medición nueva
  tras estabilizar/publicar; primera muestra sana a las 00:50:16 UTC.
- [x] T074 Verificar visualmente escritorio y móvil con Chrome headless local y
  capturas; el navegador integrado no tuvo sesiones disponibles.
- [ ] T075 Completar 24 horas reales desde la nueva medición y revisar huecos,
  salud, frescura, errores, recuentos y lag.

### Profundidad, trazabilidad y revisión visual (18-11-2026)

- [x] T076 Añadir límites de profundidad inclusivos, negativos y errores claros
  a ambos endpoints, panel y comparación histórica; contrastar live/replay
  con PostgreSQL y nulos mediante tabla temporal.
- [x] T077 Resaltar el polígono Natural Earth del país seleccionado, encuadrar
  su territorio cuando no hay eventos y no dibujar polígono para UNASSIGNED.
- [x] T078 Mostrar trazabilidad live verificable: consulta USGS, ID nuevo,
  persistencia, revisiones y cuarentena; duplicados/lag sin contador fiable
  como «no medido».
- [x] T079 Aplicar tema azul noche y verificar Chrome headless en 375, 768 y
  1440 px, filtros, mapa, gráficos, tabla, replay y caída/recuperación API;
  conservar 16 capturas locales y manifiesto UTC.
- [x] T080 Verificar el nuevo build `main-GIBIKXGC.js` publicado en Netlify
  (`6afd9c835bbf58fb34663797`), API/CORS por HTTP y navegador público a
  1440/375 px; guardar capturas y manifiesto UTC.
- [ ] T081 Completar y evaluar 24 horas reales. David autorizó la nueva
  medición, iniciada el 18-11-2026 a las 15:03:04 UTC; la primera muestra
  fue sana. La ejecución anterior conserva seis muestras exploratorias.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: independiente; prepara dependencias y rutas.
- **Foundational (Phase 2)**: depende de Setup y bloquea las historias.
- **US1 (Phase 3)**: depende de Foundational; es el MVP.
- **US3 (Phase 4)**: depende de US1 para probar mensajes reales y persistencia.
- **US2 (Phase 5)**: depende de las reglas estabilizadas en US1 y US3.
- **Polish (Phase 6)**: depende de los incrementos que se quieran declarar
  ejecutados.

### User Story Dependencies

- **US1 (P1)**: depende de Phase 2; no depende de la carga histórica.
- **US3 (P1)**: depende de Phase 2 y usa el contrato de US1, pero sus casos
  sintéticos son independientes de una descarga anual.
- **US2 (P2)**: depende de la validación y persistencia de US3 para reutilizar
  exactamente las mismas reglas.

### Parallel Opportunities

- T002-T005 pueden ejecutarse en paralelo después de confirmar la estructura.
- T008-T011 pueden ejecutarse en paralelo después de acordar el esquema.
- T013-T014 son pruebas independientes antes de T015-T020.
- T022-T025 son escenarios independientes de persistencia y geografía.
- T033-T034 pueden prepararse en paralelo antes del loader.
- T040-T042 son revisiones documentales independientes antes de T043.

## Implementation Strategy

### MVP First (US1 only)

1. Completar Setup y Foundational.
2. Implementar el cliente live y un mensaje real hasta PostgreSQL.
3. Ejecutar T013-T021 y detenerse para validar el evento real.

### Incremental Delivery

1. Añadir US3: duplicados, revisiones, validación, cuarentena y geografía.
2. Añadir US2: carga mensual 2025 y reconstrucción desde originales.
3. Ejecutar evidencias de calidad y quickstart completo.
4. Mantener API sísmica, frontend, Netlify, ngrok y replay para hitos posteriores.
