export default function Loading() {
  return (
    <div role="status" aria-live="polite" className="space-y-4">
      <p className="text-sm text-muted">Cargando datos desde la API…</p>
      <div className="h-24 animate-pulse rounded-lg border border-line bg-white" />
      <div className="h-24 animate-pulse rounded-lg border border-line bg-white" />
    </div>
  );
}
