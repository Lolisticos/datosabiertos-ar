import Link from "next/link";
import { ApiFailure, getSources } from "@/lib/api";
import { formatDateTime, formatNumber, isoTitle } from "@/lib/format";
import { SOURCE_TYPE_LABELS, labelFor } from "@/lib/labels";
import { ApiErrorState } from "@/components/api-error-state";
import { EmptyState } from "@/components/empty-state";
import {
  StatusBadge,
  toneForRunStatus,
} from "@/components/status-badge";

export const metadata = { title: "Fuentes oficiales" };

export default async function SourcesPage() {
  let sources;
  try {
    sources = await getSources();
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }

  return (
    <div className="space-y-8">
      <section aria-labelledby="fuentes-titulo">
        <h1 id="fuentes-titulo" className="text-2xl font-bold tracking-tight">
          Fuentes oficiales
        </h1>
        <p className="mt-2 max-w-3xl text-muted">
          Cada fuente es un catálogo publicado por un organismo oficial. La
          plataforma solo consulta las fuentes registradas y autorizadas; no
          descarga URLs arbitrarias. Para cada una se informa cobertura,
          licencia declarada y el resultado de la última sincronización.
        </p>
      </section>

      {sources.length === 0 ? (
        <EmptyState title="Todavía no hay fuentes registradas">
          El catálogo se poblará cuando se ejecute una ingesta sobre una fuente
          autorizada.
        </EmptyState>
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {sources.map((source) => (
            <li
              key={source.id}
              className="flex flex-col rounded-lg border border-line bg-white p-5"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="text-lg font-semibold text-ink">
                    {source.name}
                  </h2>
                  <p className="text-xs text-muted">
                    Identificador interno:{" "}
                    <span className="font-mono">{source.slug}</span>
                  </p>
                </div>
                <StatusBadge
                  tone={toneForRunStatus(source.last_run_status ?? "")}
                >
                  {source.last_run_status
                    ? `último estado: ${source.last_run_status}`
                    : "sin ejecuciones"}
                </StatusBadge>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-muted">Tipo de acceso</dt>
                  <dd className="font-medium text-ink">
                    {labelFor(SOURCE_TYPE_LABELS, source.source_type)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Datasets catalogados</dt>
                  <dd className="font-mono tabular-nums text-ink">
                    {formatNumber(source.dataset_count)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Organismo responsable</dt>
                  <dd className="font-medium text-ink">
                    {source.organization?.name ?? "No declarado"}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Licencia</dt>
                  <dd className="font-medium text-ink">
                    {source.license ?? "Se registra por dataset"}
                  </dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-muted">Última sincronización exitosa</dt>
                  <dd
                    className="text-ink"
                    title={isoTitle(source.last_successful_run_at)}
                  >
                    {formatDateTime(source.last_successful_run_at)}
                  </dd>
                </div>
              </dl>

              {source.notes ? (
                <p className="mt-3 border-t border-line pt-3 text-sm text-muted">
                  {source.notes}
                </p>
              ) : null}

              <div className="mt-4 flex flex-wrap items-center gap-3 border-t border-line pt-4 text-sm">
                <a
                  href={source.base_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-accent underline"
                >
                  Ir al catálogo original
                </a>
                <Link
                  href={`/datasets?source=${encodeURIComponent(source.slug)}`}
                  className="font-semibold text-accent underline"
                >
                  Explorar sus datasets
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
