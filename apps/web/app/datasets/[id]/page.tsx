import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ApiFailure,
  getDataset,
  getVisualization,
} from "@/lib/api";
import type { DatasetDetail, Resource } from "@/lib/schemas";
import { formatDate, formatDateTime, formatNumber, isoTitle } from "@/lib/format";
import {
  CHANGE_TYPE_LABELS,
  CHECK_STATUS_LABELS,
  RUN_STATUS_LABELS,
  SOURCE_TYPE_LABELS,
  labelFor,
} from "@/lib/labels";
import { ApiErrorState } from "@/components/api-error-state";
import { StatusBadge, toneForCheckStatus } from "@/components/status-badge";

export const metadata = { title: "Detalle de dataset" };

function sourceUrl(dataset: DatasetDetail): string {
  if (dataset.landing_url) return dataset.landing_url;
  const ckanName =
    typeof dataset.raw_metadata?.name === "string"
      ? dataset.raw_metadata.name
      : null;
  if (ckanName && dataset.source.source_type === "ckan") {
    return `${dataset.source.base_url}/dataset/${encodeURIComponent(ckanName)}`;
  }
  return dataset.source.base_url;
}

function changeSummary(summary: Record<string, unknown>): string {
  const parts = Object.entries(summary)
    .slice(0, 4)
    .map(([key, value]) =>
      typeof value === "string" || typeof value === "number"
        ? `${key}: ${value}`
        : null,
    )
    .filter((item): item is string => item !== null);
  return parts.join(" · ");
}

function formatSize(bytes: number | null): string {
  if (bytes === null) return "no declarado";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} kB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ResourceRow({ resource }: { resource: Resource }) {
  return (
    <li className="flex flex-wrap items-start justify-between gap-3 border-b border-line py-3 last:border-b-0">
      <div className="min-w-0">
        <p className="font-medium text-ink">
          {resource.name ?? resource.external_id}
        </p>
        <p className="text-xs text-muted">
          Formato: {resource.format ?? "no declarado"} · Tamaño:{" "}
          {formatSize(resource.file_size)} · MIME:{" "}
          {resource.mime_type ?? "no declarado"}
        </p>
        <a
          href={resource.url}
          target="_blank"
          rel="noopener noreferrer"
          className="break-all text-xs font-mono text-accent underline"
        >
          {resource.url}
        </a>
      </div>
      <div className="flex items-center gap-2">
        <StatusBadge tone={resource.is_available ? "ok" : "neutral"}>
          {resource.is_available ? "disponible" : "no disponible"}
        </StatusBadge>
      </div>
    </li>
  );
}

