export type FilterState = {
  viewMode: 'live' | 'replay';
  start: string;
  end: string;
  minMag: string;
  minDepthKm: string;
  maxDepthKm: string;
  country: string;
};

export const emptyFilters = (viewMode: 'live' | 'replay' = 'live'): FilterState => ({
  viewMode,
  start: viewMode === 'replay' ? '2025-01-01T00:00' : '',
  end: viewMode === 'replay' ? '2025-02-01T00:00' : '',
  minMag: '',
  minDepthKm: '',
  maxDepthKm: '',
  country: ''
});

/** One frozen UTC window is shared by the events and statistics requests. */
export function buildQuery(selected: FilterState, now = new Date()): string {
  const params = new URLSearchParams();
  params.set('mode', selected.viewMode);
  const end = selected.end ? new Date(`${selected.end}Z`) : now;
  const start = selected.start ? new Date(`${selected.start}Z`) : new Date(end.getTime() - 86400000);
  if (!Number.isFinite(start.getTime()) || !Number.isFinite(end.getTime()) || start >= end) {
    throw new Error('El periodo UTC no es válido');
  }
  params.set('start', start.toISOString());
  params.set('end', end.toISOString());
  if (selected.minMag) params.set('min_mag', selected.minMag);
  const depth = (raw: string, label: string): number | null => {
    if (raw.trim() === '') return null;
    const value = Number(raw);
    if (!Number.isFinite(value)) throw new Error(`${label} debe ser un número finito en km`);
    return value;
  };
  const minDepth = depth(selected.minDepthKm, 'La profundidad mínima');
  const maxDepth = depth(selected.maxDepthKm, 'La profundidad máxima');
  if (minDepth !== null && maxDepth !== null && minDepth > maxDepth) {
    throw new Error('La profundidad mínima no puede superar la máxima');
  }
  if (minDepth !== null) params.set('min_depth_km', String(minDepth));
  if (maxDepth !== null) params.set('max_depth_km', String(maxDepth));
  if (selected.country) params.set('country_id', selected.country);
  return `?${params.toString()}`;
}
