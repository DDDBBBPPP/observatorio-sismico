import assert from 'node:assert/strict';
import { execFileSync, spawn } from 'node:child_process';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

// Real Chrome + real local API. Screenshots include a JSON manifest with the
// exact API query, UTC window, UI/API count, viewport and capture time.
const frontend = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(frontend, '..');
const output = path.join(root, 'evidence', '002-ingesta-usgs-persistencia', 'visual-depth-night-20261118');
const base = 'http://127.0.0.1:4200';
const api = 'http://127.0.0.1:8000';
const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const outage = process.argv.includes('--test-outage');
const server = spawn('python', ['-m', 'http.server', '4200', '--bind', '127.0.0.1', '--directory', path.join(frontend, 'dist', 'observatorio', 'browser')],
  { cwd: root, windowsHide: true, stdio: 'ignore' });
let browser;
let apiStopped = false;
const captures = [];

async function waitHttp(url, limitMs = 15000) {
  const until = Date.now() + limitMs;
  while (Date.now() < until) {
    try { if ((await fetch(url, { signal: AbortSignal.timeout(2000) })).ok) return; }
    catch { /* server/API still starting */ }
    await new Promise(resolve => setTimeout(resolve, 250));
  }
  throw new Error(`HTTP unavailable after ${limitMs} ms: ${url}`);
}

async function waitPanel(page, expected = 'consulta completada') {
  await page.waitForFunction(value => {
    const text = document.querySelector('.status-main')?.textContent || '';
    return text.includes(value) && !document.querySelector('.status-panel .loading');
  }, expected, { timeout: 30000 });
}

async function setFilters(page, { start = '', end = '', mag = '', depthMin = '', depthMax = '', country = '', mode = 'live' }) {
  await page.locator('.filter-grid select').first().selectOption(mode);
  await page.locator('input[type="datetime-local"]').nth(0).fill(start);
  await page.locator('input[type="datetime-local"]').nth(1).fill(end);
  await page.locator('input[type="number"]').nth(0).fill(mag);
  await page.locator('input[type="number"]').nth(1).fill(depthMin);
  await page.locator('input[type="number"]').nth(2).fill(depthMax);
  await page.locator('.filter-grid select').nth(1).selectOption(country);
  await page.getByRole('button', { name: 'Aplicar filtros' }).click();
  await waitPanel(page);
}

async function capture(page, label, width, height, lastEventsUrl, extra = {}) {
  await page.setViewportSize({ width, height });
  await page.waitForTimeout(350);
  const overflow = await page.evaluate(() => ({ viewport: innerWidth, scroll: document.documentElement.scrollWidth }));
  assert.ok(overflow.scroll <= overflow.viewport + 1, `${label}: page overflow ${JSON.stringify(overflow)}`);
  const uiCount = Number((await page.locator('.overview-metrics strong').first().textContent()).trim().replaceAll('.', ''));
  const query = new URL(lastEventsUrl);
  const statsUrl = new URL('/api/estadisticas', api);
  statsUrl.search = query.search;
  const stats = await (await fetch(statsUrl, { signal: AbortSignal.timeout(15000) })).json();
  assert.equal(uiCount, stats.count, `${label}: panel/API count mismatch`);
  const file = `${label}-${width}.png`;
  await page.screenshot({ path: path.join(output, file), fullPage: true, animations: 'disabled', timeout: 30000 });
  captures.push({ file, captured_at_utc: new Date().toISOString(), viewport: { width, height },
    api_query: Object.fromEntries(query.searchParams), period_utc: stats.period, ui_count: uiCount,
    api_count: stats.count, historical_comparison: stats.historical_comparison,
    page_overflow_px: Math.max(0, overflow.scroll - overflow.viewport), ...extra });
  console.log(`${file}: ${uiCount} events, overflow ${Math.max(0, overflow.scroll - overflow.viewport)} px`);
}

async function highlightedPolygons(page) {
  return page.locator('.leaflet-overlay-pane path').evaluateAll(paths => paths.filter(item =>
    (item.getAttribute('stroke') || getComputedStyle(item).stroke || '').toLowerCase() === '#39c4bf').length);
}

