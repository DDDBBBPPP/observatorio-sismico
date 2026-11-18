import { CommonModule } from '@angular/common';
import { Component, OnDestroy, computed, signal } from '@angular/core';
import { LeafletDirective } from '@bluehalo/ngx-leaflet';
import * as L from 'leaflet';
import type { FeatureCollection, Point } from 'geojson';
import { buildQuery, emptyFilters, type FilterState } from './filter-query';

type Properties = { mag: number | null; place: string | null; time: number; updated: number; country_id?: string | null; country_name?: string | null; replay_at?: string | null };
type Events = FeatureCollection<Point, Properties> & { metadata?: { generated?: number; mode?: string; total?: number; truncated?: boolean; last_source_fetch?: number | null; filters?: { country_id: string | null; min_mag: number | null } } };
type Config = { mode: 'demo' | 'api'; apiUrl: string; refreshMs: number; skipNgrokWarning: boolean };
type Bin = { label: string; count: number };
type Country = { code: string; name: string };
type CountryStat = { country_id: string; country_name: string; count: number };
type CountryBin = Bin & { code: string };
type Statistics = { count: number; period: { start: string; end: string }; filters: { min_mag: number | null; country_id: string | null }; hourly_utc: { hour_utc: string; count: number }[]; countries: CountryStat[]; distributions: { magnitude: { bins: Bin[]; null_count: number }; depth_km: { bins: Bin[]; null_count: number } }; historical_comparison?: { average_for_window: number; current_window_events: number; min_mag: number; window_days: number; events: number } };

@Component({
  selector: 'app-root', standalone: true, imports: [CommonModule, LeafletDirective],
  templateUrl: './app.component.html', styleUrl: './app.component.css'
})
export class AppComponent implements OnDestroy {
  readonly mode = signal('Cargando configuración');
  readonly status = signal('Preparando el mapa…');
  readonly loading = signal(false);
  readonly hasError = signal(false);
  readonly lastRead = signal('Sin lectura');
  readonly generated = signal('Sin información');
  readonly lastIngestion = signal('Sin información');
  readonly latestEvent = signal('Sin eventos en el filtro');
  readonly count = signal(0);
  readonly omitted = signal(0);
  readonly countriesStatus = signal('Cargando catálogo');
  readonly countryOptions = signal<Country[]>([]);
  readonly apiStale = signal('');
  readonly stats = signal<Statistics | null>(null);
  readonly appliedPeriod = signal('Esperando respuesta de la API');
  readonly start = signal('');
  readonly end = signal('');
  readonly minMag = signal('');
  readonly country = signal('');
  readonly viewMode = signal<'live' | 'replay'>('live');
  readonly applied = signal<FilterState>(emptyFilters());
  readonly pending = computed(() => JSON.stringify(this.draft()) !== JSON.stringify(this.applied()));
  readonly appliedLabel = computed(() => {
    const selected = this.applied();
    const period = selected.start || selected.end ? `${selected.start || '24 h antes del final'} → ${selected.end || 'ahora'} UTC` : 'últimas 24 h UTC';
    const name = selected.country === 'UNASSIGNED' ? 'Sin país asignado' : this.countryOptions().find(item => item.code === selected.country)?.name;
    return `${selected.viewMode === 'replay' ? 'REPRODUCCIÓN' : 'Datos reales'} · ${period} · magnitud ${selected.minMag ? `≥${selected.minMag}` : 'todas'} · ${selected.country ? `${name || selected.country}${name ? ` (${selected.country})` : ''}` : 'todos los países'}`;
  });
  readonly truncated = signal(false);
  readonly tableEvents = signal<FeatureCollection<Point, Properties>['features']>([]);
  readonly options: L.MapOptions = { center: L.latLng(18, 0), zoom: 2, minZoom: 2, maxZoom: 8, preferCanvas: true, worldCopyJump: false };
  private map?: L.Map;
  private events = L.layerGroup();
  private positions: L.LatLng[] = [];
  private timer?: ReturnType<typeof setTimeout>;
  private controller = new AbortController();
  private destroyed = false;
  private requestId = 0;
  private currentConfig?: Config;

