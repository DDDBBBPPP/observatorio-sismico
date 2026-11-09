# Feature Specification: Infraestructura mínima de cinco servicios

**Feature Branch**: `001-flujo-kafka-minimo`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Preparar una infraestructura mínima de los cinco
servicios obligatorios en Docker Compose y demostrar con un evento ficticio el
recorrido productor → Kafka → consumidor."

## Clarifications

### Session 2026-11-09

- Q: ¿Qué nivel de correspondencia debe exigir la prueba entre el evento
  enviado y la salida del consumidor? → A: Comparar el identificador y todos
  los campos del evento de prueba.
- Q: ¿Debe la evidencia identificar el componente que falla? → A: Identificar
  el componente fallido y el síntoma observable.

### Decisiones de planificación registradas

- David ha elegido un único nodo Kafka en modo KRaft, con broker y controlador
  en el mismo contenedor. La limitación de no disponer de alta disponibilidad
  queda aceptada para este entorno local y deberá documentarse en la
  planificación y en la reflexión posterior.
- David ha elegido un mensaje JSON con envoltorio para separar los metadatos de
  prueba del evento.
- David ha elegido un topic de prueba separado.
- David ha elegido imágenes Python independientes para productor y consumidor.
- David ha elegido una partición para el topic de prueba de este hito. Esta
  decisión no fija todavía la topología ni las particiones futuras de
  live/replay.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Demostrar el recorrido de un evento de prueba (Priority: P1)

Como David, quiero levantar los cinco servicios obligatorios y enviar un evento
ficticio controlado para comprobar que el consumidor recibe ese mismo evento,
demostrando el primer recorrido funcional sin depender todavía de datos reales.

**Why this priority**: Es el primer punto de control vertical y prueba el
arranque coordinado de la infraestructura obligatoria y la comunicación básica
antes de añadir persistencia de eventos, API de consulta o frontend.

**Independent Test**: David ejecuta `docker compose up --build -d`, comprueba
que productor, Kafka, consumidor, PostgreSQL y API FastAPI tienen un estado
observable y honesto, y envía un evento de prueba con un identificador
inequívoco para verificar que la salida del consumidor contiene todos sus
campos.

**Acceptance Scenarios**:

1. **Given** los cinco servicios se han iniciado con `docker compose up --build
   -d`, **When** David comprueba sus estados, **Then** cada servicio informa de
   forma observable si está listo, en proceso o fallido, sin declarar éxito
   cuando no puede cumplir su función de arranque.
2. **Given** los cinco servicios están en marcha y el recorrido está listo para
   recibir mensajes, **When** David envía un evento ficticio identificado como
   prueba, **Then** el consumidor informa de la recepción del mismo evento y
   permite relacionar la salida con el mensaje enviado.
3. **Given** el evento enviado contiene todos sus datos de prueba,
   **When** el consumidor lo recibe,
   **Then** la evidencia muestra el identificador de prueba y los valores
   comprobables definidos para ese evento, sin atribuirlo a USGS ni a datos
   reales.
4. **Given** uno de los cinco servicios no está disponible o el recorrido no puede
   completarse, **When** David realiza la demostración,
   **Then** la comprobación identifica el componente fallido, registra su
   síntoma observable y no presenta el hito como superado.

---

### User Story 2 - Repetir la comprobación de forma reproducible (Priority: P2)

Como David, quiero repetir el envío y la comprobación siguiendo instrucciones
claras, para poder demostrar el hito en otro momento y explicarlo en la defensa.

**Why this priority**: Una prueba que solo funciona una vez no proporciona
evidencia suficiente de un sistema verificable.

**Independent Test**: Una persona con un PC Windows nuevo que cumpla los
prerrequisitos puede seguir las instrucciones documentadas, ejecutar el
arranque de Compose, comprobar los estados, enviar el evento de prueba y
obtener una evidencia equivalente de recepción o un error explícito.

**Acceptance Scenarios**:

1. **Given** las instrucciones, el evento de prueba y el arranque de los cinco
   servicios están documentados, **When** otra persona repite los pasos en el
   entorno preparado, **Then** puede identificar los cinco estados, el mensaje
   enviado, la recepción del consumidor y el resultado de la comprobación.
2. **Given** la prueba no puede ejecutarse por un requisito ausente o un servicio
   detenido, **When** se sigue el procedimiento,
   **Then** el procedimiento identifica el punto de fallo y no registra una
   recepción inexistente.

### Edge Cases

- El identificador del evento de prueba debe distinguirse de cualquier evento
  real y de ejecuciones anteriores.
- Un productor que no logra entregar el mensaje no debe generar una evidencia
  de recepción.
- Un consumidor detenido, desconectado o sin acceso al recorrido debe producir
  un fallo observable, no una confirmación ficticia.
- Un mensaje alterado o distinto del enviado debe considerarse una
  comprobación fallida.
- Reiniciar o repetir la demostración debe permitir distinguir cada ejecución
  sin confundir sus evidencias.
- PostgreSQL y la API pueden estar arrancados sin que ello demuestre que el
  mensaje se ha persistido o que la API sirve terremotos.
- Una señal de estado de servicio que no pueda verificarse debe registrarse como
  estado desconocido o fallo, nunca como listo.

## Alcance y exclusiones

Este hito cubre la preparación mínima de los cinco servicios obligatorios en
Docker Compose y la comunicación entre productor, Kafka y consumidor con un
evento ficticio controlado. PostgreSQL y la API FastAPI DEBEN poder arrancar,
pero su arranque no demuestra todavía persistencia ni consulta de terremotos.
Quedan fuera de este hito, pero siguen siendo objetivos obligatorios del
proyecto completo para hitos posteriores:

- extracción real de USGS y publicación periódica;
- persistencia de eventos en PostgreSQL, estado de versiones e idempotencia;
- endpoints de consulta de la API FastAPI, filtros, estadísticas y contrato de
  consulta;
- aplicación Angular, publicación en Netlify y consulta mediante ngrok HTTPS;
- transformaciones sísmicas, carga histórica, integración geográfica, análisis
  de calidad y cuarentena;
- revisiones de eventos, reproducción histórica y aislamiento live/replay.

Esta lista delimita el hito y no convierte esas capacidades posteriores en
requisitos de aceptación del recorrido mínimo.

## Consideraciones para la planificación

Las decisiones ya registradas son un único nodo Kafka KRaft, JSON con
envoltorio, topic de prueba separado con una partición e imágenes Python
independientes para productor y consumidor. Esta partición pertenece a este
hito y no fija la topología futura de live/replay. Cualquier otra decisión
técnica que afecte a la arquitectura o a la reutilización DEBE
presentarse durante `/speckit-plan` con opciones, recomendación y consecuencias;
David elegirá antes de cerrar el plan. `/speckit-clarify` se utilizará para
ambigüedades de requisitos, no para sustituir la decisión técnica del plan.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir preparar un evento ficticio controlado,
  claramente identificado como prueba y separado de los datos reales de USGS.
- **FR-002**: La entrega DEBE definir cinco servicios separados de Docker
  Compose: productor, Kafka, consumidor, PostgreSQL y API FastAPI.
- **FR-003**: El comando `docker compose up --build -d` DEBE iniciar los cinco
  servicios o informar explícitamente del fallo del servicio que no arranque.
- **FR-004**: Cada servicio DEBE proporcionar un estado observable que distinga
  como mínimo entre listo, en proceso y fallido o no disponible; NO DEBE
  declararse listo sin una comprobación adecuada para su función de arranque.
- **FR-005**: El sistema DEBE permitir enviar el evento controlado a través del
  recorrido productor → Kafka → consumidor.
- **FR-006**: El consumidor DEBE informar de forma observable la recepción del
  evento, incluyendo un identificador suficiente para relacionarla con el
  mensaje enviado.
