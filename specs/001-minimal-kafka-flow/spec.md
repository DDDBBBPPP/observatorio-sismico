# Feature Specification: Flujo mínimo productor-Kafka-consumidor

**Feature Branch**: `001-flujo-kafka-minimo`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Primera funcionalidad del Observatorio Sísmico:
demostrar de forma reproducible el recorrido mínimo productor → Kafka →
consumidor con un evento ficticio y claramente identificado como prueba."

## Clarifications

### Session 2026-11-09

- Q: ¿Qué nivel de correspondencia debe exigir la prueba entre el evento
  enviado y la salida del consumidor? → A: Comparar el identificador y todos
  los campos del evento de prueba.
- Q: ¿Debe la evidencia identificar el componente que falla? → A: Identificar
  el componente fallido y el síntoma observable.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Demostrar el recorrido de un evento de prueba (Priority: P1)

Como David, quiero enviar un evento ficticio controlado y comprobar que el
consumidor recibe ese mismo evento, para demostrar el primer recorrido
funcional del Observatorio Sísmico sin depender todavía de datos reales.

**Why this priority**: Es el primer punto de control vertical y prueba la
comunicación básica entre productor, Kafka y consumidor antes de añadir
persistencia, API o frontend.

**Independent Test**: Con los componentes del hito en marcha, David envía un
evento de prueba con un identificador inequívoco y verifica que la salida del
consumidor contiene ese identificador y los datos esperados del mismo evento.

**Acceptance Scenarios**:

1. **Given** el recorrido mínimo está iniciado y listo para recibir mensajes,
   **When** David envía un evento ficticio identificado como prueba,
   **Then** el consumidor informa de la recepción del mismo evento y permite
   relacionar la salida con el mensaje enviado.
2. **Given** el evento enviado contiene todos sus datos de prueba,
   **When** el consumidor lo recibe,
   **Then** la evidencia muestra el identificador de prueba y los valores
   comprobables definidos para ese evento, sin atribuirlo a USGS ni a datos
   reales.
3. **Given** uno de los componentes no está disponible o el recorrido no puede
   completarse, **When** David realiza la demostración,
   **Then** la comprobación identifica el componente fallido, registra su
   síntoma observable y no presenta el hito como superado.

---

### User Story 2 - Repetir la comprobación de forma reproducible (Priority: P2)

Como David, quiero repetir el envío y la comprobación siguiendo instrucciones
claras, para poder demostrar el hito en otro momento y explicarlo en la defensa.

**Why this priority**: Una prueba que solo funciona una vez no proporciona
evidencia suficiente de un sistema verificable.

**Independent Test**: Una persona con un entorno Windows nuevo puede seguir las
instrucciones documentadas, enviar el evento de prueba y obtener una evidencia
equivalente de recepción o un error explícito.

**Acceptance Scenarios**:

1. **Given** las instrucciones y el evento de prueba están documentados,
   **When** otra persona repite los pasos en el entorno preparado,
   **Then** puede identificar el mensaje enviado, la recepción del consumidor y
   el resultado de la comprobación.
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
- Este hito no debe inferir que el mensaje se ha guardado en PostgreSQL, que la
  API lo sirve o que Angular lo representa.

## Alcance y exclusiones

Este hito cubre exclusivamente la comunicación mínima entre productor, Kafka y
consumidor con un evento ficticio controlado. Quedan fuera de este hito, pero
siguen siendo objetivos obligatorios del proyecto completo para hitos
posteriores:

- extracción real de USGS y publicación periódica;
- PostgreSQL, persistencia duradera, estado de versiones e idempotencia;
- API FastAPI, filtros, estadísticas y contrato de consulta;
- aplicación Angular, publicación en Netlify y consulta mediante ngrok HTTPS;
- carga histórica, integración geográfica, análisis de calidad y cuarentena;
- revisiones de eventos, reproducción histórica y aislamiento live/replay.

Esta lista delimita el hito y no convierte esas capacidades posteriores en
requisitos de aceptación del recorrido mínimo.