  async onMapReady(map: L.Map): Promise<void> {
    this.map = map;
    const base = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19, noWrap: true, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    const borders = L.geoJSON(undefined, { style: { color: '#334155', weight: 1, fill: false },
      onEachFeature: (feature, layer) => {
        const name = document.createElement('span');
        name.textContent = feature.properties?.NAME_ES ?? feature.properties?.ADMIN ?? 'Sin nombre';
        layer.bindTooltip(name);
      }
    }).addTo(map);
    this.events.addTo(map);
    L.control.layers({ 'OpenStreetMap': base }, { 'Países (Natural Earth)': borders, 'Terremotos': this.events }).addTo(map);
    map.attributionControl.addAttribution('Fronteras: Natural Earth · Datos reales: USGS');
    try {
      const catalog = await this.readJson<FeatureCollection>('datos/paises.geojson');
      borders.addData(catalog);
      const countries = catalog.features.map(feature => ({
        code: String(feature.properties?.['ADM0_A3'] ?? ''),
        name: String(feature.properties?.['NAME_ES'] || feature.properties?.['ADMIN'] || feature.properties?.['NAME'] || '')
      })).filter(item => item.code && item.name);
      this.countryOptions.set(countries.sort((a, b) => a.name.localeCompare(b.name, 'es')));
      this.countriesStatus.set('Catálogo de países cargado');
    } catch { this.countriesStatus.set('No se pudo cargar el catálogo de países'); }
    if (this.destroyed) return;
    try {
      const config = await this.readJson<Config>('config.json');
      if (!['demo', 'api'].includes(config.mode)) throw new Error('Modo inválido');
      this.currentConfig = config;
      this.mode.set(config.mode === 'demo' ? 'DEMOSTRACIÓN · datos ficticios' : 'API · datos del backend');
      await this.refresh(config, this.applied());
    } catch { this.status.set('Error: revisa public/config.json'); }
  }