- **FR-007**: La comprobación DEBE permitir verificar que los valores observados
  por el consumidor corresponden al evento controlado enviado, comparando su
  identificador y todos los campos definidos para el evento de prueba.
- **FR-008**: La demostración DEBE distinguir entre recepción confirmada,
  recepción no confirmada y fallo del recorrido.
- **FR-009**: Si cualquiera de los cinco servicios falla, la comprobación DEBE
  identificar el componente fallido y su síntoma observable, y NO DEBE producir
  una confirmación exitosa sin evidencia de recepción.
- **FR-010**: El procedimiento DEBE poder repetirse siguiendo instrucciones
  documentadas, identificando el evento y la ejecución de prueba.
- **FR-011**: La evidencia DEBE conservar, como mínimo, el evento controlado
  enviado, su identificador de prueba, el resultado observable del consumidor,
  el estado observable de los cinco servicios, la fecha y hora de la ejecución
  y cualquier fallo relevante.

### Key Entities *(include if feature involves data)*

- **Evento ficticio de prueba**: mensaje controlado que representa un único
  evento para la demostración; incluye un identificador inequívoco y valores
  verificables, sin representar un terremoto real.
- **Ejecución de prueba**: intento reproducible de enviar el evento y verificar
  su recepción; se identifica por su fecha y hora y conserva su resultado.
- **Evidencia de recorrido**: conjunto de registros que relaciona el evento
  enviado con la salida del consumidor o con el fallo observado.
- **Estado de servicio**: resultado observable del arranque de productor, Kafka,
  consumidor, PostgreSQL y API FastAPI; no implica persistencia ni consulta de
  datos sísmicos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Tras ejecutar `docker compose up --build -d`, los cinco servicios
  requeridos tienen un estado observable y el procedimiento identifica
  explícitamente cualquier servicio que no haya arrancado correctamente.
- **SC-002**: En cada ejecución correcta de este hito, el único evento
  controlado enviado aparece identificado en la salida observable del
  consumidor con el mismo identificador y todos los campos definidos para esa
  ejecución.
- **SC-003**: Una persona que siga el procedimiento documentado puede completar
  el arranque de los cinco servicios y localizar la evidencia del envío y de la
  recepción en un máximo de 10 minutos, sin conocimiento previo del código.
- **SC-004**: En las tres pruebas deliberadas de fallo del recorrido de este
  hito (productor, broker y consumidor no disponibles), cada ejecución
  identifica el componente fallido, registra su síntoma observable y no muestra
  una recepción confirmada; este resultado valida esos casos concretos y no
  constituye una garantía universal de fiabilidad. Los fallos de arranque de
  PostgreSQL o API se registran como estados honestos conforme a SC-001, sin
  convertirlos en pruebas funcionales de persistencia o consulta.
- **SC-005**: La evidencia de cada ejecución permite identificar de forma
  inequívoca el evento enviado, el resultado del consumidor, la fecha y hora y
  el estado de los cinco servicios y si la ejecución fue correcta o fallida.
- **SC-006**: La demostración no afirma que PostgreSQL persista eventos, que la
  API sirva terremotos ni que existan extracción real de USGS, transformaciones
  sísmicas, endpoints de consulta, Angular o replay.

## Assumptions

- El usuario de este hito es David, que necesita una prueba explicable y
  repetible para la defensa.
- El evento de prueba será sintético y estará etiquetado como prueba; no se
  usarán resultados ficticios para extraer conclusiones sobre sismicidad real.
- El entorno de ejecución se iniciará mediante Docker Compose y respetará el
  requisito global de cinco servicios obligatorios.
- La salida observable del consumidor puede ser un registro de ejecución
  adecuado al diseño que David elija; esta especificación no fija su formato.
- La prueba de este hito verifica comunicación y correspondencia del mensaje,
  arranque y estados honestos, no persistencia duradera, endpoints de consulta,
  orden global, idempotencia ni procesamiento de revisiones, que pertenecen a
  hitos posteriores.