## Consideraciones para la planificación

La especificación no fija todavía la configuración de Kafka, el topic, las
particiones, la serialización, el formato del mensaje, los listeners ni la
estrategia de contenedores. Durante `/speckit-plan` se presentarán opciones,
una recomendación y sus consecuencias; David elegirá antes de cerrar el plan.
`/speckit-clarify` se utilizará para resolver ambigüedades de requisitos, no
para sustituir la decisión técnica del plan.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir preparar un evento ficticio controlado,
  claramente identificado como prueba y separado de los datos reales de USGS.
- **FR-002**: El sistema DEBE permitir enviar el evento controlado a través del
  recorrido productor → Kafka → consumidor.
- **FR-003**: El consumidor DEBE informar de forma observable la recepción del
  evento, incluyendo un identificador suficiente para relacionarla con el
  mensaje enviado.
- **FR-004**: La comprobación DEBE permitir verificar que los valores observados
  por el consumidor corresponden al evento controlado enviado, comparando su
  identificador y todos los campos definidos para el evento de prueba.
- **FR-005**: La demostración DEBE distinguir entre recepción confirmada,
  recepción no confirmada y fallo del recorrido.
- **FR-006**: Si el productor, Kafka o el consumidor falla, la comprobación DEBE
  identificar el componente fallido y su síntoma observable, y NO DEBE producir
  una confirmación exitosa sin evidencia de recepción.
- **FR-007**: El procedimiento DEBE poder repetirse siguiendo instrucciones
  documentadas, identificando el evento y la ejecución de prueba.
- **FR-008**: La evidencia DEBE conservar, como mínimo, el evento controlado
  enviado, su identificador de prueba, el resultado observable del consumidor,
  la fecha y hora de la ejecución y cualquier fallo relevante.

### Key Entities *(include if feature involves data)*

- **Evento ficticio de prueba**: mensaje controlado que representa un único
  evento para la demostración; incluye un identificador inequívoco y valores
  verificables, sin representar un terremoto real.
- **Ejecución de prueba**: intento reproducible de enviar el evento y verificar
  su recepción; se identifica por su fecha y hora y conserva su resultado.
- **Evidencia de recorrido**: conjunto de registros que relaciona el evento
  enviado con la salida del consumidor o con el fallo observado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En cada ejecución correcta de este hito, el único evento
  controlado enviado aparece identificado en la salida observable del
  consumidor con el mismo identificador y todos los campos definidos para esa
  ejecución.
- **SC-002**: Una persona que siga el procedimiento documentado puede completar
  una ejecución correcta y localizar la evidencia del envío y de la recepción
  en un máximo de 10 minutos, sin conocimiento previo del código.
- **SC-003**: En las tres pruebas deliberadas de fallo de este hito
  (productor no disponible, broker no disponible y consumidor no disponible),
  cada ejecución identifica el componente fallido, registra su síntoma
  observable y no muestra una recepción confirmada; este resultado valida esos
  casos concretos y no constituye una garantía universal de fiabilidad.
- **SC-004**: La evidencia de cada ejecución permite identificar de forma
  inequívoca el evento enviado, el resultado del consumidor, la fecha y hora y
  si la ejecución fue correcta o fallida.

## Assumptions

- El usuario de este hito es David, que necesita una prueba explicable y
  repetible para la defensa.
- El evento de prueba será sintético y estará etiquetado como prueba; no se
  usarán resultados ficticios para extraer conclusiones sobre sismicidad real.
- El entorno de ejecución y la forma de iniciar los componentes se concretarán
  en una fase posterior de planificación, respetando la constitución y el
  requisito global de servicios en Docker Compose.
- La salida observable del consumidor puede ser un registro de ejecución
  adecuado al diseño que David elija; esta especificación no fija su formato.
- La prueba de este hito verifica comunicación y correspondencia del mensaje,
  no persistencia duradera, orden global, idempotencia ni procesamiento de
  revisiones, que pertenecen a hitos posteriores.
