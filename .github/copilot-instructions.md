# Instrucciones permanentes del repositorio

## Comunicación y cierre de tareas

- Responde siempre en español.
- Al terminar cada tarea, aunque sea pequeña o falle, entrega una respuesta final con:
  - qué has hecho;
  - las rutas de los archivos creados o modificados;
  - qué has comprobado y con qué resultado;
  - qué queda pendiente;
  - cuál sería el siguiente paso.
- Si no has cambiado archivos, dilo expresamente.
- Al cerrar cada sección sustancial, plantea una o dos preguntas breves para comprobar que David podría explicarla en la defensa. No conviertas cada comando o ajuste menor en un cuestionario.
- Si un dato es incierto o una comprobación no se ha realizado, indícalo. No afirmes que algo funciona solo porque el código se haya escrito.
- Una vez informado el resultado, detente para que David pueda revisarlo.

## Alcance y toma de decisiones

- Completa únicamente la tarea solicitada en el prompt actual. No encadenes por iniciativa propia otra fase de Spec Kit, otra funcionalidad, un commit o un push.
- Antes de concretar requisitos, consulta los documentos docentes de la raíz del repositorio y el código existente.
- Distingue siempre entre:
  - requisitos obligatorios del enunciado, el contrato de la API y la rúbrica;
  - recomendaciones de las guías y FAQ;
  - propuestas propias.
- Si hay contradicciones, señala los documentos y pasajes afectados sin inventar una solución.
- Para decisiones abiertas de arquitectura, Kafka, transformación de datos, comunicación con el frontend o análisis:
  1. presenta las opciones viables;
  2. recomienda una opción razonada;
  3. explica las consecuencias y compromisos;
  4. pregunta a David cuando la decisión sea necesaria;
  5. documenta la opción que David elija y por qué.
- No fijes por tu cuenta decisiones pendientes que requieran una elección de David.

## Requisitos obligatorios del proyecto

- Respeta el contrato de la API en `CONTRATO-API.md` y la rúbrica del enunciado.
- Conserva y completa la aplicación Angular proporcionada; no la sustituyas por otra aplicación ni elimines su base cartográfica.
- Mantén en este mismo repositorio el productor Python, el consumidor Python, Kafka, PostgreSQL, la API FastAPI y el frontend.
- El backend debe poder ejecutarse mediante Docker Compose con los cinco servicios obligatorios separados: productor, Kafka, consumidor, PostgreSQL y API.
- La API debe conservar el contrato GeoJSON, sus filtros, sus metadatos, sus errores explícitos y la compatibilidad con el frontend.
- Respeta la separación entre datos de demostración y datos reales, y entre ingesta live y reproducción histórica.
- No añadas claves, tokens, contraseñas ni otras credenciales al repositorio. Usa variables de entorno, secretos locales y `.env.example` sin valores reales.

## Desarrollo incremental y verificable

- Trabaja de forma incremental, con cambios pequeños y verificables.
- Antes de editar, inspecciona el código, la configuración, los documentos docentes y los patrones existentes que afecten a la tarea.
- Reutiliza las estructuras y convenciones existentes; evita cambios no relacionados.
- Documenta durante el desarrollo:
  - la instalación en un PC Windows nuevo;
  - la ejecución de los servicios y del frontend;
  - las transformaciones y decisiones de datos;
  - las pruebas ejecutadas;
  - las evidencias necesarias para la entrega y la defensa.
- Explica de forma comprensible qué se ha construido y cómo repetir cada comprobación.
- No marques una prueba como superada porque el comportamiento esté programado: ejecútala y registra el resultado observado.
- Si una comprobación no puede ejecutarse, indica el motivo, el alcance de la limitación y el siguiente paso necesario.
- Conserva los rechazos y sus motivos cuando el consumidor descarte datos, y documenta las dimensiones de calidad, resultados, acciones y limitaciones.

## Referencias de trabajo

- Revisa `ENUNCIADO.md` para la arquitectura, pruebas de aceptación, entregables y evaluación.
- Revisa `CONTRATO-API.md` antes de cambiar endpoints, formatos, filtros, CORS o integración con el frontend.
- Revisa `FAQ-ALUMNADO.md` para aclaraciones y ejemplos de funcionamiento esperado.
- Revisa `Guia-entregables-observatorio-sismico.md` para la documentación, evidencias y defensa.
- Revisa `README.md`, `VALIDACION.md` y `FUENTES-Y-LICENCIAS.md` para la base Angular, comprobaciones ya realizadas, procedencia y licencias.
- Mantén la configuración de Angular y el catálogo cartográfico entregado salvo que la tarea solicite expresamente modificarla.
