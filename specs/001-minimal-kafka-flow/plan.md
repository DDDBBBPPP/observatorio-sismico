# Plan de implementación: Infraestructura mínima de cinco servicios

**Branch**: `001-flujo-kafka-minimo` | **Date**: 2026-11-09 | **Spec**:
[spec.md](./spec.md)

**Input**: Especificación del primer hito: cinco servicios separados en
Docker Compose y un único evento sintético productor → Kafka → consumidor.

## Resumen

Se preparará una topología local de Docker Compose con cinco servicios:
productor Python, Kafka en un único nodo KRaft, consumidor Python, PostgreSQL
oficial y API FastAPI. El productor y el consumidor usarán imágenes Python
independientes. PostgreSQL y FastAPI solo demostrarán arranque y estado
observable en este hito; no se implementarán persistencia de eventos ni
endpoints de consulta.

La prueba funcional usará un topic separado con una partición y un mensaje JSON
con envoltorio. El productor persistente permanecerá “ready” solo tras probar
su comunicación con Kafka y la prueba se activará bajo demanda dentro de ese
contenedor mediante
`docker compose exec -T producer python /app/src/main.py publish-test`. La publicación solo
se considerará envío confirmado cuando Kafka confirme el registro. La
recepción solo se considerará confirmada cuando un verificador compare el JSON
conservado por el productor con el JSON registrado por el consumidor, usando el
`run_id` y todos los campos del envoltorio y del evento.

## Contexto técnico

**Lenguaje/versión**: Python 3.12 para productor, consumidor y API; versiones
fijadas en los manifiestos de cada imagen.

**Dependencias principales**: `aiokafka` para productor/consumidor, FastAPI y
Uvicorn para la API, cliente PostgreSQL únicamente para la comprobación de
disponibilidad futura; Docker Compose para coordinar los cinco servicios.

**Almacenamiento**: PostgreSQL 16 Alpine con volumen local. En este hito no se
crean ni se validan tablas de eventos.

**Pruebas**: comprobaciones de Compose y salud, prueba reproducible del evento
controlado, JSON y acuse conservados por el productor, JSON registrado por el
consumidor, comparación externa por `run_id` y todos los campos, y
comprobaciones de arranque de PostgreSQL y FastAPI. La automatización de
pruebas se concretará en `/speckit-tasks`.

**Plataforma objetivo**: Docker Desktop en Windows; red interna de Compose y
puertos host solo donde sean necesarios para la demostración.

**Tipo de proyecto**: repositorio monolítico con cinco servicios backend
contenedorizados y frontend Angular existente, que permanece fuera de este
hito funcional.

**Objetivos de rendimiento**: ninguno para este hito. Se mide una sola
ejecución controlada, no rendimiento ni disponibilidad.

**Restricciones**: el comando de entrada es `docker compose up --build -d`;
Kafka y PostgreSQL no se exponen mediante túnel; no se incluyen secretos; la
prueba no debe afirmar persistencia ni consultas sísmicas.

**Escala/alcance**: un nodo Kafka KRaft, un topic de prueba, una partición y un
evento sintético por ejecución. Esta partición pertenece a este hito y no fija
la topología futura de live/replay.

## Comprobación de la constitución

*Puerta: debe pasar antes de investigación y se revisa después del diseño.*

- **Principio I — contrato y rúbrica**: PASS. Se conserva la arquitectura de
  cinco servicios y se deja el contrato completo de API para un hito posterior;
  este hito solo prueba el arranque de FastAPI.
- **Principio II — entrega incremental**: PASS. Se prueba primero el recorrido
  mínimo y se excluyen USGS real, persistencia, consultas, Angular, histórico,
  calidad y replay.
- **Principio III — integridad y trazabilidad**: PASS parcial justificado. El
  mensaje de prueba conserva un envoltorio y se compara completo; la
  idempotencia, revisiones y persistencia pertenecen a hitos posteriores.
- **Principio IV — integración y secretos**: PASS. Los cinco servicios
  permanecen en el mismo repositorio, usan Compose y no requieren credenciales
  reales para este hito.
- **Principio V — verificación y defensa**: PASS. `quickstart.md`, contratos y
  evidencias de estados y logs permiten repetir la demostración en Windows.

No hay violaciones constitucionales que requieran complejidad adicional.

## Investigación y decisiones

Las decisiones y alternativas consideradas están en
[research.md](./research.md). Las decisiones de David conservadas son:

- Kafka de un nodo en modo KRaft, con broker y controlador juntos.
- JSON con envoltorio.
- Topic separado para la prueba.
- Una partición para ese topic de prueba.
- Imágenes Python independientes para productor y consumidor.

La topología futura de live/replay y sus particiones no queda decidida por este
hito.

## Estructura del proyecto

### Documentación de este hito

```text
specs/001-minimal-kafka-flow/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── event-envelope.md
    └── service-status.md
```

### Código previsto para la implementación posterior

```text
compose.yaml
.env.example
services/
├── producer/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       ├── main.py
│       ├── healthcheck.py
│       ├── event_model.py
│       └── status.py
├── consumer/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── src/
│       └── main.py
└── api/
    ├── Dockerfile
    ├── requirements.txt
    └── src/
        └── main.py
services/verifier/
├── README.md
└── verify_event.py
evidence/
└── 001-minimal-kafka-flow/
```

Los nombres son una propuesta de estructura para `/speckit-tasks`, no archivos
creados por esta fase. El frontend `frontend/` existente no se modifica.

