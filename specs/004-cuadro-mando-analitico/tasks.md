# Tareas: Cuadro de mando analítico

Cada tarea se cierra con evidencia y **un commit propio**. El diseño documental
de David está recogido en `spec.md`, `plan.md` y `guia-visualizacion.md`.
Los años 2023–2024 son objetivos de carga, no cobertura disponible.

- [x] **T001 — Modelo analítico y seguridad (local).** Definir esquema mínimo, identidad
  y regla de revisión; crear la superficie pública de lectura y los permisos
  de escritura solo para el proceso local. Comprobar con el rol público que no
  puede escribir ni leer tablas privadas/originales y que los parámetros de
  lectura están acotados. Entrega: migraciones/contrato de acceso y resultados
  de pruebas de seguridad, sin secretos versionados. Evidencia: dos migraciones
  versionadas, `contrato-lectura.md` y `python tests/run_analytics_t001.py`
  correcto en PostgreSQL 16 desechable. Aplicación y prueba en un proyecto
  Supabase real pendientes de que exista el proyecto; no se han cargado datos.
- [ ] **T002 — Carga inicial.** Cargar desde el PostgreSQL local los eventos
  vigentes reales ya disponibles, registrar cobertura real e instante de copia.
  Comprobar recuentos e identidades por periodo y reejecutar la carga sin
  duplicados. No ampliar aún el histórico hasta que se elijan años y se revise
  `producer/src/historical_loader.py`, `consumer/src/batch_manifest.py` y
  `consumer/src/batch.py`. Entrega: procedimiento repetible y conciliación.
- [ ] **T003 — Sincronización incremental.** Implementar ejecución local,
  progreso persistente, reintentos y reconciliación. Comprobar revisión nueva,
  revisión antigua, lote repetido, corte a mitad, reinicio y commits
  concurrentes. Entrega: sincronizador y registro de última sincronización
  correcta sin adelantos ficticios.
- [ ] **T004 — API de lectura o consultas seguras.** Elegir y documentar una
  de las dos vías tras verificar permisos, límites y contrato. Probar filtros
  de año, últimos 12 meses, última semana y magnitud mínima ≥4 en UTC, cobertura incompleta,
  respuesta vacía válida, errores y metadatos coherentes. Entrega: consultas
  públicas limitadas y pruebas de acceso directo con rol público.
- [ ] **T005 — Interfaz Angular.** Con ejemplos y capturas recibidos, añadir
  navegación y sección sin mapa, separada de live; conectar lectura, filtros,
  cabecera, 3 KPI y 4 gráficos según `guia-visualizacion.md`. Comprobar que
  título, periodo y todas las cifras cambian juntos,
  que una respuesta antigua no pisa otra nueva y que nunca se presenta la
  copia como tiempo real. Entrega: build y comprobación funcional/visual.
- [ ] **T006 — Pruebas con PC apagado.** Con una copia ya sincronizada, apagar
  PC/servicios/túnel y abrir la web de Netlify desde otro dispositivo. Comprobar
  acceso a Supabase, cifras conservadas y fecha de última sincronización;
  probar también la recuperación posterior. Entrega: evidencia fechada de la
  prueba y limitaciones observadas.
- [ ] **T007 — Documentación operativa.** Actualizar README y guía de
  instalación con configuración segura, carga, sincronización, recuperación,
  cobertura, costes/límites y significado de la fecha mostrada. Comprobar
  enlaces y que ningún secreto ni paso implícito quede en las instrucciones.
  Entrega: guía reproducible contrastada con el sistema implementado.
