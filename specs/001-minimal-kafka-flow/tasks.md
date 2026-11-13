---

description: "Tareas del primer hito: infraestructura Docker y recorrido sintético productor-Kafka-consumidor"
---

# Tasks: Infraestructura mínima de cinco servicios

**Input**: Artefactos de diseño de `specs/001-minimal-kafka-flow/`

**Branch**: `001-flujo-kafka-minimo`

**Alcance**: este hito cubre cinco servicios Docker Compose, el arranque
honesto, un evento sintético y su comprobación extremo a extremo. Quedan fuera
USGS real, persistencia de terremotos, endpoints sísmicos de consulta, Angular,
Netlify, ngrok y replay.

**Nota de ubicación**: las tareas conservan sus identificadores y trazabilidad,
pero la implementación final sitúa `producer/`, `consumer/` y `api/` en la
raíz, al nivel de `frontend/`, y `tools/verifier/` como herramienta externa.
Kafka y PostgreSQL continúan definidos como imágenes oficiales en
`compose.yaml`.

**Pruebas**: no se añaden tareas TDD independientes; la especificación exige
escenarios de aceptación ejecutables y evidencias reproducibles.

## Phase 1: Setup

**Purpose**: preparar la estructura de los cinco servicios sin implementar aún
la lógica real de terremotos.

- [X] T001 Crear la estructura `producer/`, `consumer/`, `api/`, `tools/verifier/`, `evidence/001-minimal-kafka-flow/` y los archivos base `compose.yaml` y `.env.example` en la raíz; `tools/verifier/` es una herramienta de comprobación y no un sexto servicio Compose.
- [X] T002 [P] Crear `producer/Dockerfile` y `producer/requirements.txt` para una imagen Python independiente con `aiokafka` y sus dependencias fijadas.
- [X] T003 [P] Crear `consumer/Dockerfile` y `consumer/requirements.txt` para una imagen Python independiente con `aiokafka` y sus dependencias fijadas.
- [X] T004 [P] Crear `api/Dockerfile` y `api/requirements.txt` para una imagen Python independiente con FastAPI, Uvicorn y sus dependencias fijadas.
- [X] T005 [P] Definir `.env.example` con nombres de servicio (`kafka`, `postgres`, `api`), `KAFKA_BOOTSTRAP_SERVERS`, topic de prueba, credenciales locales de PostgreSQL no reales y parámetros de comprobación, sin incluir secretos reales.

## Phase 2: Foundational

**Purpose**: configurar la red, ciclo de vida y dependencias que bloquean las
dos historias de usuario.

- [X] T006 Configurar `compose.yaml` con exactamente cinco servicios (`producer`, `kafka`, `consumer`, `postgres`, `api`), red interna por nombres de servicio, `restart: unless-stopped` y el bind mount `./evidence/001-minimal-kafka-flow:/evidence` en `producer` y `consumer`; publicar solo `127.0.0.1:8000:8000` para `api`, sin publicar Kafka ni PostgreSQL al host.
- [X] T007 Configurar en `compose.yaml` la imagen fijada `apache/kafka:3.9.0` en un único nodo KRaft con broker y controlador en el mismo contenedor, sin ZooKeeper, y especificar que el productor creará y validará automáticamente el topic de prueba con exactamente una partición y una réplica mediante el cliente administrativo de `aiokafka`.
- [X] T008 Configurar en `compose.yaml` la imagen fijada `postgres:16-alpine`, un volumen persistente para PostgreSQL y `pg_isready` como comprobación de salud; no crear tablas ni afirmar persistencia de eventos en este hito.
- [X] T009 Configurar en `compose.yaml` volumen y retención explícita para los datos de Kafka, incluyendo la política de retención del topic de prueba, sin exponer el broker mediante el túnel.
- [X] T010 Definir en `compose.yaml` `depends_on` con condiciones de salud, reintentos y límites de espera para que el orden de arranque no se interprete como disponibilidad.
- [X] T011 Implementar la configuración común de estados `starting`, `ready`, `completed`, `failed` y `unavailable` en `producer/src/status.py`, `consumer/src/status.py` y `api/src/status.py`, incluyendo timestamps y síntoma observable en caso de fallo.
- [X] T012 Añadir a `compose.yaml` la comprobación de salud de FastAPI mediante `GET http://127.0.0.1:8000/api/salud` dentro del contenedor y publicar únicamente `127.0.0.1:8000:8000` al host, sin presentar una ingesta inexistente como realizada.
- [X] T013 Añadir a `producer/src/healthcheck.py` una comprobación real del productor: proceso persistente vivo, resolución de `kafka`, conexión de cliente `aiokafka` al broker, creación o validación idempotente del topic con exactamente una partición y una réplica, y operación de metadatos sin publicar el evento sintético; un `sleep`, proceso ocioso o contenedor `running` sin conectividad no puede producir `ready`.
- [X] T014 Añadir a `consumer/src/healthcheck.py` una comprobación de proceso persistente y conexión al broker, y definir en `compose.yaml` reintentos para que el consumidor no se declare `ready` antes de Kafka.
- [X] T015 Implementar `api/src/main.py` con `GET /api/salud`, respuesta de estado técnico y escucha en `0.0.0.0:8000`; no implementar `/api/eventos` ni otros endpoints sísmicos.

