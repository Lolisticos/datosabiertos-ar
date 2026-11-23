import Link from "next/link";
import type { DatasetListItem } from "@/lib/schemas";
import { formatDateTime, formatNumber, isoTitle } from "@/lib/format";
import { StatusBadge } from "@/components/status-badge";

// One catalogue result. Every metadata line is traceable: publisher, source
// catalogue, formats and the exact last sync instant (ISO in the tooltip).
export function DatasetCard({ dataset }: { dataset: DatasetListItem }) {
  const coverage =
    dataset.coverage.start || dataset.coverage.end
      ? `${dataset.coverage.start ?? "sin inicio"} → ${dataset.coverage.end ?? "sin fin"}`
      : null;

  return (
    <li className="rounded-lg border border-line bg-white p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-lg font-semibold text-ink">
            <Link
              href={`/datasets/${dataset.id}`}
              className="hover:text-accent-deep hover:underline"
            >
              {dataset.title}
            </Link>
          </h2>
          <p className="text-xs text-muted">
            {dataset.organization?.name ?? "Organismo no declarado"} ·{" "}
            {dataset.source.name}
          </p>
        </div>
        <StatusBadge tone={dataset.is_available ? "ok" : "neutral"}>
          {dataset.is_available ? "disponible" : "no disponible"}
        </StatusBadge>
      </div>

      {dataset.description ? (
        <p className="mt-2 line-clamp-3 text-sm text-muted">
          {dataset.description}
        </p>
      ) : null}

      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted">
        {dataset.topic ? (
          <div className="flex gap-1">
            <dt className="font-medium">Tema:</dt>
            <dd>{dataset.topic}</dd>
          </div>
        ) : null}
        <div className="flex gap-1">
          <dt className="font-medium">Recursos:</dt>
          <dd className="font-mono tabular-nums">
            {formatNumber(dataset.resource_count)}
          </dd>
        </div>
        <div className="flex gap-1">
          <dt className="font-medium">Formatos:</dt>
          <dd>{dataset.formats.join(", ") || "sin formato declarado"}</dd>
        </div>
        {coverage ? (
          <div className="flex gap-1">
            <dt className="font-medium">Cobertura:</dt>
            <dd>{coverage}</dd>
          </div>
        ) : null}
        {dataset.license ? (
          <div className="flex gap-1">
            <dt className="font-medium">Licencia:</dt>
            <dd>{dataset.license}</dd>
          </div>
        ) : null}
      </dl>

      <p className="mt-3 border-t border-line pt-2 text-xs text-muted">
        Última sincronización:{" "}
        <span title={isoTitle(dataset.last_successful_sync)}>
          {formatDateTime(dataset.last_successful_sync)}
        </span>
      </p>
    </li>
  );
}
