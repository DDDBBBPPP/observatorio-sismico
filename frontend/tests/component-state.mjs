import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

// Exercise component state and request wiring without a browser or extra packages.
function loadTypeScript(path, requireMock) {
  const source = readFileSync(new URL(path, import.meta.url), 'utf8');
  const javascript = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
      experimentalDecorators: true }
  }).outputText;
  const module = { exports: {} };
  new Function('require', 'module', 'exports', javascript)(requireMock, module, module.exports);
  return module.exports;
}

function signal(initial) {
  let current = initial;
  const read = () => current;
  read.set = value => { current = value; };
  return read;
}
let markerCalls = 0;
let selectedPolygonCode = null;
const leaflet = {
  latLng: (lat, lon) => ({ lat, lon }),
  latLngBounds: () => ({ pad() { return this; } }),
  layerGroup: () => ({ addTo() { return this; }, clearLayers() {}, addLayer() {} }),
  tileLayer: () => ({ addTo() {} }),
  svg: () => ({}),
  geoJSON: () => ({ addTo() { return this; }, addData(feature) { if (feature?.properties?.ADM0_A3) selectedPolygonCode = feature.properties.ADM0_A3; }, clearLayers() { selectedPolygonCode = null; }, getBounds() { return { pad() { return this; } }; } }),
  circleMarker: () => { markerCalls++; return { bindPopup() { return this; }, addTo() {} }; },
  control: { layers: () => ({ addTo() {} }) }
};
const filters = loadTypeScript('../src/app/filter-query.ts', () => { throw Error('Unexpected import'); });
const { AppComponent } = loadTypeScript('../src/app/app.component.ts', name => {
  if (name === '@angular/common') return { CommonModule: class {} };
  if (name === '@angular/core') return { Component: () => target => target, signal, computed: fn => fn };
  if (name === '@bluehalo/ngx-leaflet') return { LeafletDirective: class {} };
  if (name === 'leaflet') return leaflet;
  if (name === './filter-query') return filters;
  throw Error(`Unexpected import: ${name}`);
});

globalThis.document = { createElement: () => ({ textContent: '' }) };
const catalog = { type: 'FeatureCollection', features: [
  { properties: { ADM0_A3: 'USA', NAME_ES: 'Estados Unidos' } },
  { properties: { ADM0_A3: 'ESP', NAME_ES: 'España' } },
  { properties: { ADM0_A3: 'CAN', NAME_ES: 'Canadá' } }
] };
const feature = (id, country_id, mag, replay_at = null, depth = 10) => ({
  type: 'Feature', id, geometry: { type: 'Point', coordinates: [-3, 40, depth] },
  properties: { place: id, time: 1794787200000, updated: 1794787200000,
    country_id, country_name: country_id === 'USA' ? 'Estados Unidos' : 'España', mag, replay_at,
    mode: replay_at ? 'replay' : 'live' }
});
const live = [feature('us-a', 'USA', 3), feature('es-a', 'ESP', 5, null, 100)];
const replay = [feature('replay-a', 'ESP', 4, '2026-11-16T10:00:00Z')];
const requests = [];
let apiUp = true;
globalThis.fetch = async url => {
  if (url === 'datos/paises.geojson') return { ok: true, json: async () => catalog };
  if (url === 'config.json') return { ok: true, json: async () => ({
    mode: 'api', apiUrl: 'http://127.0.0.1:8000', refreshMs: 60000, skipNgrokWarning: true
  }) };
  if (new URL(url).pathname.endsWith('/salud')) return { ok: true, json: async () => ({ trace: {
    last_new_event_persisted_at: '2026-11-18T00:00:00Z', last_persisted_at: '2026-11-18T00:01:00Z',
    revisions_stored: 3, duplicates_discarded: null, quarantined: 1, consumer_lag_messages: null
  } }) };
  if (!apiUp) throw new TypeError('Failed to fetch');
  const parsed = new URL(url);
  requests.push(parsed);
  const mode = parsed.searchParams.get('mode');
  const country = parsed.searchParams.get('country_id');
  const minMag = parsed.searchParams.get('min_mag');
  const minDepth = parsed.searchParams.get('min_depth_km');
  const maxDepth = parsed.searchParams.get('max_depth_km');
  const selected = (mode === 'replay' ? replay : live).filter(item =>
    (!country || item.properties.country_id === country) &&
    (!minMag || item.properties.mag >= Number(minMag)) &&
    (minDepth === null || item.geometry.coordinates[2] >= Number(minDepth)) &&
    (maxDepth === null || item.geometry.coordinates[2] <= Number(maxDepth)));
  const payload = parsed.pathname.endsWith('/eventos') ? {
    type: 'FeatureCollection', features: selected,
    metadata: { mode, total: selected.length, generated: Date.now(),
      last_source_fetch: Date.now() - 20 * 60 * 1000, filters: { country_id: country, min_mag: minMag ? Number(minMag) : null,
        min_depth_km: minDepth === null ? null : Number(minDepth), max_depth_km: maxDepth === null ? null : Number(maxDepth) } }
  } : {
    count: selected.length, period: { start: '2026-11-17T00:00:00+00:00', end: '2026-11-18T00:00:00+00:00' },
    filters: { country_id: country, min_mag: minMag ? Number(minMag) : null,
      min_depth_km: minDepth === null ? null : Number(minDepth), max_depth_km: maxDepth === null ? null : Number(maxDepth) },
    hourly_utc: [], countries: selected.map(item => ({ country_id: item.properties.country_id, country_name: item.properties.country_name, count: 1 })), distributions: {
      magnitude: { bins: [], null_count: 0 }, depth_km: { bins: [], null_count: 0 }
    }
  };
  return { ok: true, json: async () => payload };
};

