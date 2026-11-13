# Investigación y decisiones: primer hito

## Decisión: Compose como coordinador de cinco servicios

**Decisión**: usar un único `compose.yaml` con productor, Kafka, consumidor,
PostgreSQL y API FastAPI como cinco servicios separados.

**Motivo**: `ENUNCIADO.md`, `README.md` y las FAQ exigen que esos cinco servicios
se ejecuten juntos con `docker compose up --build -d`. Compose coordina
contenedores; no se cuenta como una sexta imagen.

**Alternativas consideradas**:

- Ejecutar productor o consumidor en el host: rechazado porque contradice la
  obligación de que los cinco servicios estén en Docker.
- Añadir un contenedor separado para Compose: rechazado porque Compose no es un
  servicio de aplicación.

## Decisión: imágenes de infraestructura

**Decisión**: usar `apache/kafka:3.9.0` como imagen oficial de Apache Kafka
compatible con KRaft y `postgres:16-alpine` como imagen oficial de PostgreSQL.
Las etiquetas quedarán fijadas en `compose.yaml`.

**Motivo**: reduce mantenimiento de imágenes de infraestructura y sigue la
petición de usar imágenes oficiales si son adecuadas. PostgreSQL tendrá
volumen y `pg_isready`; Kafka tendrá una comprobación de disponibilidad.

**Alternativas consideradas**:

- Construir Kafka y PostgreSQL desde imágenes Python: rechazado por duplicar
  mantenimiento y alejarse de la práctica docente.
- Usar una distribución no oficial de Kafka: queda como alternativa solo si la
  imagen oficial seleccionada no ofrece una configuración KRaft reproducible.

La disponibilidad de la etiqueta y la configuración KRaft se comprobarán al
implementar; no se usará `latest` como decisión de reproducibilidad.

## Decisión: creación automática del topic

**Decisión**: el productor persistente creará y validará el topic de prueba al
arrancar, mediante el cliente administrativo de `aiokafka`, después de conectar
con Kafka y antes de declararse `ready`.

**Reglas**: el topic tendrá exactamente una partición y un factor de réplica
de uno. Una creación nueva será idempotente; si ya existe, el productor
comprobará exactamente esas propiedades. Una discrepancia será `failed` y no
se ocultará recreando el topic.

**Motivo**: elimina pasos manuales y hace que el arranque de los cinco
servicios sea reproducible sin añadir un sexto servicio Compose.

## Decisión: topología Kafka del hito

**Decisión**: un nodo Kafka en modo KRaft, con broker y controlador en el mismo
contenedor, y un topic de prueba dedicado con una partición.

**Motivo**: es la elección expresa de David para reducir recursos y complejidad
en un PC local. Una partición es suficiente para el único flujo secuencial de
este hito.

**Consecuencia**: no hay alta disponibilidad. La partición y el topic de este
hito no fijan todavía la topología de live/replay ni sus particiones.

**Alternativas consideradas**:

- Kafka con ZooKeeper: rechazado porque añade un servicio y complejidad no
  necesarios.
- Varios nodos y particiones: reservado para una decisión posterior de
  topología y disponibilidad.

## Decisión: evento JSON con envoltorio

**Decisión**: el productor de prueba envía un JSON con metadatos de ejecución y
un evento sintético anidado.

**Motivo**: permite distinguir una prueba de datos reales y comparar todos los
campos sin confundir confirmación de publicación con confirmación de consumo.

**Alternativas consideradas**:

- JSON plano: rechazado para este hito porque mezcla metadatos de prueba con el
  evento.
- Avro/Protobuf: reservado para una futura decisión; añade registro o esquema
  antes de que exista una necesidad en esta demostración.

## Decisión: productor persistente y activación dentro del contenedor

**Decisión**: el servicio `producer` permanecerá vivo y listo como componente
de Compose; la ejecución del evento sintético se activará dentro del contenedor
ya iniciado mediante `docker compose exec -T producer python /app/src/main.py publish-test`.

**Motivo**: el comando principal debe arrancar cinco servicios y no debe
interpretar un proceso que termina con código 0 como “listo”. Separar estado
persistente y resultado de ejecución hace explícito el ciclo de vida sin añadir
un sexto servicio ni crear un contenedor efímero. `exec` también permite que la
prueba deliberada con el productor detenido falle en la activación.