**Checkpoint**: Compose y sus comprobaciones deben estar listas para validar el
arranque de los cinco servicios antes de enviar mensajes.

## Phase 3: User Story 1 - Demostrar el recorrido de un evento de prueba (Priority: P1) 🎯 MVP

**Goal**: arrancar los cinco servicios, activar exactamente un evento sintético
dentro del productor existente, conservar publicación y recepción por separado
y demostrar `receive_confirmed` solo mediante comparación completa.

**Independent Test**: con Docker Desktop y las imágenes ya disponibles
localmente, ejecutar `docker compose up --build -d`, observar los cinco
estados, activar el productor con
`docker compose exec -T producer python /app/src/main.py publish-test` y
comparar los dos JSON de la misma ejecución por `run_id` y por todos sus campos.

### Implementation for User Story 1

- [X] T016 [US1] Implementar `producer/src/event_model.py` con el envoltorio JSON `observatorio.test-envelope.v1` y los campos obligatorios `schema`, `run_id`, `source=synthetic-test`, `mode=test`, `created_at` y `event`.
- [X] T017 [US1] Implementar en `producer/src/event_model.py` el evento sintético con `event_id` no vacío y único por ejecución, `event_type=test-earthquake`, timestamps sintéticos en milisegundos UTC, `mag` numérica o nula, `mag_type`, `place` identificando la prueba y `coordinates` de tres números en orden `[longitud, latitud, profundidad_km]`.
- [X] T018 [US1] Implementar `producer/src/main.py` como proceso persistente del servicio `producer`, con comando de espera controlada y `ready` únicamente después de la comprobación de Kafka de T013; no publicar automáticamente al arrancar.
- [X] T019 [US1] Implementar en `producer/src/main.py` el proceso persistente con `python /app/src/main.py serve` y la activación controlada con `python /app/src/main.py publish-test`, ejecutable mediante `docker compose exec -T producer python /app/src/main.py publish-test`; generar `run_id`/`event_id`, publicar al topic de prueba y conservar en `/evidence/<run_id>/producer.json` el JSON exacto y el acuse.
- [X] T020 [US1] Distinguir en `producer/src/main.py` `send_attempted`, `send_confirmed` y `send_failed`; `send_confirmed` solo puede emitirse después de la confirmación de Kafka y nunca equivale a recepción.
- [X] T021 [US1] Implementar `consumer/src/main.py` como consumidor persistente del topic de prueba, registrando en `/evidence/<run_id>/consumer.json` el JSON exacto recibido, su `run_id`, timestamp de recepción y estado, sin comparar contra un original que el consumidor no posee.
- [X] T022 [US1] Configurar en `consumer/src/main.py` la identificación explícita del mensaje como prueba y el registro de todos los mensajes sintéticos recibidos por su propio `run_id`; el consumidor no conoce la ejecución actual y no descarta mensajes por una comparación externa.
- [X] T023 [US1] Añadir a `compose.yaml` el comando persistente de `producer` y el comando de `consumer`, sus variables de entorno, el topic separado y las conexiones internas por nombre de servicio; no añadir un sexto servicio para la activación.
- [X] T024 [US1] Ejecutar y documentar la comprobación de arranque de los cinco servicios en `evidence/001-minimal-kafka-flow/<run_id>/startup.txt` usando exactamente:

```powershell
docker compose up --build -d
docker compose ps
docker compose logs --no-log-prefix --tail=100 kafka postgres api producer consumer
curl.exe -fsS http://localhost:8000/api/salud
```

La evidencia debe distinguir `starting`, `ready`, `failed` y `unavailable`; `GET /api/salud` solo prueba el estado técnico de FastAPI.

