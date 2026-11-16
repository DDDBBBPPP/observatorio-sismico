# Tareas de entrega completa

- [x] T001 Corregir y descargar el manifiesto histórico con los filtros
  mundiales de 2025, `minmagnitude=4` y `eventtype=earthquake`.
- [x] T002 Aplicar migración de procedencia y excluir sintéticos en consultas.
- [x] T003 Verificar los tres endpoints de la API con PostgreSQL real.
- [x] T004 Implementar y comprobar la ingesta periódica y el topic replay.
- [ ] T005 Compilar y comprobar el panel Angular conectado a la API. Build
  y prueba de estado del componente superados el 16-11-2026. David confirmó
  visualmente la versión nueva, los controles, replay USA=0/global=10 y,
  en incógnito sobre Netlify, mapa con círculos, indicador de 192 eventos,
  gráficos por país/hora y tabla con filas. Quedan por observar visualmente
  las distribuciones completas y el aviso durante caída/recuperación.
- [ ] T006 Ejecutar aceptación integrada y actualizar evidencias. API y cinco
  servicios superados; caída/recuperación HTTP y estado del componente probados.
  Sitio público HTTP 200, config publicado, CORS y capturas de David comprobados.
  Pendientes la prueba desde otro dispositivo y el aviso visual de caída y
  recuperación del túnel.
- [x] T007 Completar documentación de diccionario, modelo, calidad,
  conclusiones, complejidad, costes y despliegue.
- [x] T008 Verificar filtros `USA`, `ESP`, magnitud ≥4 y «Sin país asignado» en
  ambos endpoints, comparación histórica, botón/limpieza en estado del
  componente, replay aislado y versión antigua fuera de orden con rollback.
- [x] T009 Identificar el `ng serve` que entregaba código antiguo, reiniciarlo
  con `--poll 2000` y comprobar que `main.js` servido contiene los controles
  actuales y que una edición posterior se publica. Confirmar por HTTP replay
  enero global=10, enero+USA=0 y noviembre 2026=0, con estadísticas iguales.
- [x] T010 Registrar la comprobación visual comunicada por David sin
  atribuírsela al agente: versión nueva, «País», «Filtros aplicados», dos
  fechas y replay enero USA aplicado=0/global aplicado=10. Auditar los 55
  archivos candidatos a Git, exclusiones y ausencia de secretos detectables.
- [x] T011 Cierre local breve: build Angular, contrato de filtros, estado del
  componente, aceptación y `git diff --check` con exit 0; cinco servicios
  saludables. README Windows y preparación SPA/CORS revisados. Publicación y
  captura visual final permanecen en T005 y T006.
