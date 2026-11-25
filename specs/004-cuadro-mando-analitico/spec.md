# Especificación: Cuadro de mando analítico

## Objetivo y alcance

Añadir a la web Angular publicada en Netlify una sección «Cuadro de mando», sin
mapa, que consulte datos analíticos alojados en Supabase. El flujo existente
USGS → productor → Kafka → consumidor → PostgreSQL → API y la exploración actual
de Angular se conservan. Supabase recibe una copia de lectura analítica desde
PostgreSQL local cuando el equipo está encendido; no sustituye la base local ni
la API existente.

Esta especificación fija comportamiento y límites. **En esta entrega solo se
redacta documentación**: no se crea un proyecto Supabase, no se descargan ni
cargan datos y no se cambia la aplicación.

## Escenarios y requisitos

### Consulta con el equipo encendido

- **CM-01** La sección consulta exclusivamente el conjunto analítico de
  Supabase mediante una superficie de lectura limitada. No depende de que la
  API local o el túnel estén disponibles para mostrar los datos sincronizados.
- **CM-02** La sincronización local copia solo terremotos reales de USGS que
  sean la versión vigente. Una repetición no crea duplicados y una versión
  antigua no reemplaza otra más reciente.
- **CM-03** La sincronización conserva un progreso recuperable. Tras un corte o
  reinicio reintenta lo no confirmado y reconcilia posibles huecos antes de
  declarar la copia al día. Una carga inicial y los incrementos posteriores
  usan la misma regla de identidad y revisión.

### Consulta con el equipo apagado

- **CM-04** Netlify sigue sirviendo Angular y el cuadro muestra los datos ya
  sincronizados en Supabase, junto con la **fecha y hora de última
  sincronización correcta**. La etiqueta explica que es una copia y no afirma
  que sea actividad en tiempo real. Se distingue esa fecha de la del terremoto
  más reciente y de la hora en que el navegador hizo la consulta.
- **CM-05** Un fallo de lectura muestra un estado de error o de datos no
  disponibles; nunca convierte el fallo en cero terremotos ni cambia la fecha
  de sincronización. Un conjunto vacío válido se identifica por separado.

### Periodos y coherencia

- **CM-06** Se prevén filtros sencillos por **año**, **últimos 12 meses** y
  **última semana**. Cada respuesta identifica el intervalo efectivo y su zona
  temporal, la cobertura disponible y la fecha de la copia. Título, etiqueta
  del periodo y todas las cifras/gráficos visibles corresponden al mismo filtro
  aplicado y a la misma instantánea; mientras se carga otra consulta no se
  mezclan resultados.
- **CM-07** Se planifica ampliar el histórico a varios años. La selección de
  años y cualquier nueva descarga o carga quedan pendientes; los periodos sin
  cobertura no se muestran como ceros ni como años completos.

### Separación de datos y seguridad

- **CM-08** Replay, pruebas sintéticas y eventos `controlled-*` quedan fuera de
  las cifras reales, tanto en la carga inicial como en cada sincronización y
  consulta. La procedencia y el alcance de la cobertura deben poder auditarse.
- **CM-09** El navegador no contiene credenciales de escritura ni conexión a
  PostgreSQL. La lectura pública solo expone columnas y operaciones necesarias
  para el cuadro; no da acceso a originales, procedencia interna, tablas de
  control ni funciones de escritura. Se prueban permisos y aislamiento con el
  rol público antes de publicar.

## Criterios de aceptación para las entregas futuras

1. Una misma identidad de USGS aparece una sola vez; reejecutar la carga o el
   sincronizador deja idénticos recuentos. Una revisión nueva actualiza la
   copia y una antigua no la revierte.
2. Cortar el proceso a mitad de lote y reiniciarlo completa la copia sin
   pérdidas ni duplicados. Los controles de integridad comparan el origen real
   elegible con Supabase en periodos cubiertos.
3. Replay y sintéticos no figuran en la copia pública ni en los agregados. El
   rol público no puede leer tablas privadas ni escribir, incluso mediante
   llamadas directas a la API de Supabase.
4. Con el PC, Docker y el túnel apagados, la sección sigue consultando la copia
   desde la web publicada y muestra la última sincronización correcta. No
   muestra una señal de «en directo».
5. Cambiar de periodo actualiza conjuntamente título, rango efectivo y todas
   las cifras. Un año sin cobertura y un error de red se distinguen de un cero
   real; una respuesta lenta anterior no sobrescribe el filtro nuevo.

## Decisiones pendientes de ejemplos y capturas

- Años concretos que se incorporarán y cuál se ofrecerá por defecto.
- KPI y definiciones exactas, incluidos denominadores y tratamiento de nulos.
- Tipos, cantidad y contenido de gráficos.
- Distribución visual, jerarquía y detalles de presentación del cuadro.

No se da por elegido ningún valor de esos puntos por el hecho de que la vista
actual ya tenga indicadores o gráficos.