export default async function DatasetDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  let dataset: DatasetDetail;
  let visualization;
  try {
    [dataset, visualization] = await Promise.all([
      getDataset(id),
      getVisualization(id),
    ]);
  } catch (error) {
    if (error instanceof ApiFailure) {
      if (error.kind === "http" && error.status === 404) notFound();
      return <ApiErrorState error={error} />;
    }
    throw error;
  }

  const coverage =
    dataset.coverage.start || dataset.coverage.end
      ? `${dataset.coverage.start ?? "sin inicio"} → ${dataset.coverage.end ?? "sin fin"}`
      : "sin cobertura declarada";

  return (
    <div className="space-y-8">
      <nav aria-label="Migas de pan" className="text-sm text-muted">
        <Link href="/datasets" className="text-accent underline">
          Explorador de datasets
        </Link>{" "}
        / detalle
      </nav>

      <header className="space-y-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <h1 className="max-w-3xl text-2xl font-bold tracking-tight text-ink">
            {dataset.title}
          </h1>
          <StatusBadge tone={dataset.is_available ? "ok" : "neutral"}>
            {dataset.is_available ? "disponible" : "no disponible"}
          </StatusBadge>
        </div>
        <p className="text-sm text-muted">
          {dataset.organization?.name ?? "Organismo no declarado"} ·{" "}
          {labelFor(SOURCE_TYPE_LABELS, dataset.source.source_type)}:{" "}
          {dataset.source.name}
        </p>
        {dataset.description ? (
          <p className="max-w-3xl whitespace-pre-line text-ink">
            {dataset.description}
          </p>
        ) : null}
        <p className="text-sm">
          <span className="font-medium text-ink">URL de origen: </span>
          <a
            href={sourceUrl(dataset)}
            target="_blank"
            rel="noopener noreferrer"
            className="break-all text-accent underline"
          >
            {sourceUrl(dataset)}
          </a>
        </p>
      </header>

      <section aria-labelledby="metadatos">
        <h2 id="metadatos" className="text-xl font-semibold">
          Metadatos y procedencia
        </h2>
        <dl className="mt-3 grid gap-4 rounded-lg border border-line bg-white p-5 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <dt className="text-sm text-muted">Organismo</dt>
            <dd className="font-medium text-ink">
              {dataset.organization?.name ?? "No declarado"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Tema</dt>
            <dd className="font-medium text-ink">
              {dataset.topic ?? "No declarado"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Licencia</dt>
            <dd className="font-medium text-ink">
              {dataset.license ?? "No declarada"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Formatos</dt>
            <dd className="font-medium text-ink">
              {dataset.formats.join(", ") || "No declarados"}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Cobertura temporal</dt>
            <dd className="font-medium text-ink">{coverage}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Recursos publicados</dt>
            <dd className="font-mono tabular-nums text-ink">
              {formatNumber(dataset.resource_count)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">
              Última actualización declarada por la fuente
            </dt>
            <dd
              className="text-ink"
              title={isoTitle(dataset.last_source_update)}
            >
              {formatDateTime(dataset.last_source_update)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Última sincronización exitosa</dt>
            <dd
              className="text-ink"
              title={isoTitle(dataset.last_successful_sync)}
            >
              {formatDateTime(dataset.last_successful_sync)}
            </dd>
          </div>
          <div>
            <dt className="text-sm text-muted">Snapshots RAW preservados</dt>
            <dd className="font-mono tabular-nums text-ink">
              {formatNumber(dataset.provenance.raw_snapshot_count)}
            </dd>
          </div>
        </dl>
        <p className="mt-2 text-xs text-muted">
          Cada sincronización conserva el artefacto original descargado de la
          fuente; los metadatos publicados aquí se normalizan a partir de ese
          artefacto y registran la versión de transformación aplicada.
        </p>
      </section>

      <section aria-labelledby="recursos">
        <h2 id="recursos" className="text-xl font-semibold">
          Recursos ({formatNumber(dataset.resources.length)})
        </h2>
        <p className="mt-1 text-sm text-muted">
          Archivos y enlaces tal como los publica la fuente. Esta fase expone
          metadatos; todavía no se importaron sus tablas de datos.
        </p>
        {dataset.resources.length === 0 ? (
          <p className="mt-3 rounded-lg border border-dashed border-line bg-white p-4 text-sm text-muted">
            La fuente no declaró recursos para este dataset.
          </p>
        ) : (
          <ul className="mt-3 rounded-lg border border-line bg-white px-5">
            {dataset.resources.map((resource) => (
              <ResourceRow key={resource.id} resource={resource} />
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="validaciones">
        <h2 id="validaciones" className="text-xl font-semibold">
          Validaciones de la última sincronización
        </h2>
        {dataset.quality_checks.length === 0 ? (
          <p className="mt-3 rounded-lg border border-dashed border-line bg-white p-4 text-sm text-muted">
            No hay chequeos de calidad registrados para la última ejecución.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {dataset.quality_checks.map((check) => (
              <li
                key={check.id}
                className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3"
              >
                <div>
                  <p className="font-medium text-ink">
                    {check.check_type.replaceAll("_", " ")}
                  </p>
                  <p className="font-mono text-xs text-muted">
                    {JSON.stringify(check.details)}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="text-xs text-muted"
                    title={isoTitle(check.checked_at)}
                  >
                    {formatDateTime(check.checked_at)}
                  </span>
                  <StatusBadge tone={toneForCheckStatus(check.status)}>
                    {labelFor(CHECK_STATUS_LABELS, check.status)}
                  </StatusBadge>
                </div>
              </li>
            ))}
          </ul>
        )}
        {dataset.latest_run ? (
          <p className="mt-3 text-sm text-muted">
            Ejecución:{" "}
            <span className="font-mono">{dataset.latest_run.run_type}</span> ·{" "}
            {labelFor(RUN_STATUS_LABELS, dataset.latest_run.status)} · leídos{" "}
            {formatNumber(dataset.latest_run.records_read)}, aceptados{" "}
            {formatNumber(dataset.latest_run.records_accepted)}, rechazados{" "}
            {formatNumber(dataset.latest_run.records_rejected)}.{" "}
            <Link
              href={`/historial?run=${dataset.latest_run.id}`}
              className="text-accent underline"
            >
              Ver en el historial
            </Link>
          </p>
        ) : null}
      </section>

      <section aria-labelledby="visualizacion">
        <h2 id="visualizacion" className="text-xl font-semibold">
          Visualización
        </h2>
        <div className="mt-3 rounded-lg border border-accent/30 bg-accent-soft p-5">
          <p className="font-semibold text-accent-deep">
            {visualization.available
              ? `Visualizaciones disponibles: ${visualization.visualizations.length}`
              : "Todavía no hay una visualización real para este dataset"}
          </p>
          <p className="mt-2 text-sm text-ink">{visualization.reason}</p>
        </div>
      </section>

      <section aria-labelledby="historial-dataset">
        <h2 id="historial-dataset" className="text-xl font-semibold">
          Historial de cambios detectados
        </h2>
        {dataset.changes.length === 0 ? (
          <p className="mt-3 rounded-lg border border-dashed border-line bg-white p-4 text-sm text-muted">
            No se registraron cambios para este dataset desde su incorporación.
          </p>
        ) : (
          <ul className="mt-3 space-y-2">
            {dataset.changes.map((change) => (
              <li
                key={change.id}
                className="rounded-lg border border-line bg-white px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="font-medium text-ink">
                    {labelFor(CHANGE_TYPE_LABELS, change.change_type)}
                  </p>
                  <span
                    className="text-xs text-muted"
                    title={isoTitle(change.detected_at)}
                  >
                    {formatDateTime(change.detected_at)}
                  </span>
                </div>
                <p className="mt-1 font-mono text-xs text-muted">
                  {changeSummary(change.change_summary) || "sin detalle"}
                </p>
              </li>
            ))}
          </ul>
        )}
        {dataset.changes.length > 0 ? (
          <p className="mt-2 text-xs text-muted">
            Se muestran hasta 50 cambios, del más reciente al más antiguo.
            Cobertura temporal de los datos: {formatDate(dataset.coverage.start)}{" "}
            → {formatDate(dataset.coverage.end)}.
          </p>
        ) : null}
      </section>
    </div>
  );
}
