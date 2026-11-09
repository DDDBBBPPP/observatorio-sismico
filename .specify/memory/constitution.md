<!--
Sync Impact Report
- Version change: 1.0.0 → 1.0.0 (adopción inicial con aclaraciones editoriales)
- Modified principles: I. Contrato y rúbrica; II. Entrega incremental;
  III. Integridad del dato; IV. Integración y seguridad; V. Verificación y evidencias
- Added sections: separación explícita entre requisitos docentes y acuerdos de trabajo;
  publicación del frontend en Netlify mediante ngrok HTTPS; requisitos de tres
  conclusiones fundamentadas
- Removed sections: ningún principio ni sección de gobierno
- Follow-up TODOs: ninguno
-->

# Constitución del Observatorio Sísmico

## Principios fundamentales

### I. Contrato y rúbrica son la definición de terminado

El sistema DEBE cumplir `CONTRATO-API.md`, los requisitos obligatorios de
`ENUNCIADO.md` y los criterios de su rúbrica. La API DEBE devolver el formato
GeoJSON, filtros, metadatos, errores explícitos y semántica de versiones
establecidos en el contrato. Las estadísticas DEBEN utilizar filtros
equivalentes a los del mapa y NO DEBEN presentar una muestra truncada como un
resultado global. La implementación DEBE conservar y completar el frontend
Angular proporcionado, sin tratar el mapa de demostración como sustituto del
pipeline y del análisis.

Esta regla evita que una solución aparentemente funcional incumpla la interfaz
evaluada o los criterios de extracción, calidad, modelado, análisis y reflexión.

### II. Entrega incremental y vertical

El desarrollo DEBE avanzar en incrementos pequeños, ejecutables y verificables.
El primer hito DEBE demostrar el recorrido mínimo productor → Kafka → consumidor
con un mensaje controlado; los siguientes hitos pueden añadir PostgreSQL, API,
frontend, calidad, histórico, filtros, estadísticas y reproducción. Cada hito
DEBE dejar una comprobación repetible y documentada antes de ampliar el alcance.

Este orden reduce el riesgo de construir mucha infraestructura sin una evidencia
temprana de comunicación entre servicios y mantiene el trabajo revisable.

### III. Integridad, trazabilidad e idempotencia de datos

El productor DEBE conservar el original y sus metadatos de extracción, publicar
por Kafka las novedades y revisiones identificadas por `id` y `updated`, y
confirmar la publicación antes de avanzar su estado. El consumidor DEBE validar,
transformar, enriquecer y persistir de forma idempotente, confirmando el offset
después de la escritura. Las repeticiones NO DEBEN crear filas ni recuentos
adicionales; una versión antigua NO DEBE sustituir a una más reciente.

Los nulos, eventos marítimos, anomalías y rechazos DEBEN conservar su
significado. Los registros no tratables DEBEN quedar en cuarentena con su
original y motivo. Las fechas y coordenadas DEBEN mantener unidades y sistemas
documentados. Las revisiones DEBEN reflejarse en el estado actual y en las
agregaciones afectadas.

Así se preserva la procedencia y se evita confundir mensajes recibidos con
eventos actuales, especialmente cuando Kafka entrega al menos una vez.

### IV. Integración completa y protección de secretos

Productor Python, Kafka, consumidor Python, PostgreSQL y API FastAPI DEBEN
permanecer en este repositorio y ejecutarse como cinco servicios separados de
Docker Compose, con imágenes reproducibles, persistencia, comprobaciones de
salud y reintentos adecuados. El frontend Angular DEBE consultar la API propia,
NO DEBE consultar USGS directamente en la entrega y DEBE publicarse como SPA en
Netlify. La publicación DEBE utilizar la URL HTTPS pública de ngrok para
consultar la API local. La integración geográfica DEBE usar el catálogo
entregado y una operación espacial documentada, conservando «Sin país
asignado» cuando proceda.

La configuración DEBE usar variables de entorno y `.env.example` sin valores
reales. NO DEBEN incluirse credenciales, tokens, volúmenes binarios,
`node_modules` ni grandes descargas regenerables. Kafka, PostgreSQL y las rutas
de administración NO DEBEN exponerse mediante el túnel público. CORS, timeouts,
errores del frontend y el encabezado de ngrok DEBEN configurarse conforme al
contrato, sin tratar CORS como autenticación.

La separación de responsabilidades y la protección de secretos son requisitos
de ejecución y de entrega, no mejoras opcionales.

### V. Verificación, documentación y defensa

Toda afirmación de funcionamiento DEBE estar respaldada por una ejecución,
resultado observado y evidencia repetible. La memoria o notebook DEBE
documentar instalación en un PC Windows nuevo, ejecución, procedencia,
transformaciones, decisiones, calidad, modelo, análisis, complejidad,
mediciones, costes, limitaciones y pruebas de aceptación. Las mediciones de
rendimiento DEBEN usar al menos tres tamaños de entrada; los datos sintéticos
DEBEN identificarse y quedar fuera del análisis sísmico real.

La entrega DEBE incluir instrucciones reproducibles en `README.md` y evidencias
de duplicados, revisiones, nulos, coordenadas inválidas, reinicios, errores del
túnel y reproducción histórica aislada. El panel DEBE distinguir lectura,
generación y última ingesta, y DEBE comunicar los fallos sin presentar datos
antiguos como recién obtenidos.

El análisis DEBE incluir al menos tres conclusiones fundamentadas. Cada
conclusión DEBE interpretar un resultado con cifras, periodo, ámbito, filtros y
denominador identificables; tres gráficos sin interpretación NO constituyen tres
conclusiones. La comparación histórica DEBE utilizar periodos y filtros
equivalentes y NO DEBE presentarse como una predicción de terremotos.

