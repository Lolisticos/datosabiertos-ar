import Link from "next/link";
import {
  ApiFailure,
  getChanges,
  getRun,
  getRuns,
  getSources,
} from "@/lib/api";
import type { ChangeListItem, Run } from "@/lib/schemas";
import { formatDateTime, formatNumber, isoTitle } from "@/lib/format";
import {
  CHANGE_TYPE_LABELS,
  CHECK_STATUS_LABELS,
  RUN_STATUSES,
  RUN_STATUS_LABELS,
  RUN_TYPE_LABELS,
  labelFor,
} from "@/lib/labels";
import { ApiErrorState } from "@/components/api-error-state";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";
import {
  StatusBadge,
  toneForCheckStatus,
  toneForRunStatus,
} from "@/components/status-badge";

export const metadata = { title: "Historial de sincronización" };

type SearchParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function duration(run: Run): string {
  if (!run.finished_at) return "en curso";
  const started = new Date(run.started_at).getTime();
  const finished = new Date(run.finished_at).getTime();
  if (Number.isNaN(started) || Number.isNaN(finished)) return "sin registro";
  const seconds = Math.max(0, Math.round((finished - started) / 1000));
  return `${formatNumber(seconds)} s`;
}

function changeSummary(change: ChangeListItem): string {
  const parts = Object.entries(change.change_summary)
    .slice(0, 4)
    .map(([key, value]) =>
      typeof value === "string" || typeof value === "number"
        ? `${key}: ${value}`
        : null,
    )
    .filter((item): item is string => item !== null);
  return parts.join(" · ");
}

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const raw = await searchParams;
  const runId = first(raw.run) || undefined;
  const source = first(raw.source) || undefined;
  const status = first(raw.status) || undefined;
  const changeType = first(raw.change_type) || undefined;
  const runsPage = positiveInt(first(raw.runs_page), 1);
  const changesPage = positiveInt(first(raw.changes_page), 1);

  let sources;
  let runs;
  let runDetail;
  let changes;
  try {
    [sources, runs, runDetail, changes] = await Promise.all([
      getSources(),
      getRuns({ source, status, page: runsPage, page_size: 10 }),
      runId ? getRun(runId) : Promise.resolve(null),
      getChanges({ change_type: changeType, page: changesPage, page_size: 10 }),
    ]);
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }

  return (
      <div className="space-y-10">
        <section aria-labelledby="historial-titulo">
          <h1 id="historial-titulo" className="text-2xl font-bold tracking-tight">
            Historial de sincronización
          </h1>
          <p className="mt-2 max-w-3xl text-muted">
            Registro estructurado de cada ejecución de ingesta y de los cambios
            detectados en el catálogo. Una modificación de formato u orden de
            registros no cuenta como cambio de contenido: solo se registra lo
            que altera los metadatos normalizados.
          </p>
        </section>

        <section aria-labelledby="ejecuciones">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 id="ejecuciones" className="text-xl font-semibold">
              Ejecuciones de ingesta
            </h2>
            <form method="get" action="/historial" className="flex flex-wrap items-end gap-2">
              <label className="text-sm text-ink">
                Fuente
                <select
                  name="source"
                  defaultValue={source ?? ""}
                  className="mt-1 block rounded-md border border-line bg-white px-2 py-1.5 text-sm"
                >
                  <option value="">Todas</option>
                  {sources.map((item) => (
                    <option key={item.id} value={item.slug}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm text-ink">
                Estado
                <select
                  name="status"
                  defaultValue={status ?? ""}
                  className="mt-1 block rounded-md border border-line bg-white px-2 py-1.5 text-sm"
                >
                  <option value="">Todos</option>
                  {RUN_STATUSES.map((item) => (
                    <option key={item} value={item}>
                      {labelFor(RUN_STATUS_LABELS, item)}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                className="rounded-md bg-accent px-4 py-1.5 text-sm font-semibold text-white hover:bg-accent-deep"
              >
                Filtrar
              </button>
            </form>
          </div>

          {runDetail ? (
            <div className="mt-4 rounded-lg border border-accent/30 bg-white p-5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-ink">
                    Ejecución {formatDateTime(runDetail.started_at)}
                  </h3>
                  <p className="text-sm text-muted">
                    {labelFor(RUN_TYPE_LABELS, runDetail.run_type)} ·{" "}
                    {runDetail.source?.name ?? "fuente no registrada"} ·
                    disparada por {runDetail.triggered_by} · transformación{" "}
                    {runDetail.transformation_version ?? "no declarada"}
                  </p>
                </div>
                <StatusBadge tone={toneForRunStatus(runDetail.status)}>
                  {labelFor(RUN_STATUS_LABELS, runDetail.status)}
                </StatusBadge>
              </div>
              <p className="mt-3 text-sm text-ink">
                Leídos{" "}
                <span className="font-mono tabular-nums">
                  {formatNumber(runDetail.records_read)}
                </span>
                , aceptados{" "}
                <span className="font-mono tabular-nums">
                  {formatNumber(runDetail.records_accepted)}
                </span>
                , rechazados{" "}
                <span className="font-mono tabular-nums">
                  {formatNumber(runDetail.records_rejected)}
                </span>
                . Duración: {duration(runDetail)}.
              </p>
              {runDetail.error_summary ? (
                <p className="mt-2 rounded-md border border-danger/40 bg-danger/5 p-3 text-sm text-danger">
                  {runDetail.error_summary}
                </p>
              ) : null}
              {runDetail.quality_checks.length > 0 ? (
                <ul className="mt-4 space-y-2">
                  {runDetail.quality_checks.map((check) => (
                    <li
                      key={check.id}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-paper px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium text-ink">
                          {check.check_type.replaceAll("_", " ")}
                        </p>
                        <p className="font-mono text-xs text-muted">
                          {JSON.stringify(check.details)}
                        </p>
                      </div>
                      <StatusBadge tone={toneForCheckStatus(check.status)}>
                        {labelFor(CHECK_STATUS_LABELS, check.status)}
                      </StatusBadge>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-3 text-sm text-muted">
                  Esta ejecución no registró chequeos de calidad.
                </p>
              )}
              <Link
                href="/historial"
                className="mt-4 inline-block text-sm text-accent underline"
              >
                Cerrar detalle
              </Link>
            </div>
          ) : null}

          {runs.items.length === 0 ? (
            <div className="mt-4">
              <EmptyState title="No hay ejecuciones registradas con estos filtros">
                Ejecutá una ingesta desde el CLI autorizado para poblar el
                historial.
              </EmptyState>
            </div>
          ) : (
            <div className="mt-4 overflow-x-auto rounded-lg border border-line bg-white">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-line text-xs uppercase tracking-wide text-muted">
                  <tr>
                    <th className="px-4 py-2 font-semibold">Inicio</th>
                    <th className="px-4 py-2 font-semibold">Tipo</th>
                    <th className="px-4 py-2 font-semibold">Fuente</th>
                    <th className="px-4 py-2 font-semibold">Estado</th>
                    <th className="px-4 py-2 text-right font-semibold">Leídos</th>
                    <th className="px-4 py-2 text-right font-semibold">Aceptados</th>
                    <th className="px-4 py-2 text-right font-semibold">Rechazados</th>
                    <th className="px-4 py-2 text-right font-semibold">Duración</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {runs.items.map((run) => (
                    <tr key={run.id} className="border-b border-line last:border-b-0">
                      <td className="px-4 py-2" title={isoTitle(run.started_at)}>
                        {formatDateTime(run.started_at)}
                      </td>
                      <td className="px-4 py-2">
                        {labelFor(RUN_TYPE_LABELS, run.run_type)}
                      </td>
                      <td className="px-4 py-2">{run.source?.name ?? "—"}</td>
                      <td className="px-4 py-2">
                        <StatusBadge tone={toneForRunStatus(run.status)}>
                          {labelFor(RUN_STATUS_LABELS, run.status)}
                        </StatusBadge>
                      </td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">
                        {formatNumber(run.records_read)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">
                        {formatNumber(run.records_accepted)}
                      </td>
                      <td className="px-4 py-2 text-right font-mono tabular-nums">
                        {formatNumber(run.records_rejected)}
                      </td>
                      <td className="px-4 py-2 text-right">{duration(run)}</td>
                      <td className="px-4 py-2 text-right">
                        <Link
                          href={`/historial?run=${run.id}${source ? `&source=${source}` : ""}`}
                          className="text-accent underline"
                        >
                          Detalle
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Pagination
            page={runs.page}
            pages={runs.pages}
            pageParam="runs_page"
            params={{ source, status, run: runId }}
          />
        </section>

        <section aria-labelledby="cambios">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 id="cambios" className="text-xl font-semibold">
              Cambios detectados
            </h2>
            <form method="get" action="/historial" className="flex flex-wrap items-end gap-2">
              <label className="text-sm text-ink">
                Tipo de cambio
                <select
                  name="change_type"
                  defaultValue={changeType ?? ""}
                  className="mt-1 block rounded-md border border-line bg-white px-2 py-1.5 text-sm"
                >
                  <option value="">Todos</option>
                  {Object.entries(CHANGE_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="submit"
                className="rounded-md bg-accent px-4 py-1.5 text-sm font-semibold text-white hover:bg-accent-deep"
              >
                Filtrar
              </button>
            </form>
          </div>

          {changes.items.length === 0 ? (
            <div className="mt-4">
              <EmptyState title="No hay cambios registrados con estos filtros">
                Los cambios aparecen cuando una sincronización detecta
                diferencias reales respecto de la versión anterior.
              </EmptyState>
            </div>
          ) : (
            <ul className="mt-4 space-y-2" aria-live="polite">
              {changes.items.map((change) => (
                <li
                  key={change.id}
                  className="rounded-lg border border-line bg-white px-4 py-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-medium text-ink">
                      {labelFor(CHANGE_TYPE_LABELS, change.change_type)}
                      {change.dataset ? (
                        <>
                          {" · "}
                          <Link
                            href={`/datasets/${change.dataset.id}`}
                            className="text-accent underline"
                          >
                            {change.dataset.title}
                          </Link>
                        </>
                      ) : null}
                    </p>
                    <span
                      className="text-xs text-muted"
                      title={isoTitle(change.detected_at)}
                    >
                      {formatDateTime(change.detected_at)}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-xs text-muted">
                    {changeSummary(change) || "sin detalle adicional"}
                  </p>
                </li>
              ))}
            </ul>
          )}

          <Pagination
            page={changes.page}
            pages={changes.pages}
            pageParam="changes_page"
            params={{ change_type: changeType }}
          />
        </section>
      </div>
  );
}