try {
  await mkdir(output, { recursive: true });
  await waitHttp(base);
  browser = await chromium.launch({ executablePath: chrome, headless: true, timeout: 15000 });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'es-ES' });
  const pageErrors = [];
  let lastEventsUrl = '';
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => { if (new URL(request.url()).pathname === '/api/eventos') lastEventsUrl = request.url(); });
  await page.route('**/config.json', route => route.fulfill({ json: { mode: 'api', apiUrl: api, refreshMs: 60000, skipNgrokWarning: false } }));
  await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await waitPanel(page);
  assert.match(await page.locator('.applied strong').textContent(), /magnitud ≥4/);
  await capture(page, 'inicio-mag4', 1440, 900, lastEventsUrl);
  await capture(page, 'inicio-mag4', 768, 900, lastEventsUrl);
  await capture(page, 'inicio-mag4', 375, 812, lastEventsUrl);

  const historical = { start: '2025-01-01T00:00', end: '2026-01-01T00:00', mag: '4' };
  await setFilters(page, historical);
  await capture(page, 'conclusion-1-historico-paises', 1440, 900, lastEventsUrl);
  await capture(page, 'conclusion-1-historico-paises', 375, 812, lastEventsUrl);
  await setFilters(page, { ...historical, depthMin: '0', depthMax: '70' });
  await capture(page, 'conclusion-2-historico-profundidad', 1440, 900, lastEventsUrl);
  await capture(page, 'conclusion-2-historico-profundidad', 375, 812, lastEventsUrl);

  const recent = { start: '2026-11-17T00:43', end: '2026-11-18T00:43', mag: '4' };
  await setFilters(page, recent);
  await capture(page, 'conclusion-3-reciente-mag4', 1440, 900, lastEventsUrl);
  await capture(page, 'conclusion-3-reciente-mag4', 375, 812, lastEventsUrl);
  await setFilters(page, { ...recent, mag: '', country: 'USA' });
  assert.ok(await highlightedPolygons(page) > 0, 'USA polygon must be highlighted');
  await capture(page, 'usa-con-eventos', 1440, 900, lastEventsUrl);
  await setFilters(page, { ...recent, country: 'CAN' });
  assert.equal(Number((await page.locator('.overview-metrics strong').first().textContent()).trim()), 0);
  assert.ok(await highlightedPolygons(page) > 0, 'Empty CAN polygon must remain highlighted');
  await capture(page, 'can-sin-eventos', 1440, 900, lastEventsUrl);
  await setFilters(page, { ...recent, country: 'UNASSIGNED' });
  assert.equal(await highlightedPolygons(page), 0, 'UNASSIGNED must not have a polygon');
  await capture(page, 'sin-pais', 1440, 900, lastEventsUrl);

  await setFilters(page, { mode: 'replay', start: '2025-01-01T00:00', end: '2025-02-01T00:00', depthMin: '0', depthMax: '70' });
  assert.match(await page.locator('.applied strong').textContent(), /REPRODUCCIÓN/);
  await capture(page, 'replay-profundidad', 1440, 900, lastEventsUrl);
  await capture(page, 'replay-profundidad', 375, 812, lastEventsUrl);

  if (outage) {
    execFileSync('docker', ['compose', 'stop', 'api'], { cwd: root, timeout: 30000, stdio: 'pipe' });
    apiStopped = true;
    await page.getByRole('button', { name: 'Aplicar filtros' }).click();
    await waitPanel(page, 'No se pudo actualizar');
    assert.match(await page.locator('.status-main').textContent(), /se conserva la última lectura/);
    await page.screenshot({ path: path.join(output, 'api-caida-375.png'), fullPage: true, timeout: 30000 });
    const errorQuery = new URL(lastEventsUrl);
    captures.push({ file: 'api-caida-375.png', captured_at_utc: new Date().toISOString(), viewport: { width: 375, height: 812 },
      state: 'API container stopped; last successful replay view retained', api_query: Object.fromEntries(errorQuery.searchParams),
      period_utc: { start: errorQuery.searchParams.get('start'), end: errorQuery.searchParams.get('end'), timezone: 'UTC' },
      ui_count: Number((await page.locator('.overview-metrics strong').first().textContent()).trim()),
      last_confirmed_api_count: captures.at(-1).api_count, api_count_during_outage: null });
    execFileSync('docker', ['compose', 'up', '-d', 'api'], { cwd: root, timeout: 30000, stdio: 'pipe' });
    apiStopped = false;
    await waitHttp(`${api}/api/salud`, 20000);
    await page.getByRole('button', { name: 'Reintentar consulta' }).click();
    await waitPanel(page);
    await capture(page, 'api-recuperada', 375, 812, lastEventsUrl);
  }
  assert.deepEqual(pageErrors, [], `Browser errors: ${pageErrors.join('; ')}`);
  await writeFile(path.join(output, 'manifest.json'), JSON.stringify({ generated_at_utc: new Date().toISOString(),
    browser: `Chrome ${await browser.version()}`, site: base, api, captures }, null, 2) + '\n');
  console.log(`visual check: passed, ${captures.length} captures`);
} finally {
  if (apiStopped) {
    try { execFileSync('docker', ['compose', 'up', '-d', 'api'], { cwd: root, timeout: 30000, stdio: 'pipe' }); }
    catch (error) { console.error(`API restart failed: ${error.message}`); }
  }
  if (browser) await browser.close();
  server.kill();
}