- [X] T025 [US1] Ejecutar y documentar el flujo correcto en `evidence/001-minimal-kafka-flow/<run_id>/`, registrando el instante de inicio antes de activar:

```powershell
docker compose exec -T producer python /app/src/main.py publish-test
docker compose logs --no-log-prefix --since <inicio-ejecucion> consumer
```

Conservar el JSON y acuse del productor, el JSON del consumidor y el `run_id`; no declarar `receive_confirmed` todavía sin la comparación de T026.

- [X] T026 [US1] Implementar `tools/verifier/verify_event.py` y su ejecución documentada en `evidence/001-minimal-kafka-flow/<run_id>/verification.json` para seleccionar exactamente una evidencia del productor y una del consumidor por `run_id`, excluir registros anteriores al inicio de la ejecución y comparar `schema`, `run_id`, `source`, `mode`, `created_at` y todos los campos de `event`; emitir `receive_confirmed` solo si coinciden, o `receive_failed` con diferencia explícita.
- [X] T027 [US1] Documentar en `tools/verifier/README.md` y `specs/001-minimal-kafka-flow/quickstart.md` la separación de responsabilidades, el prerrequisito Python 3.14 o compatible y el comando exacto desde Windows con variables reales; un código 0 del productor no demuestra recepción. Incluir la copia de `consumer.json`, la alteración de un campo y la ejecución con `--consumer-json`, que debe producir `receive_failed` sin modificar la evidencia original.

**Checkpoint**: US1 es aceptable solo con cinco servicios observables, `GET
/api/salud` correcto, `send_confirmed` y `receive_confirmed` respaldado por la
comparación completa de la misma ejecución.

## Phase 4: User Story 2 - Repetir la comprobación de forma reproducible (Priority: P2)

**Goal**: repetir el hito en Windows y demostrar fallos deliberados sin
reiniciar inadvertidamente el componente detenido ni aceptar logs antiguos.

**Independent Test**: con Docker y las imágenes ya disponibles, repetir el
arranque, generar un nuevo `run_id`, activar por `exec`, obtener evidencias
aisladas y ejecutar las tres pruebas de fallo con resultados negativos
honestos.

### Implementation for User Story 2

- [X] T028 [P] [US2] Añadir a `quickstart.md` y `evidence/001-minimal-kafka-flow/README.md` los prerrequisitos Windows, indicando que el objetivo de diez minutos comienza con Docker e imágenes disponibles y no incluye clonado, descargas ni el primer build.
- [X] T029 [US2] Documentar en `quickstart.md` la repetición correcta con un `run_id` y `event_id` nuevos, registro de hora de inicio, JSON del productor, acuse Kafka, JSON del consumidor, comparación por todos los campos y exclusión de logs antiguos.
- [X] T030 [US2] Documentar y ejecutar la prueba de productor detenido en `evidence/001-minimal-kafka-flow/failures/producer-stopped.txt`:

```powershell
docker compose stop producer
docker compose exec -T producer python /app/src/main.py publish-test
```

El segundo comando debe fallar porque no existe un contenedor productor operativo; el procedimiento no debe ejecutar `docker compose up`, `start` ni recrearlo. Restaurar después con el arranque normal documentado, fuera de la prueba, y registrar la restauración por separado.

- [X] T031 [US2] Documentar y ejecutar la prueba de Kafka detenido en `evidence/001-minimal-kafka-flow/failures/kafka-stopped.txt`:

```powershell
docker compose stop kafka
docker compose exec -T producer python /app/src/main.py publish-test
```

La activación debe fallar al conectar o al obtener el acuse de Kafka; ningún comando de la prueba puede ejecutar `docker compose up`, `start` ni recrear Kafka. Restaurar después con el arranque normal documentado y registrar la restauración por separado.

- [X] T032 [US2] Documentar y ejecutar la prueba de consumidor detenido en `evidence/001-minimal-kafka-flow/failures/consumer-stopped.txt`:

```powershell
docker compose stop consumer
docker compose exec -T producer python /app/src/main.py publish-test
```

Puede existir `send_confirmed`, pero no puede existir `receive_confirmed` sin JSON del consumidor con el `run_id` actual; ningún log antiguo cuenta. Restaurar después con el arranque normal documentado y registrar la restauración por separado.

