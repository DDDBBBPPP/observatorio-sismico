# Feature Specification: Ingesta USGS y persistencia trazable

**Feature Branch**: `002-ingesta-usgs-persistencia`

**Created**: 2026-11-13

**Status**: Draft

**Input**: User description: "Datos reales USGS recientes e histórico anual,
publicación por Kafka, conservación de originales, validación y
transformaciones, integración con el catálogo geográfico y persistencia
idempotente en PostgreSQL con versiones y cuarentena. Mantener API sísmica,
integración Angular, Netlify/ngrok y replay como hitos posteriores."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingerir novedades reales de USGS (Priority: P1)

Como responsable del observatorio, quiero consultar el feed reciente de USGS y
publicar las novedades y revisiones identificadas para que el sistema conserve
datos reales sin confundirlos con el evento sintético del hito anterior.

**Why this priority**: Es el primer incremento que sustituye la demostración
controlada por una fuente real y alimenta el procesamiento posterior.

**Independent Test**: Con el entorno preparado, una ejecución del productor
consulta el feed reciente, conserva la respuesta y sus metadatos, y publica
solo eventos sísmicos nuevos o revisados. Una repetición de la misma respuesta
no produce publicaciones duplicadas.

**Acceptance Scenarios**:

1. **Given** una respuesta válida del feed reciente con eventos de tipo
   `earthquake`, **When** se procesa por primera vez, **Then** se conserva el
   original, se registra la consulta y se publica cada versión nueva con su
   identificador, fuente, momento de ingesta y modo `live`.
2. **Given** una respuesta que contiene un evento ya conocido con el mismo
   `id` y `updated`, **When** se procesa de nuevo, **Then** no se publica una
   segunda vez esa versión y queda registrada la decisión de omisión.
3. **Given** un evento conocido con un `updated` posterior, **When** llega la
   respuesta, **Then** se publica la revisión y se conservan la versión
   anterior y la nueva.
4. **Given** una respuesta HTTP con error, límite de uso, timeout o JSON
   inválido, **When** termina el intento, **Then** se registra el fallo con su
   síntoma, se conserva el estado válido anterior y no se presenta la consulta
   como correcta.

### User Story 2 - Cargar un histórico anual reproducible (Priority: P2)

Como responsable del análisis, quiero incorporar una instantánea anual de
eventos USGS con filtros documentados para comparar periodos equivalentes sin
descargarla repetidamente ni perderla al reiniciar el entorno.

**Why this priority**: El histórico permite validar el pipeline con volumen y
proporciona la base temporal para el análisis posterior, sin mezclarlo con el
feed vivo.

**Independent Test**: Una ejecución de carga obtiene el año 2025 con el alcance
documentado, conserva las respuestas y consultas por intervalo, deduplica
eventos compartidos entre intervalos y deja un resultado reproducible que
sobrevive a un reinicio.

**Acceptance Scenarios**:

1. **Given** el alcance anual y sus filtros documentados, **When** se ejecuta
   la carga, **Then** cada intervalo queda identificado con su consulta,
   fecha de extracción, respuesta original y número de registros.
2. **Given** un intervalo que supera el límite de resultados de la fuente,
   **When** se prepara la carga, **Then** se subdivide sin truncar
   silenciosamente la respuesta y se conserva la relación entre intervalos y
   registros.
3. **Given** eventos repetidos en los límites de dos intervalos, **When** se
   combina el histórico, **Then** cada versión se procesa una sola vez y se
   conserva su procedencia.
4. **Given** el sistema se reinicia después de la carga, **When** se consulta
   el estado de la ingesta, **Then** el histórico y su trazabilidad siguen
   disponibles para repetir o auditar el procesamiento.

### User Story 3 - Validar, enriquecer y persistir versiones (Priority: P1)

Como responsable de datos, quiero que cada mensaje sea validado, transformado,
enriquecido con el catálogo geográfico y persistido con control de versiones
para que los resultados actuales sean consultables y los rechazos no se
pierdan.

