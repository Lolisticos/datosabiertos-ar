import type { IndicatorDetail } from "@/lib/schemas";
import { formatDateTime, isoTitle } from "@/lib/format";

export function SourceAttribution({ indicator }: { indicator: IndicatorDetail }) {
  return (
    <section className="rounded-lg border border-line bg-white p-5" aria-labelledby="transparencia-titulo">
      <h2 id="transparencia-titulo" className="text-lg font-semibold">Fuente y metodología</h2>
      <dl className="mt-4 grid gap-x-8 gap-y-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="font-medium text-muted">Fuente primaria</dt>
          <dd className="mt-1 text-ink">{indicator.source?.name ?? "No informada"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted">Serie oficial</dt>
          <dd className="mt-1 font-mono text-xs text-ink">{indicator.source_series_id ?? "No informada"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted">Descarga RAW</dt>
          <dd className="mt-1 text-ink" title={isoTitle(indicator.downloaded_at)}>
            {formatDateTime(indicator.downloaded_at)}
          </dd>
        </div>
        <div>
          <dt className="font-medium text-muted">Transformación</dt>
          <dd className="mt-1 text-ink">
            {indicator.transformation_name ?? "Sin publicar"}
            {indicator.transformation_version ? ` · v${indicator.transformation_version}` : ""}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="font-medium text-muted">Definición metodológica</dt>
          <dd className="mt-1 max-w-4xl text-ink">{indicator.methodology ?? "No informada"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted">Hash RAW (SHA-256)</dt>
          <dd className="mt-1 break-all font-mono text-xs text-ink">{indicator.raw_content_hash ?? "No disponible"}</dd>
        </div>
        <div>
          <dt className="font-medium text-muted">Hash normalizado (SHA-256)</dt>
          <dd className="mt-1 break-all font-mono text-xs text-ink">{indicator.normalized_hash ?? "No disponible"}</dd>
        </div>
      </dl>
      <div className="mt-5 flex flex-wrap gap-4 text-sm">
        {indicator.methodology_url ? (
          <a className="font-medium text-accent underline" href={indicator.methodology_url} target="_blank" rel="noopener noreferrer">
            Metodología oficial
          </a>
        ) : null}
        {indicator.source_url ? (
          <a className="font-medium text-accent underline" href={indicator.source_url} target="_blank" rel="noopener noreferrer">
            Respuesta oficial vía API
          </a>
        ) : null}
        <span>Licencia: {indicator.license ?? "No informada"}</span>
      </div>
    </section>
  );
}
