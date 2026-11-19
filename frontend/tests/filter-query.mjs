import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

const source = readFileSync(new URL('../src/app/filter-query.ts', import.meta.url), 'utf8');
const javascript = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 }
}).outputText;
const { buildQuery, emptyFilters } = await import(`data:text/javascript,${encodeURIComponent(javascript)}`);

const now = new Date('2026-11-16T12:00:00Z');
const params = filters => new URLSearchParams(buildQuery(filters, now).slice(1));
const usa = params({ ...emptyFilters(), country: 'USA', minMag: '4' });
assert.equal(usa.get('mode'), 'live');
assert.equal(usa.get('country_id'), 'USA');
assert.equal(usa.get('min_mag'), '4');
assert.equal(usa.get('start'), '2026-11-15T12:00:00.000Z');
assert.equal(usa.get('end'), '2026-11-16T12:00:00.000Z');
assert.equal(params({ ...emptyFilters(), country: 'ESP' }).get('country_id'), 'ESP');
assert.equal(params({ ...emptyFilters(), country: 'UNASSIGNED' }).get('country_id'), 'UNASSIGNED');
assert.equal(params(emptyFilters('replay')).get('mode'), 'replay');
assert.equal(params(emptyFilters('replay')).get('start'), '2025-01-01T00:00:00.000Z');
assert.equal(params(emptyFilters('replay')).get('end'), '2025-02-01T00:00:00.000Z');
assert.equal(params(emptyFilters()).has('country_id'), false);
assert.equal(params(emptyFilters()).has('min_depth_km'), false);
const shallow = params({ ...emptyFilters(), minDepthKm: '0', maxDepthKm: '70' });
assert.equal(shallow.get('min_depth_km'), '0');
assert.equal(shallow.get('max_depth_km'), '70');
assert.equal(params({ ...emptyFilters('replay'), minDepthKm: '-2.5' }).get('min_depth_km'), '-2.5');
assert.throws(() => buildQuery({ ...emptyFilters(), minDepthKm: 'x' }, now), /número finito/);
assert.throws(() => buildQuery({ ...emptyFilters(), minDepthKm: 'NaN' }, now), /número finito/);
assert.throws(() => buildQuery({ ...emptyFilters(), minDepthKm: '300', maxDepthKm: '70' }, now), /no puede superar/);
assert.throws(() => buildQuery({ ...emptyFilters(), start: '2026-11-17T00:00', end: '2026-11-16T00:00' }, now));
console.log('filter query: passed');