**Why this priority**: Sin persistencia idempotente y procedencia, la ingesta
no puede sostener el análisis ni demostrar que una revisión o un duplicado se
trató correctamente.

**Independent Test**: Se envían casos reales y casos sintéticos aislados con
duplicados, revisiones, nulos, coordenadas inválidas y eventos marítimos. Se
comprueba el estado actual, el historial, el país asignado o su ausencia, la
cuarentena y el comportamiento tras repetir o reiniciar el consumidor.

**Acceptance Scenarios**:

1. **Given** un evento válido con coordenadas compatibles con el catálogo,
   **When** se consume, **Then** se guarda su versión original y transformada,
   se asocia el país mediante una operación espacial y queda disponible como
   estado actual.
2. **Given** un evento marítimo o sin polígono coincidente, **When** se
   transforma, **Then** conserva el evento con país no asignado y una razón
   distinguible de un rechazo.
3. **Given** la misma versión llega varias veces, **When** se procesa,
   **Then** no aumenta el número de eventos actuales ni de versiones distintas.
4. **Given** una revisión posterior y después una versión antigua, **When** se
   procesan en ese orden, **Then** el estado actual conserva la revisión más
   reciente y el historial conserva ambas versiones.
5. **Given** un registro que no puede tratarse por datos obligatorios inválidos,
   **When** se procesa, **Then** se conserva el original, el motivo y el
   contexto en cuarentena, no aparece como evento válido y el consumidor puede
   continuar con los siguientes mensajes.
6. **Given** el consumidor guarda una transacción y se interrumpe antes de
   confirmar la posición del mensaje, **When** vuelve a recibirlo, **Then** la
   repetición no duplica los efectos persistidos y la confirmación solo ocurre
   después de una escritura válida.

### Edge Cases

- El feed reciente puede devolver una ventana móvil sin que la ausencia de un
  evento signifique que USGS lo eliminó.
- USGS puede devolver `mag` o profundidad nulas; deben conservarse como
  desconocidas y excluirse de cálculos que requieran un valor.
- Magnitudes negativas o profundidades inusuales no se rechazan sin una regla
  justificada.
- Coordenadas no numéricas, fuera de rango o no finitas deben quedar en
  cuarentena con el original y un motivo explícito.
- Los límites temporales de consultas históricas pueden repetir un evento.
- Un evento puede estar en el mar, sobre una frontera o en una zona sin
  cobertura del catálogo.
- Un evento cuyo tipo no sea `earthquake` debe quedar excluido del conjunto
  sísmico con el motivo de exclusión conservado.
- Una respuesta parcial o un fallo de red no debe borrar el último estado
  válido ni producir una confirmación de ingesta.
- Los casos artificialmente dañados deben identificarse como pruebas y quedar
  separados de los datos reales y del análisis.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE consultar el feed reciente de USGS con una
  frecuencia configurable y registrar URL, parámetros, fecha, duración,
  resultado y error cuando corresponda.
- **FR-002**: El sistema DEBE permitir una carga inicial de un año completo del
  catálogo USGS, por defecto 2025, descargado una vez por meses con ámbito y
  filtros documentados, reutilizable sin descargar de nuevo los originales.
  La carga DEBE conservar metadatos propios de la ejecución batch y no
  presentarse como una recepción reciente del feed.
- **FR-003**: El sistema DEBE conservar cada respuesta original de USGS y sus
  metadatos antes de aplicar transformaciones, con una política de retención
  documentada.
- **FR-004**: El sistema DEBE filtrar el conjunto sísmico a eventos de tipo
  `earthquake` y conservar el motivo de exclusión de otros tipos.
- **FR-005**: El sistema DEBE identificar una versión por `id` y `updated`,
  publicar novedades y revisiones, omitir versiones ya publicadas y usar
  únicamente `mode=live` para el feed reciente o `mode=replay` para una
  reproducción posterior. La carga histórica inicial DEBE distinguirse por
  metadatos de extracción y carga batch, no por un tercer valor de `mode`.
