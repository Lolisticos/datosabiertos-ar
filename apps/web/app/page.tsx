import Link from "next/link";
import { ApiFailure, getFacets, getSources, getStats } from "@/lib/api";
import type { Facets, Source, Stats } from "@/lib/schemas";
import { formatDateTime, formatNumber, isoTitle } from "@/lib/format";
import { SOURCE_TYPE_LABELS, labelFor } from "@/lib/labels";
import { ApiErrorState } from "@/components/api-error-state";
import { Figure } from "@/components/figure";
import { StatusBadge, toneForRunStatus } from "@/components/status-badge";

export const metadata = { title: "Inicio" };

export default async function HomePage() {
  let stats: Stats;
  let facets: Facets;
  let sources: Source[];
  try {
    [stats, facets, sources] = await Promise.all([
      getStats(),
      getFacets(),
      getSources(),
    ]);
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }
  const lastSync =
    stats.last_successful_run?.finished_at ??
    stats.last_run?.finished_at ??
    stats.latest_source_update;

  return (
    <div className="space-y-10">
      <section aria-labelledby="que-consultar">
        <h1 id="que-consultar" className="text-3xl font-bold tracking-tight">
          Datos públicos de Argentina, con procedencia verificable
        </h1>
        <p className="mt-3 max-w-3xl text-muted">
          Acá podés consultar el catálogo normalizado de fuentes oficiales:
          qué datasets publica cada organismo, con qué licencia, en qué
          formatos, cuándo se sincronizó por última vez y qué validaciones
          superó. Todo es rastreable hasta el artefacto original descargado.
        </p>

        <form
          action="/datasets"
          method="get"
          className="mt-6 flex max-w-2xl flex-col gap-2 sm:flex-row"
          role="search"
        >
          <label htmlFor="busqueda" className="sr-only">
            Buscar datasets por tema, territorio u organismo
          </label>
          <input
            id="busqueda"
            name="q"
            type="search"
            placeholder="Buscar por tema, territorio u organismo…"
            className="w-full flex-1 rounded-md border border-line bg-white px-4 py-2.5 text-ink"
          />
          <button
            type="submit"
            className="rounded-md bg-accent px-5 py-2.5 font-semibold text-white hover:bg-accent-deep"
          >
            Buscar datasets
          </button>
        </form>

        <nav aria-label="Temáticas del catálogo" className="mt-4">
          <ul className="flex flex-wrap gap-2">
            {facets.topics.map((topic) => (
              <li key={topic.value}>
                <Link
                  href={`/datasets?topic=${encodeURIComponent(topic.value)}`}
                  className="rounded-full border border-line bg-white px-3 py-1 text-sm text-ink hover:border-accent hover:text-accent-deep"
                >
                  {topic.value}{" "}
                  <span className="font-mono text-xs text-muted">
                    ({topic.count})
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </section>

      <section aria-labelledby="cobertura">
        <h2 id="cobertura" className="text-xl font-semibold">
          Cobertura actual del catálogo
        </h2>
        <p className="mt-1 text-sm text-muted">
          Cifras obtenidas de la API en el momento de esta consulta; alcance:
          catálogo completo sincronizado.
        </p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          <Figure
            value={stats.datasets}
            label="Datasets catalogados"
            note={`${stats.datasets_available} disponibles`}
          />
          <Figure value={stats.resources} label="Recursos (archivos/enlaces)" />
          <Figure value={stats.organizations} label="Organismos publicantes" />
          <Figure value={stats.sources} label="Fuentes oficiales activas" />
          <Figure value={stats.topics} label="Temáticas" />
          <Figure
            value={stats.raw_snapshots}
            label="Snapshots RAW preservados"
            note="artefactos originales"
          />
          <Figure
            value={stats.changes_last_7_days}
            label="Cambios detectados"
            note="últimos 7 días, todo el catálogo"
          />
          <div className="rounded-lg border border-line bg-white p-4">
            <p
              className="font-mono text-lg font-semibold text-ink"
              title={isoTitle(lastSync)}
            >
              {formatDateTime(lastSync)}
            </p>
            <p className="mt-1 text-sm font-medium text-ink">
              Última sincronización exitosa
            </p>
            <p className="text-xs text-muted">
              hora de Argentina; alcance: todas las fuentes
            </p>
          </div>
        </div>
      </section>

      <section aria-labelledby="fuentes-strip">
        <div className="flex items-baseline justify-between gap-4">
          <h2 id="fuentes-strip" className="text-xl font-semibold">
            Fuentes oficiales
          </h2>
          <Link
            href="/fuentes"
            className="text-sm font-semibold text-accent underline"
          >
            Ver detalle de fuentes
          </Link>
        </div>
        <ul className="mt-4 grid gap-3 sm:grid-cols-2">
          {sources.map((source) => (
            <li
              key={source.id}
              className="rounded-lg border border-line bg-white p-4"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-ink">{source.name}</p>
                  <p className="text-xs text-muted">
                    Tipo de acceso:{" "}
                    {labelFor(SOURCE_TYPE_LABELS, source.source_type)} ·{" "}
                    <a
                      href={source.base_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent underline"
                    >
                      {source.base_url}
                    </a>
                  </p>
                </div>
                <StatusBadge tone={toneForRunStatus(source.last_run_status ?? "")}>
                  {source.last_run_status
                    ? `último estado: ${source.last_run_status}`
                    : "sin ejecuciones"}
                </StatusBadge>
              </div>
              <p className="mt-2 font-mono text-sm tabular-nums text-ink">
                {formatNumber(source.dataset_count)} datasets
              </p>
            </li>
          ))}
        </ul>
      </section>

      <section
        aria-labelledby="frescura"
        className="rounded-lg border border-accent/30 bg-accent-soft p-5"
      >
        <h2 id="frescura" className="text-lg font-semibold text-accent-deep">
          Frescura y cobertura de los datos
        </h2>
        <p className="mt-2 text-sm text-ink">{stats.coverage_note}</p>
        <p className="mt-2 text-sm text-ink">
          Última actualización declarada por una fuente:{" "}
          <span title={isoTitle(stats.latest_source_update)}>
            {formatDateTime(stats.latest_source_update)}
          </span>
          . Última sincronización exitosa:{" "}
          <span title={isoTitle(lastSync)}>{formatDateTime(lastSync)}</span>.
        </p>
      </section>
    </div>
  );
}