La activación concreta será
`docker compose exec -T producer python /app/src/main.py publish-test`; el
proceso persistente usará el comando separado
`python /app/src/main.py serve`.

## Decisión: evidencias compartidas

Productor y consumidor montarán
`./evidence/001-minimal-kafka-flow` en `/evidence`. Escribirán
`/evidence/<run_id>/producer.json` y `/evidence/<run_id>/consumer.json`.
El verificador se ejecutará desde Windows, no como servicio Compose, con
Python 3.12 disponible:

```powershell
python tools\verifier\verify_event.py --evidence-dir evidence\001-minimal-kafka-flow\<run_id> --run-id <run_id> --started-at <inicio-ejecucion>
```

**Alternativas consideradas**:

- Hacer que el productor de Compose termine tras publicar: rechazado porque
  dejaría el servicio detenido y haría ambiguo el criterio de cinco servicios.
- `docker compose run --rm producer test-once`: rechazado por decisión de David;
  crea una ejecución separada y no prueba la activación dentro del productor
  persistente.
- Mantener un proceso que publique automáticamente al arrancar: rechazado
  porque impediría controlar exactamente un evento por ejecución.

## Decisión: significado verificable de `ready` en el productor

**Decisión**: `ready` exige proceso persistente vivo, resolución del nombre de
Kafka, conexión TCP o equivalente al broker y una comprobación de cliente que
demuestre que puede comunicarse con Kafka sin publicar el evento de prueba.

**Motivo**: un `sleep`, un proceso ocioso o un contenedor en estado `running`
solo demuestran que existe un proceso, no que el productor pueda realizar su
responsabilidad.

**Consecuencia**: si el productor no puede resolver o conectar con Kafka queda
en `starting`, `failed` o `unavailable`, nunca en `ready`. La activación se
realiza solo después de observar `ready`.

## Decisión: estados y recepción

**Decisión**: distinguir `starting`, `ready`, `completed` y
`failed/unavailable`. El productor conserva el JSON enviado y el acuse de
Kafka; el consumidor conserva el JSON recibido. Un verificador de la prueba
selecciona ambos por `run_id` y compara todos los campos antes de producir
`receive_confirmed`.

**Motivo**: la rúbrica y la especificación exigen estados honestos y no
permiten presentar un envío confirmado como recepción confirmada.

**Alternativas consideradas**:

- Hacer que el consumidor compare con un original propio: rechazado, porque no
  garantiza que tenga acceso al JSON exacto enviado por el productor.
- Usar solo `docker compose ps`: insuficiente, porque muestra ciclo de vida del
  contenedor pero no la recepción del mensaje.

## Decisión: aislamiento de ejecuciones frente a logs antiguos

**Decisión**: cada ejecución genera un `run_id` único y registra su instante de
inicio. El consumidor registra los mensajes con su propio `run_id`; el verificador
externo filtra por ambos criterios. Un registro antiguo o de otro `run_id` no
puede confirmar la ejecución actual.

**Motivo**: conservar logs no debe convertir una recepción histórica en éxito
de una prueba nueva.

**Prueba de fallos**:

- Productor detenido: `docker compose stop producer` y después
  `docker compose exec -T producer python /app/src/main.py publish-test`; la activación falla por ausencia de un
  contenedor operativo y no se ejecuta ningún comando de arranque.
- Kafka detenido: `docker compose stop kafka` y después la activación sobre el
  productor; se conserva el fallo de conexión y no se ejecuta `up`, `start` ni
  recreación de Kafka.
- Consumidor detenido: `docker compose stop consumer`, activar el productor y
  comprobar que puede existir `send_confirmed`, pero no `receive_confirmed`;
  el resultado final es fallo por ausencia de recepción.

La política normal puede ser `restart: unless-stopped`, pero cada prueba
negativa debe verificar que `docker compose stop` mantiene detenido el
componente durante el caso y que ningún comando de prueba ejecuta `up`,
`start` o recrea servicios. La restauración se hace después y se registra
separadamente.

## Decisiones no fijadas por este plan

- La topología futura live/replay y sus particiones.
- La persistencia real de eventos, tablas y semántica de revisiones.
- Los endpoints de consulta y el contrato operativo completo de la API.
- La estrategia de extracción USGS, histórico, calidad, Angular, Netlify y
  ngrok.