- **FR-006**: Cada mensaje Kafka publicado DEBE conservar el evento original e
  incluir como mínimo su fuente, el momento de ingesta, un `mode` limitado a
  `live` o `replay` y el identificador del evento. La carga histórica batch
  DEBE conservar además sus metadatos de consulta, intervalo y ejecución sin
  convertirlos en `mode=live`.
- **FR-007**: El productor DEBE confirmar la publicación antes de avanzar el
  estado de una versión y DEBE registrar timeouts, errores HTTP, límites de
  uso, errores de formato y reintentos sin ocultar fallos.
- **FR-008**: El consumidor DEBE validar tipos, fechas, unidades, coordenadas,
  campos obligatorios y valores nulos con reglas explícitas y conservar el
  original de cada registro rechazado.
- **FR-009**: El consumidor DEBE transformar timestamps a UTC sin perder su
  unidad ni el valor original, separar tiempo de ocurrencia, actualización,
  ingesta y procesamiento, y registrar cuántos registros afecta cada
  transformación.
- **FR-010**: El sistema DEBE integrar cada evento mediante una operación
  espacial con el catálogo geográfico entregado, conservar `country_id`,
  nombre y atributos definidos por el catálogo cuando exista coincidencia, y
  representar «Sin país asignado» cuando no exista.
- **FR-011**: El sistema DEBE persistir el estado actual, las versiones
  recibidas, la procedencia y las consultas de ingesta con claves que impidan
  duplicados de evento y de versión.
- **FR-012**: El sistema DEBE aplicar actualizaciones solo cuando `updated` sea
  posterior a la versión actual, conservar versiones antiguas y mantener
  idempotencia después de repeticiones o reinicios.
- **FR-013**: El sistema DEBE conservar una cuarentena durable con el original,
  motivo, etapa, fecha y referencia del mensaje para cada registro no tratable,
  sin bloquear indefinidamente el procesamiento posterior.
- **FR-014**: El sistema DEBE confirmar la posición del mensaje únicamente
  después de persistir correctamente el evento o su cuarentena.
- **FR-015**: El sistema DEBE distinguir datos reales, datos sintéticos de
  prueba y una eventual reproducción histórica mediante etiquetas y evidencias
  separadas. La carga histórica inicial DEBE identificarse como ejecución batch
  mediante sus metadatos, sin inventar `mode=historical`.
- **FR-016**: El sistema DEBE proporcionar evidencias de calidad con código o
  consultas, denominador y resultados antes/después para completitud,
  unicidad, validez, consistencia, actualidad y exactitud, incluyendo acciones
  y limitaciones.
- **FR-017**: El sistema DEBE permitir repetir la ingesta reciente y la carga
  histórica desde archivos y metadatos conservados, sin depender de datos
  descargables versionados en Git.
- **FR-018**: Este incremento NO DEBE implementar todavía endpoints de consulta
  sísmica, filtros de la API, estadísticas, integración del frontend,
  publicación en Netlify, túnel ngrok ni reproducción histórica de demostración;
  esos objetivos quedan para hitos posteriores.

### Decisiones de alcance registradas

- El modelo de PostgreSQL será híbrido: estado actual, versiones, ingestas y
  cuarentena tendrán claves y restricciones; los originales se conservarán en
  JSONB y los índices se justificarán según las consultas.
- La integración geográfica usará GeoPandas/Shapely sobre el catálogo entregado
  en WGS84, documentando fronteras, varias coincidencias y «Sin país
  asignado».
- El histórico completo de 2025 se descargará una vez por meses mediante un
  proceso batch que reutilice las reglas de validación y persistencia. El feed
  reciente usará un topic live separado del topic sintético.
- La topología de topics y aislamiento para replay queda abierta para
  `/speckit-plan`; no se fija en esta especificación.

### Key Entities

- **Respuesta USGS**: documento original devuelto por una consulta, con URL,
  parámetros, fecha, estado, contenido y metadatos de extracción.
- **Evento sísmico**: identidad estable de USGS con tiempo, actualización,
  magnitud, tipo, lugar y coordenadas originales.