El objetivo es que otra persona pueda ejecutar, revisar y repetir el trabajo, y
que David pueda explicar el flujo y una decisión técnica durante la defensa.

## Requisitos docentes y acuerdos de trabajo

Los siguientes requisitos proceden del enunciado, el contrato de la API, la
rúbrica y los documentos docentes:

- **Requisitos obligatorios:** arquitectura de cinco servicios Docker Compose,
  contrato de la API, frontend Angular entregado y publicado en Netlify,
  consulta de la API mediante ngrok HTTPS, integración con el catálogo,
  idempotencia y revisiones, cuarentena, documentación y pruebas exigidas por
  el enunciado y la rúbrica.
- **Recomendaciones docentes:** comenzar con un evento ficticio, avanzar por
  hitos visibles, calcular agregaciones desde el estado actual, mantener
  originales reutilizables, usar índices justificados y organizar evidencias
  enlazadas desde `README.md`.
- **Mejoras opcionales:** automatizar informes de calidad, añadir un panel de
  calidad, usar Spark/Flink/Kubernetes o mantener disponibilidad permanente.
  Estas mejoras no sustituyen requisitos ni añaden puntos por sí mismas.

Los siguientes son acuerdos de trabajo propios de David y guían la colaboración,
pero NO son exigencias adicionales de la rúbrica:

- Las respuestas DEBEN redactarse en español.
- Cada tarea DEBE limitarse al prompt actual; NO DEBE encadenarse por iniciativa
  propia otra fase de Spec Kit, otra funcionalidad, un commit o un push.
- Antes de concretar requisitos, DEBEN consultarse los documentos docentes y el
  código existente, distinguiendo obligaciones, recomendaciones y propuestas.
- Las decisiones abiertas DEBEN presentarse con opciones, recomendación y
  consecuencias; David DEBE elegir antes de fijarlas y la elección DEBE quedar
  documentada.
- Cada cierre DEBE indicar qué se hizo, rutas afectadas, comprobaciones y
  resultados, pendientes y siguiente paso. Si no se modificaron archivos, DEBE
  decirse expresamente.
- Al cerrar una sección sustancial, DEBE plantearse una o dos preguntas breves
  para comprobar que David puede explicarla en la defensa, sin convertir cada
  ajuste menor en un cuestionario.
- Si un dato es incierto o una comprobación no se realizó, DEBE indicarse; NO
  DEBE afirmarse que algo funciona solo porque se escribió el código.

Las fuentes consultadas son `ENUNCIADO.md`, `CONTRATO-API.md`, `README.md`,
`FAQ-ALUMNADO.md`, `FAQ-observatorio-sismico .md`,
`Guia-entregables-observatorio-sismico.md`, `VALIDACION.md` y
`FUENTES-Y-LICENCIAS.md`. No se ha identificado contradicción entre ellas:
`FAQ-ALUMNADO.md` declara que aclara el enunciado sin añadir requisitos y la
guía declara que lo complementa sin modificar la rúbrica.

## Límites de arquitectura y decisiones abiertas

La constitución fija restricciones y criterios, pero no selecciona decisiones
abiertas de arquitectura, Kafka, transformación de datos, comunicación con el
frontend ni análisis. Cuando una de estas decisiones sea necesaria, el trabajo
DEBE presentar opciones viables, una recomendación razonada y sus consecuencias.
David DEBE elegir; la opción elegida y su motivo DEBEN quedar documentados antes
de implementarla.

La elección concreta de topic y esquema para live/replay, modelo físico de
PostgreSQL, estrategia de carga histórica, biblioteca espacial, forma de
agregación y diseño de filtros queda deliberadamente pendiente. NO DEBE
inventarse una decisión para cerrar una tarea. Estas alternativas se mantienen
abiertas porque el enunciado permite elegirlas, siempre que se justifiquen y
cumplan el contrato y la rúbrica.

## Flujo de trabajo y calidad

Antes de concretar requisitos o editar, se DEBE consultar la documentación
docente pertinente, el contrato y el código existente. Cada cambio DEBE estar
acotado a la tarea actual, reutilizar patrones existentes y evitar cambios no
relacionados.

Las pruebas DEBEN distinguir entre programado y ejecutado. Si una comprobación
no se realiza, se DEBE indicar la incertidumbre, la causa, el alcance y el
siguiente paso. Los errores DEBEN ser explícitos; NO se permiten ceros,
respuestas exitosas o estados de salud ficticios para ocultar fallos.

## Gobernanza

Esta constitución define las reglas de gobierno del repositorio y prevalece
sobre recomendaciones de implementación cuando exista conflicto. Una enmienda
DEBE describir su impacto, actualizar la versión y fecha, conservar la
trazabilidad con el contrato y la rúbrica, y revisar las instrucciones o
documentos afectados. Los cambios de código derivados de una enmienda se
realizarán en una tarea posterior, no implícitamente durante la edición de la
constitución.

La versión usa SemVer:

- **MAJOR:** eliminar o redefinir de forma incompatible un principio o una
  obligación.
- **MINOR:** añadir un principio, sección u obligación materialmente nueva.
- **PATCH:** aclarar redacción sin cambiar el gobierno ni el comportamiento
  exigido.

Cada revisión DEBE comprobar que no quedan placeholders inexplicados, que las
fechas usan `YYYY-MM-DD`, que los principios son declarativos y comprobables, y
que las evidencias siguen siendo repetibles. La revisión de cumplimiento se
realizará al planificar, implementar y cerrar cada incremento sustancial.

**Versión**: 1.0.0 | **Ratificada**: 2026-11-09 | **Última enmienda**: 2026-11-09