  private async readJson<T>(url: string, headers: Record<string, string> = {}): Promise<T> {
    const response = await fetch(url, { headers, cache: 'no-store', signal: AbortSignal.any([this.controller.signal, AbortSignal.timeout(15000)]) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json() as Promise<T>;
  }
  private draft(): FilterState {
    return { viewMode: this.viewMode(), start: this.start(), end: this.end(), minMag: this.minMag(), country: this.country() };
  }
  private async refresh(config: Config, selected: FilterState, recenter = false): Promise<void> {
    clearTimeout(this.timer);
    const requestId = ++this.requestId;
    this.loading.set(true);
    try {
      const headers: Record<string, string> = {};
      if (config.mode === 'api' && config.skipNgrokWarning) headers['ngrok-skip-browser-warning'] = '1';
      const query = config.mode === 'api' ? buildQuery(selected) : '';
      const base = config.apiUrl.replace(/\/$/, '');
      const data = await this.readJson<Events>(config.mode === 'demo' ? 'datos/terremotos-demo.geojson' : `${base}/api/eventos${query}`, headers);
      if (this.destroyed || requestId !== this.requestId) return;
      if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) throw new Error('Se esperaba FeatureCollection');
      const summary = config.mode === 'api' ? await this.readJson<Statistics>(`${base}/api/estadisticas${query}`, headers) : null;
      if (this.destroyed || requestId !== this.requestId) return;
      if (config.mode === 'api' && (data.metadata?.mode !== selected.viewMode ||
        data.metadata?.filters?.country_id !== (selected.country || null) ||
        data.metadata?.filters?.min_mag !== (selected.minMag ? Number(selected.minMag) : null) ||
        summary?.filters.country_id !== (selected.country || null) ||
        summary?.filters.min_mag !== (selected.minMag ? Number(selected.minMag) : null))) {
        throw new Error('La API no confirmó los filtros solicitados');
      }
      const next = L.layerGroup();
      const positions: L.LatLng[] = [];
      let omitted = 0;
      for (const feature of data.features) {
        const p = feature.properties;
        const c = feature.geometry?.type === 'Point' ? feature.geometry.coordinates : [];
        const [lon, lat, depth] = c;
        if (!p || !Number.isFinite(lon) || !Number.isFinite(lat) || Math.abs(lon) > 180 || Math.abs(lat) > 90) { omitted++; continue; }
        const magnitude = typeof p.mag === 'number' && Number.isFinite(p.mag) ? p.mag : null;
        const depthOk = typeof depth === 'number' && Number.isFinite(depth);
        const color = !depthOk ? '#64748b' : depth < 70 ? '#e8a317' : depth < 300 ? '#e35b37' : '#7b3fb6';
        const popup = document.createElement('div');
        popup.textContent = `${p.place ?? 'Sin descripción'}\nMagnitud: ${magnitude ?? 'ND'}\nProfundidad: ${depthOk ? depth + ' km' : 'ND'}\nFecha original UTC: ${this.date(p.time)}\n${selected.viewMode === 'replay' ? `Reproducido UTC: ${this.replayDate(p.replay_at)}\n` : ''}País: ${this.countryDisplay(p.country_id, p.country_name)}\nID: ${feature.id ?? 'ND'}`;
        const point = L.latLng(lat, lon);
        positions.push(point);
        L.circleMarker(point, { radius: magnitude === null ? 4 : Math.max(3, Math.min(18, 3 + (magnitude + 1) * 2)), color, fillColor: color, fillOpacity: .75, weight: 1 }).bindPopup(popup).addTo(next);
      }
      this.events.clearLayers(); this.events.addLayer(next);
      this.positions = positions;
      if (recenter && this.map) {
        if (selected.viewMode === 'live' && !selected.country && !selected.start && !selected.end && !selected.minMag) this.map.setView(this.options.center!, this.options.zoom!);
        else if (positions.length === 1) this.map.setView(positions[0], 5);
        else if (positions.length > 1 && (selected.country !== 'UNASSIGNED' || positions.length <= 30)) this.map.fitBounds(L.latLngBounds(positions).pad(0.15), { maxZoom: 6 });
      }
      this.count.set(positions.length);
      this.omitted.set(omitted);
      this.truncated.set(Boolean(data.metadata?.truncated));
      this.lastRead.set(new Date().toISOString());
      this.generated.set(this.date(data.metadata?.generated));
      this.tableEvents.set(data.features.slice(0, 100));
      this.latestEvent.set(data.features.length ? this.date(data.features[0].properties.time) : 'Sin eventos en el filtro');
      const sourceFetch = data.metadata?.last_source_fetch;
      this.lastIngestion.set(sourceFetch ? this.date(sourceFetch) : 'Sin consulta confirmada');
      this.apiStale.set(selected.viewMode === 'live' && sourceFetch && Date.now() - sourceFetch > 10 * 60 * 1000
        ? 'Aviso: la última consulta USGS correcta supera 10 minutos.' : '');
      this.stats.set(summary);
      this.applied.set({ ...selected });
      this.appliedPeriod.set(summary?.period ? `${summary.period.start.replace('T', ' ').slice(0, 16)} → ${summary.period.end.replace('T', ' ').slice(0, 16)} UTC` : this.appliedLabel());
      this.hasError.set(false);
      this.status.set(config.mode === 'demo' ? 'Ejemplo estático: no representa actividad real' : selected.viewMode === 'replay' ? 'REPRODUCCIÓN · consulta completada' : 'API accesible · consulta completada');
    } catch (error) {
      if (!this.destroyed && requestId === this.requestId) {
        this.hasError.set(true);
        this.status.set(`No se pudo actualizar: se conserva la última lectura. ${error instanceof Error ? error.message : 'Revisa API, túnel y CORS.'}`);
      }
    } finally {
      if (!this.destroyed && requestId === this.requestId) {
        this.loading.set(false);
        if (config.mode === 'api') this.timer = setTimeout(() => void this.refresh(config, this.applied()), Math.max(30000, Number(config.refreshMs) || 60000));
      }
    }
  }
  applyFilter(name: 'start' | 'end' | 'minMag' | 'country', event: Event): void {
    this[name].set((event.target as HTMLInputElement).value);
  }
  applyFilters(): void { if (this.currentConfig) void this.refresh(this.currentConfig, this.draft(), true); }
  retry(): void { if (this.currentConfig) void this.refresh(this.currentConfig, this.applied()); }
  fitMap(): void {
    if (!this.map) return;
    if (this.positions.length === 1) this.map.setView(this.positions[0], 5);
    else if (this.positions.length > 1) this.map.fitBounds(L.latLngBounds(this.positions).pad(0.12), { maxZoom: 6 });
    else this.map.setView(this.options.center!, this.options.zoom!);
  }
  clearFilters(): void {
    const empty = emptyFilters(this.viewMode());
    this.start.set(empty.start); this.end.set(empty.end); this.minMag.set(''); this.country.set('');
    if (this.currentConfig) void this.refresh(this.currentConfig, empty, true);
  }
  setViewMode(event: Event): void {
    const viewMode = (event.target as HTMLSelectElement).value === 'replay' ? 'replay' : 'live';
    const empty = emptyFilters(viewMode);
    this.viewMode.set(viewMode); this.start.set(empty.start); this.end.set(empty.end); this.minMag.set(''); this.country.set('');
    if (this.currentConfig) void this.refresh(this.currentConfig, empty, true);
  }
  barWidth(count: number, values: { count: number }[]): number {
    return Math.max(2, Math.round(100 * count / Math.max(1, ...values.map(value => value.count))));
  }
  countryName(code: string | null | undefined, fallback?: string | null): string {
    if (!code || code === 'UNASSIGNED') return 'Sin país asignado';
    return this.countryOptions().find(item => item.code === code)?.name || fallback || code;
  }
  countryDisplay(code: string | null | undefined, fallback?: string | null): string {
    return code && code !== 'UNASSIGNED' ? `${this.countryName(code, fallback)} (${code})` : 'Sin país asignado';
  }
  percent(count: number, total: number): number { return total > 0 ? 100 * count / total : 0; }
  countryChart(countries: Statistics['countries']): CountryBin[] {
    const selected = countries.slice(0, 6);
    const unassigned = countries.find(item => item.country_id === 'UNASSIGNED');
    if (unassigned && !selected.includes(unassigned)) selected.push(unassigned);
    const other = countries.filter(item => !selected.includes(item)).reduce((sum, item) => sum + item.count, 0);
    return [...selected.map(item => ({ label: this.countryDisplay(item.country_id, item.country_name), code: item.country_id, count: item.count })), ...(other ? [{ label: 'Otros países', code: 'OTHER', count: other }] : [])];
  }
  otherCountries(countries: Statistics['countries']): CountryStat[] {
    const shown = new Set(this.countryChart(countries).map(item => item.code));
    return countries.filter(item => !shown.has(item.country_id));
  }
  hourlyChart(hours: Statistics['hourly_utc']): Bin[] {
    return hours.slice(-8).map(item => ({ label: `${item.hour_utc.slice(0, 16).replace('T', ' ')} UTC`, count: item.count }));
  }
  date(value: unknown): string {
    if (typeof value !== 'number' || !Number.isFinite(value)) return 'ND';
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'ND' : date.toISOString();
  }
  depth(feature: FeatureCollection<Point, Properties>['features'][number]): number | 'ND' {
    const value = feature.geometry.coordinates[2];
    return typeof value === 'number' && Number.isFinite(value) ? value : 'ND';
  }
  replayDate(value: unknown): string {
    return typeof value === 'string' && !Number.isNaN(Date.parse(value)) ? new Date(value).toISOString() : 'ND';
  }
  ngOnDestroy(): void { this.destroyed = true; clearTimeout(this.timer); this.controller.abort(); }
}