- **Versión de evento**: observación de un evento identificada por `(id,
  updated)`, con su original, transformación y procedencia.
- **Evento actual**: representación más reciente aceptada de un evento,
  asociada opcionalmente a una entidad geográfica.
- **Entidad geográfica**: país o región del catálogo entregado, con sus
  atributos y geometría de referencia.
- **Registro de ingesta**: intento de consulta, carga, publicación o
  procesamiento con estado, tiempos, recuentos y error explícito.
- **Registro de cuarentena**: original no tratable, motivo, etapa y referencia
  a la ejecución o mensaje que lo produjo.
- **Evidencia de calidad**: comprobación reproducible con conjunto,
  denominador, resultado, acción y limitación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una ejecución correcta conserva el 100 % de las respuestas
  consultadas y sus metadatos de extracción, y permite identificar el número
  de registros obtenidos por intervalo.
- **SC-002**: Al procesar dos veces la misma respuesta, el número de eventos
  actuales y de versiones distintas permanece sin cambios adicionales, y la
  evidencia identifica las omisiones por duplicado.
- **SC-003**: Una secuencia con una versión inicial, una repetición, una
  revisión posterior y una versión antigua termina con un estado actual
  correspondiente a la revisión más reciente, conserva las dos versiones
  distintas y no crea eventos adicionales.
- **SC-004**: El histórico anual seleccionado puede reconstruirse tras reiniciar
  el entorno sin volver a descargar los originales conservados y sin perder
  sus consultas, recuentos o filtros.
- **SC-005**: El 100 % de los registros rechazados en los casos de prueba
  controlados conserva original, motivo, etapa, fecha y referencia; ninguno
  aparece como evento válido.
- **SC-006**: Cada evento válido de los casos geográficos de prueba queda con
  el identificador del catálogo correspondiente o con «Sin país asignado» y
  una razón observable; no se asigna un país usando el texto descriptivo del
  lugar.
- **SC-007**: Las evidencias de calidad cubren al menos cuatro dimensiones
  exigidas por la rúbrica y muestran conjunto, denominador, resultado,
  decisión, efecto antes/después y limitación para cada comprobación.
- **SC-008**: En los casos de fallo HTTP, timeout, límite de uso, JSON inválido
  y caída del consumidor, el sistema conserva el estado válido anterior,
  registra el síntoma y puede continuar o reanudar sin afirmar éxito inexistente.
- **SC-009**: Una persona con el entorno del hito 001 preparado puede ejecutar
  una ingesta de prueba documentada y localizar originales, mensajes,
  versiones, cuarentena y resultados de calidad en menos de 15 minutos, sin
  conocimiento previo del código.
- **SC-010**: Ninguna evidencia de este incremento afirma que la API sísmica,
  Angular, Netlify, ngrok o replay estén terminados.

## Assumptions

- El feed reciente de referencia es la ventana `all_day.geojson` de USGS y la
  carga anual inicial toma 2025 como periodo por defecto.
- El alcance geográfico y los filtros de la carga anual se documentarán antes
  de ejecutar la carga y serán iguales en las comparaciones posteriores.
- El catálogo geográfico entregado se considera la fuente de referencia para
  la asignación espacial y puede dejar eventos sin país.
- La ingesta se ejecuta dentro de los cinco servicios Compose del hito 001;
  no se añade un sexto servicio para este incremento.
- Los fallos de red y fuente se registran con errores explícitos y no sustituyen
  datos ausentes por ceros ni eliminan el último estado válido.
- El análisis de calidad se entrega en memoria o notebook; no se exige un
  generador automático ni un panel específico de calidad.
- El modelo híbrido de PostgreSQL, GeoPandas/Shapely en WGS84, la carga batch
  mensual de 2025 y el topic live separado del topic sintético quedan fijados
  por las decisiones de alcance registradas; la topología futura de replay
  sigue abierta para la planificación.
- La API sísmica, el frontend, la publicación, el túnel y la reproducción
  histórica de demostración consumirán los resultados de este hito en fases
  posteriores.