**Decisión de estructura**: separar productor, consumidor y API en directorios
con imágenes Python propias, y coordinar Kafka y PostgreSQL mediante imágenes
oficiales desde `compose.yaml`. Docker Compose no es una sexta imagen.

## Diseño operativo del hito

### Arranque y estados

`docker compose up --build -d` debe crear e iniciar los cinco servicios.
Kafka se declara saludable solo tras aceptar su comprobación de disponibilidad;
PostgreSQL se declara saludable con `pg_isready`; la API se declara saludable
con `GET /api/salud` en `http://127.0.0.1:8000/api/salud` dentro de su
contenedor; productor y consumidor usan comprobaciones que distinguen
proceso vivo de dependencia lista.

El estado observable común se documentará como:

- `starting`: contenedor iniciado, dependencias aún no preparadas;
- `ready`: proceso persistente preparado para su responsabilidad;
- `completed`: ejecución controlada terminada correctamente; no equivale a
  `ready`;
- `failed` o `unavailable`: no puede cumplir su responsabilidad.

Un productor de una sola ejecución que publique y termine con código 0 queda en
`completed`, nunca en `ready`. Para que los cinco servicios sigan activos tras
el arranque, el servicio `producer` será persistente y aceptará una activación
controlada dentro del contenedor ya iniciado mediante
`docker compose exec -T producer python /app/src/main.py publish-test`. El
proceso persistente se inicia con un comando separado, por ejemplo
`python /app/src/main.py serve`; `publish-test` no se presupone por un
ENTRYPOINT. El estado `ready` del productor solo
será válido si su comprobación demuestra que el proceso persistente está vivo,
puede resolver y abrir conexión con Kafka y puede completar una operación de
verificación definida por el servicio; un proceso ocioso, un `sleep` o un
contenedor en ejecución sin conectividad no bastan. La prueba registrará por
separado el estado persistente y el resultado de la activación.

### Activación y comprobación del evento

1. Arrancar los cinco servicios con `docker compose up --build -d`.
2. Esperar las comprobaciones de salud y conservar el estado observado.
3. Generar un `run_id`/`event_id` único y activar exactamente una ejecución
   dentro del productor ya iniciado mediante:

   ```powershell
   docker compose exec -T producer python /app/src/main.py publish-test
   ```
4. Conservar desde el productor el JSON enviado y el acuse de Kafka. Registrar
   `send_confirmed` solo si Kafka devuelve confirmación; un código 0 no implica
   recepción.
5. Esperar el registro del consumidor en el topic de prueba y conservar el JSON
   que el consumidor declara recibido.
6. La comprobación externa, ejecutada desde Windows con Python 3.12 disponible,
   selecciona únicamente los registros de esta
   ejecución por su `run_id` y compara el JSON enviado por el productor con el
   JSON recibido por el consumidor, incluyendo todos los campos definidos.
   Solo entonces registrar `receive_confirmed`.
   El comando previsto es:

   ```powershell
   python services\verifier\verify_event.py --evidence-dir evidence\001-minimal-kafka-flow\<run_id> --run-id <run_id> --started-at <inicio-ejecucion>
   ```
7. Conservar estados, JSON, acuses, salida del consumidor, timestamps y
   resultado final. Los logs se consultarán con un límite temporal posterior al
   inicio de la ejecución y con el `run_id`; los logs antiguos no pueden
   confirmar una ejecución nueva.

Si el productor está detenido, la activación con `docker compose exec -T
producer python /app/src/main.py publish-test` debe fallar porque no existe un
contenedor productor operativo;
no se debe arrancar o recrear automáticamente. Si Kafka está detenido, la
prueba debe conservar el estado fallido del broker y la activación no debe
ejecutar `docker compose up`, `start` ni ninguna acción que lo vuelva a
arrancar inadvertidamente. Si el consumidor falla, no habrá `receive_confirmed`.
En todos los casos se identifica el componente y el síntoma. Si PostgreSQL o
API no arranca, la infraestructura no pasa el criterio de cinco servicios,
pero no se presenta ese fallo como prueba de persistencia o consulta.

### Evidencias compartidas y configuración de Compose

Productor y consumidor montarán el mismo directorio del repositorio:

```yaml
volumes:
  - ./evidence/001-minimal-kafka-flow:/evidence
```

Dentro de los contenedores escribirán respectivamente
`/evidence/<run_id>/producer.json` y `/evidence/<run_id>/consumer.json`.
El verificador no será un servicio Compose: se ejecutará desde Windows sobre
`evidence\001-minimal-kafka-flow\<run_id>`. Solo la API publicará
`127.0.0.1:8000:8000`; Kafka y PostgreSQL permanecerán accesibles por nombres
de servicio dentro de la red Compose y no se publicarán al host.

El productor creará el topic de prueba de forma automática e idempotente al
arrancar su proceso persistente, después de conectar con Kafka y antes de
declararse `ready`, usando el cliente administrativo de `aiokafka`. La
configuración exigida será una partición y un factor de réplica de uno. Si el
topic ya existe, el arranque comprobará que conserva exactamente una
partición y réplica uno; cualquier discrepancia producirá `failed` y no
`ready`. No habrá un paso manual ni otro servicio para crear el topic.

La política de recuperación será `restart: unless-stopped` para los servicios
que deban recuperarse durante el uso normal. Las pruebas negativas detendrán
explícitamente el componente con `docker compose stop` y verificarán que los
comandos de la prueba no ejecutan `up`, `start` ni una recreación automática;
la comprobación real de esta propiedad queda en las tareas de fallo.

## Complejidad

No se añade una tabla de complejidad porque no hay una violación constitucional.