- [X] T033 [US2] Añadir a `evidence/001-minimal-kafka-flow/README.md` una matriz de cada prueba de fallo con comando, componente, síntoma esperado, resultado observado y restauración, confirmando que no se reinició inadvertidamente el componente detenido.
- [X] T034 [US2] Ejecutar la repetición completa descrita en `quickstart.md` con Docker e imágenes disponibles y conservar en `evidence/001-minimal-kafka-flow/repeat/` los estados de cinco servicios, `GET /api/salud`, JSON enviado, acuse, JSON recibido, verificación y tiempos.

**Checkpoint**: US2 es aceptable cuando otra persona puede repetir el flujo y
distinguir envío, recepción, fallo y restauración sin inferencias silenciosas.

## Phase 5: Polish y comprobación transversal

- [X] T035 [P] Revisar `compose.yaml`, `.env.example`, los tres Dockerfiles y los manifiestos Python para confirmar versiones fijadas, nombres de servicio, volúmenes, retención, salud, reintentos y ausencia de secretos.
- [X] T036 [P] Revisar `producer/`, `consumer/`, `api/` y `tools/verifier/` para confirmar que no contienen extracción USGS, persistencia de terremotos, endpoints sísmicos, Angular ni replay.
- [X] T037 Ejecutar la validación final de `quickstart.md`, actualizar `evidence/001-minimal-kafka-flow/README.md` con resultados observados y registrar explícitamente cualquier comprobación no realizada; no declarar funcionamiento solo por haber escrito código.

## Dependencias y orden de ejecución

### Dependencias de fases

- Setup (T001-T005): tareas iniciales; T002-T005 pueden ejecutarse en paralelo
  tras crear la estructura.
- Foundational (T006-T015): depende de Setup y bloquea las historias.
- US1 (T016-T027): depende de toda la fase Foundational; T016-T017,
  T018-T022 y T023 pueden prepararse en paralelo cuando estén definidos los
  contratos, pero T024-T026 requieren la infraestructura integrada.
- US2 (T028-T034): depende de US1 para repetir el flujo ya verificable.
- Polish (T035-T037): depende de US1 y US2.

### Dependencias entre historias

- **US1 (P1)**: depende de T006-T015; es el MVP y no depende de US2.
- **US2 (P2)**: depende de US1 porque repite el flujo y sus evidencias.

## Oportunidades de paralelismo

Después de T001:

```text
T002  Dockerfile/requirements del productor
T003  Dockerfile/requirements del consumidor
T004  Dockerfile/requirements de la API
T005  .env.example
```

Dentro de US1, después de definir los contratos:

```text
T016-T017  Modelo y envoltorio del evento del productor
T018-T020  Proceso persistente y publicación del productor
T021-T022  Registro del consumidor
T026       Verificador, cuando existan los formatos de evidencia
```

Dentro de US2, la documentación y preparación de las tres pruebas pueden
revisarse en paralelo, pero las ejecuciones deben aislarse y restaurarse una a
una:

```text
T028-T029  Guía reproducible y aislamiento por run_id
T030       Fallo del productor detenido
T031       Fallo de Kafka detenido
T032       Fallo del consumidor detenido
```

## Estrategia de implementación

### MVP: User Story 1

1. Completar Setup y Foundational.
2. Verificar los cinco servicios con `docker compose up --build -d`.
3. Implementar el productor persistente, el consumidor y el evento sintético.
4. Activar con `docker compose exec -T producer python /app/src/main.py publish-test`.
5. Implementar el verificador y detenerse para comprobar US1 de forma
   independiente.

### Entrega incremental

1. Añadir US2 solo después de disponer de una evidencia correcta de US1.
2. Ejecutar las tres pruebas de fallo sin recuperación automática dentro del
   caso probado.
3. Repetir desde un entorno Windows preparado y conservar las evidencias.
4. Dejar para hitos posteriores USGS real, persistencia, API sísmica, Angular,
   Netlify, ngrok y replay.

## Phase 6: Convergence

- [X] T038 Hacer invariable la configuración del topic sintético para exigir exactamente una partición y una réplica, rechazando valores divergentes en Compose, el productor y sus comprobaciones, según las reglas del topic de prueba del plan (partial).

## Phase 7: Convergence

- [X] T039 Verificar la trazabilidad de las evidencias tras el traslado del verificador: conservar `services\verifier\verify_event.py` en los registros históricos realmente ejecutados, mantener `tools\verifier\verify_event.py` en README y quickstart para las instrucciones actuales, y documentar la diferencia según T027, T032, T037 y la estructura del plan (partial, resuelta).