const app = new AppComponent();
let recenterCount = 0;
const map = { attributionControl: { addAttribution() {} },
  setView() { recenterCount++; }, fitBounds() { recenterCount++; } };
async function settle() {
  for (let i = 0; i < 20; i++) {
    await new Promise(resolve => setTimeout(resolve, 0));
    if (!app.loading()) return;
  }
  throw Error('Component request did not settle');
}

try {
  await app.onMapReady(map);
  assert.equal(app.count(), 1, 'Initial view must use magnitude ≥4');
  assert.equal(app.trace().revisions_stored, 3);
  assert.equal(app.trace().duplicates_discarded, null);
  assert.equal(app.applied().minMag, '4');
  assert.equal(app.activeQuickView(), 'comparison');
  assert.equal(requests.at(-1).searchParams.get('min_mag'), '4');
  assert.equal(app.stats().count, 1);
  assert.equal(app.tableEvents()[0].properties.country_id, 'ESP');
  assert.equal(markerCalls, 1);
  assert.equal(app.countryDisplay('CAN', 'Canada'), 'Canadá (CAN)');
  assert.equal(app.formatDepth(1.12999999523163), '1,13');
  assert.equal(app.formatDepth(null), 'ND');
  assert.equal(app.date(1794787200000).endsWith(' UTC'), true);
  assert.equal(app.isRecentPeriod('2025-12-31T00:00:00Z'), false);
  assert.deepEqual(app.otherCountries([
    ...Array.from({ length: 7 }, (_, i) => ({ country_id: `X${i}`, country_name: `Country ${i}`, count: 8 - i })),
    { country_id: 'UNASSIGNED', country_name: 'Sin país asignado', count: 1 }
  ]).map(item => item.country_id), ['X6']);
  assert.match(app.appliedPeriod(), /2026-11-17 00:00/);
  assert.match(app.apiStale(), /consulta USGS correcta/);
  assert.equal(app.countryOptions().find(item => item.code === 'USA').name, 'Estados Unidos');
  app.selectQuickView('all');
  await settle();
  assert.equal(app.count(), 2);
  assert.equal(markerCalls, 3);
  assert.equal(app.activeQuickView(), 'all');
  assert.equal(requests.at(-1).searchParams.has('min_mag'), false);
  assert.equal(app.countryChart(app.stats().countries)[0].label, 'Estados Unidos (USA)');
  assert.equal(app.percent(1, app.stats().count), 50);
  const initialRequests = requests.length;
  app.applyFilter('country', { target: { value: 'USA' } });
  assert.equal(app.pending(), true);
  assert.equal(app.count(), 2, 'Editing must not relabel old global results');
  assert.equal(requests.length, initialRequests, 'Editing alone must not request the API');
  app.applyFilters();
  assert.equal(app.loading(), true);
  await settle();
  assert.equal(app.count(), 1);
  assert.equal(markerCalls, 4, 'The map must redraw for the selected filter');
  assert.equal(app.tableEvents()[0].properties.country_id, 'USA');
  assert.equal(app.stats().count, 1);
  assert.equal(app.countryChart(app.stats().countries)[0].count, 1);
  assert.equal(app.pending(), false);
  assert.match(app.appliedLabel(), /Estados Unidos \(USA\)/);
  assert.ok(recenterCount > 0, 'Applying a country must frame its result');
  assert.equal(selectedPolygonCode, 'USA');
  assert.equal(requests.at(-2).search, requests.at(-1).search, 'Both endpoints must receive identical filters');
  app.applyFilter('minMag', { target: { value: '4' } });
  app.applyFilters();
  await settle();
  assert.equal(app.count(), 0, 'USA and magnitude ≥4 must update the map');
  assert.equal(app.stats().count, 0, 'The chart must use the same filter');
  assert.equal(app.tableEvents().length, 0, 'The table must use the same filter');
  assert.equal(selectedPolygonCode, 'USA', 'A zero-result country must retain its polygon');
  assert.equal(requests.at(-2).searchParams.get('min_mag'), '4');
  assert.equal(requests.at(-2).searchParams.get('country_id'), 'USA');
  app.clearFilters();
  await settle();
  assert.equal(app.count(), 2);
  assert.equal(app.minMag(), '', 'Reset must return to the chosen quick view');
  assert.equal(app.country(), '');

  app.applyFilter('minDepthKm', { target: { value: '0' } });
  app.applyFilter('maxDepthKm', { target: { value: '70' } });
  app.applyFilters(); await settle();
  assert.equal(app.count(), 1);
  assert.equal(app.tableEvents()[0].properties.country_id, 'USA');
  assert.equal(app.stats().count, 1);
  assert.match(app.appliedLabel(), /profundidad 0–70 km/);
  assert.equal(requests.at(-2).search, requests.at(-1).search);
  app.applyFilter('minDepthKm', { target: { value: '70' } });
  app.applyFilter('maxDepthKm', { target: { value: '300' } });
  app.applyFilters(); await settle();
  assert.equal(app.count(), 1);
  assert.equal(app.tableEvents()[0].properties.country_id, 'ESP');
  app.applyFilter('country', { target: { value: 'CAN' } });
  const beforeEmptyCountry = recenterCount;
  app.applyFilters(); await settle();
  assert.equal(app.count(), 0);
  assert.equal(selectedPolygonCode, 'CAN');
  assert.ok(recenterCount > beforeEmptyCountry, 'Empty country must frame its polygon');
  app.clearFilters(); await settle();
  app.applyFilter('country', { target: { value: 'UNASSIGNED' } });
  app.applyFilters(); await settle();
  assert.equal(selectedPolygonCode, null, 'Unassigned must not invent a polygon');
  app.clearFilters(); await settle();

  app.selectQuickView('comparison');
  await settle();
  assert.equal(app.count(), 1);
  assert.equal(app.activeQuickView(), 'comparison');
  app.selectQuickView('all');
  await settle();

  const beforeFailure = app.lastRead();
  apiUp = false;
  app.applyFilters();
  await settle();
  assert.match(app.status(), /No se pudo actualizar/);
  assert.equal(app.lastRead(), beforeFailure);
  assert.equal(app.tableEvents().length, 2);
  apiUp = true;
  app.applyFilters();
  await settle();
  assert.match(app.status(), /API accesible/);

  app.setViewMode({ target: { value: 'replay' } });
  await settle();
  assert.equal(app.applied().viewMode, 'replay');
  assert.equal(app.count(), 1);
  assert.equal(app.tableEvents()[0].properties.replay_at, '2026-11-16T10:00:00Z');
  assert.equal(app.apiStale(), '', 'A delayed live ingestion must not look like a replay failure');
  assert.equal(requests.at(-2).searchParams.get('mode'), 'replay');
  assert.equal(requests.at(-1).searchParams.get('mode'), 'replay');
  app.applyFilter('country', { target: { value: 'USA' } });
  assert.equal(app.count(), 1, 'Edited replay filter must not change the applied view');
  app.applyFilters();
  await settle();
  assert.equal(app.count(), 0);
  assert.equal(app.stats().count, 0);
  assert.equal(app.tableEvents().length, 0);
  assert.equal(app.applied().country, 'USA');
  assert.equal(requests.at(-2).searchParams.get('country_id'), 'USA');
  assert.equal(requests.at(-1).searchParams.get('country_id'), 'USA');
  console.log('component state: passed (apply, clear, outage, recovery, replay)');
} finally {
  app.ngOnDestroy();
}
