import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const output = path.join(root, 'evidence', '002-ingesta-usgs-persistencia', 'visual-depth-night-20261118');
const site = 'https://stellar-basbousa-cee41b.netlify.app/';
const chrome = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const browser = await chromium.launch({ executablePath: chrome, headless: true, timeout: 15000 });
const captures = [];
try {
  await mkdir(output, { recursive: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, locale: 'es-ES' });
  const errors = [];
  let eventsUrl = '';
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (new URL(request.url()).pathname === '/api/eventos') eventsUrl = request.url();
  });
  await page.goto(site, { waitUntil: 'domcontentloaded', timeout: 20000 });
  await page.waitForFunction(() => document.querySelector('.status-main')?.textContent?.includes('API accesible')
    && !document.querySelector('.status-panel .loading'), undefined, { timeout: 30000 });
  assert.match(await page.locator('.applied strong').textContent(), /magnitud ≥4/);
  for (const [width, height] of [[1440, 900], [375, 812]]) {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(350);
    const scroll = await page.evaluate(() => document.documentElement.scrollWidth);
    assert.ok(scroll <= width + 1, `Public ${width}px overflow: ${scroll}`);
    const count = Number((await page.locator('.overview-metrics strong').first().textContent()).trim());
    const query = new URL(eventsUrl);
    const stats = new URL('/api/estadisticas', query.origin);
    stats.search = query.search;
    const response = await fetch(stats, { headers: { 'ngrok-skip-browser-warning': '1' }, signal: AbortSignal.timeout(15000) });
    assert.equal(response.status, 200);
    const payload = await response.json();
    assert.equal(count, payload.count);
    const file = `public-inicio-${width}.png`;
    await page.screenshot({ path: path.join(output, file), fullPage: true, animations: 'disabled', timeout: 30000 });
    captures.push({ file, captured_at_utc: new Date().toISOString(), viewport: { width, height },
      api_query: Object.fromEntries(query.searchParams), period_utc: payload.period,
      ui_count: count, api_count: payload.count, page_overflow_px: Math.max(0, scroll - width) });
    console.log(`${file}: ${count} events, overflow 0 px`);
  }
  assert.deepEqual(errors, []);
  await writeFile(path.join(output, 'public-manifest.json'), JSON.stringify({ generated_at_utc: new Date().toISOString(),
    site, browser: `Chrome ${await browser.version()}`, captures }, null, 2) + '\n');
} finally {
  await browser.close();
}
