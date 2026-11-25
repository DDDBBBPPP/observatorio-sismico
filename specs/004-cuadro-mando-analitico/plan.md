# Plan de implementación: Cuadro de mando analítico

## Base comprobada en el repositorio

- `compose.yaml` mantiene cinco servicios: Kafka, PostgreSQL, productor,
  consumidor y API. `README.md` explica que Angular está en Netlify y que hoy
  la API local requiere PC y túnel activos. El nuevo cuadro leerá Supabase sin
  alterar ese recorrido.
- `consumer/src/migrations/001_ingestion_schema.sql` define `event_version`
  con unicidad `(event_id, updated)`, `event_current` con una fila por `event_id`
  y `current_updated`, marcas `source`, `load_type`, `is_synthetic`, tablas de
  replay separadas y `historical_interval_checkpoint`.
- `consumer/src/persistence.py` inserta versiones sin duplicarlas y solo cambia
  `event_current` si `current_updated` aumenta. `api/src/main.py` consulta
  `event_current` para live, usa `replay_event_current` aparte y filtra
  `is_synthetic = FALSE` en los datos reales.
- `producer/src/historical_loader.py` permite indicar año, parte de 2025 y
  descarga USGS por meses con `minmagnitude=4` y `eventtype=earthquake`;
  divide intervalos si alcanzan el límite. `consumer/src/batch_manifest.py`
  valida cobertura, filtros y originales. `consumer/src/batch.py` carga con
  checkpoints por intervalo y etiqueta `historical_initial`; su bloqueo
  consultivo usa actualmente la clave fija `historical-2025`. Antes de cargar
  otros años habrá que revisar esa clave, la política de corridas y la
  capacidad/tiempo de carga. `docs/GUIA-INSTALACION.md` documenta la operación
  separada de descarga y carga de 2025. **Aquí no se ejecuta.**
- `frontend/src/app/app.component.ts` y `.html` contienen la vista actual con
  mapa Leaflet, gráficos y tabla; `frontend/src/app/filter-query.ts` construye
  el periodo UTC compartido por `/api/eventos` y `/api/estadisticas`.
  `frontend/public/config.json` configura la URL de esa API y
  `frontend/netlify.toml` el build de Netlify. La nueva sección convivirá con
  la vista actual y tendrá estado de lectura y filtros propios, sin mapa.

## Secuencia técnica prevista

1. **Modelo y seguridad.** Diseñar en Supabase una proyección mínima de eventos
   reales vigentes, identificada por `event_id`, con `updated` de USGS,
   `event_time`, atributos analíticos necesarios y alcance de cobertura. Separar
   tablas de control y metadatos de sincronización de la superficie pública.
   Publicar solo una vista, función de lectura o API que aplique las restricciones
   acordadas; limitar columnas, parámetros, rangos y volumen. Configurar y
   verificar privilegios/RLS según el mecanismo elegido. No exponer claves de
   servicio, de escritura ni secretos en Angular, `config.json` o Netlify.
2. **Carga inicial.** Tomar una instantánea consistente de PostgreSQL local
   sobre `event_current` elegible (`source='usgs'`, `is_synthetic=FALSE`,
   versión vigente y fuera de replay). Registrar cobertura efectiva y conciliar
   identidad, revisiones y recuentos por periodo; no inferir cobertura de un
   año solo por tener eventos. Los años adicionales se elegirán antes de
   programar descargas, volúmenes y orden de cargas.
3. **Incrementos recuperables.** Ejecutar un sincronizador local cuando el PC
   esté activo. Persistir un punto de avance solo tras confirmar la escritura
   remota; reintentar lotes de manera idempotente. En Supabase aplicar una
   escritura condicional: mismo `event_id` y mismo `updated` no cambian la fila;
   solo un `updated` mayor la reemplaza. Evitar perder commits concurrentes
   mediante un registro duradero de cambios o una exploración solapada con
   reconciliación periódica del estado actual. Comprobar explícitamente ese
   caso antes de elegir el cursor definitivo. Actualizar el instante de última
   sincronización correcta únicamente tras confirmar el lote y la cobertura
   correspondiente; registrar fallos sin adelantarlo.
4. **Lectura analítica.** Elegir entre API de lectura propia o consultas seguras
   de Supabase según permisos y coste reales. Definir un contrato que devuelva
   datos de un único periodo e instantánea junto con `last_synced_at`, cobertura
   y errores distinguibles. Los límites `[inicio, fin)` se expresan en UTC;
   «últimos 12 meses» y «última semana» se calculan con un final de referencia
   explícito. Rechazar rangos/volúmenes abusivos. Las cifras concretas esperan
   la selección de KPI y gráficos.
5. **Interfaz.** Añadir navegación y sección «Cuadro de mando» dentro de
   Angular. Mantener aparte el mapa y los filtros/API actuales. Aplicar un
   único estado de consulta por filtro, cancelar o ignorar respuestas antiguas
   y actualizar juntos título, periodo y cifras. Mostrar siempre la fecha de
   última sincronización correcta y la condición de copia histórica, con
   estados de carga, falta de cobertura y error accesibles. La composición
   visual se diseñará al recibir ejemplos y capturas.
6. **Verificación y operación.** Probar idempotencia, revisión posterior y
   antigua, corte y reanudación, concurrencia, exclusiones, permisos públicos
   y lectura desde Netlify con el PC apagado. Documentar configuración local
   segura, arranque, seguimiento, recuperación y límites de cobertura.

## Límite de este primer paso

Solo se añaden `spec.md`, `plan.md` y `tasks.md` en este directorio. Ningún
esquema, servicio, dato, secreto o archivo de Angular se modifica ahora.
