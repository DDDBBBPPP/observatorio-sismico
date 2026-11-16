export type FilterState = {
  viewMode: 'live' | 'replay';
  start: string;
  end: string;
  minMag: string;
  country: string;
};

export const emptyFilters = (viewMode: 'live' | 'replay' = 'live'): FilterState => ({
  viewMode,
  start: viewMode === 'replay' ? '2025-01-01T00:00' : '',
  end: viewMode === 'replay' ? '2025-02-01T00:00' : '',
  minMag: '',
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
  if (selected.country) params.set('country_id', selected.country);
  return `?${params.toString()}`;
}
