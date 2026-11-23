import Link from "next/link";
import {
  ApiFailure,
  getDatasetFilters,
  getOrganizationOptions,
  searchDatasets,
  type DatasetSearchParams,
} from "@/lib/api";
import { formatNumber } from "@/lib/format";
import { ApiErrorState } from "@/components/api-error-state";
import { DatasetCard } from "@/components/dataset-card";
import { EmptyState } from "@/components/empty-state";
import { Pagination } from "@/components/pagination";

export const metadata = { title: "Explorador de datasets" };

type SearchParams = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

function positiveInt(value: string | undefined, fallback: number): number {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

export default async function DatasetsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const raw = await searchParams;
  const q = first(raw.q)?.trim() || undefined;
  const source = first(raw.source) || undefined;
  const topic = first(raw.topic) || undefined;
  const format = first(raw.format) || undefined;
  const organizationId = first(raw.organization_id) || undefined;
  const availableOnly = first(raw.available_only) !== "false";
  const page = positiveInt(first(raw.page), 1);

  const params: DatasetSearchParams = {
    q,
    source,
    topic,
    format,
    organization_id: organizationId,
    available_only: availableOnly,
    page,
    page_size: 20,
  };

  let filters;
  let results;
  let organizations;
  try {
    [filters, organizations, results] = await Promise.all([
      getDatasetFilters(),
      getOrganizationOptions(),
      searchDatasets(params),
    ]);
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }

  const activeFilters = [q, source, topic, format, organizationId].filter(Boolean).length;

  return (
    <div className="space-y-6">
      <section aria-labelledby="explorador-titulo">
        <h1 id="explorador-titulo" className="text-2xl font-bold tracking-tight">
          Explorador de datasets
        </h1>
        <p className="mt-2 max-w-3xl text-muted">
          Búsqueda sobre el catálogo normalizado, servida por PostgreSQL. Los
          filtros y los conteos provienen de los datos sincronizados, no de
          valores estimados.
        </p>
      </section>

      <form
        method="get"
        action="/datasets"
        className="rounded-lg border border-line bg-white p-4"
        role="search"
      >
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="sm:col-span-2 lg:col-span-5">
            <label htmlFor="q" className="text-sm font-medium text-ink">
              Buscar por tema, territorio u organismo
            </label>
            <input
              id="q"
              name="q"
              type="search"
              defaultValue={q ?? ""}
              placeholder="Ej.: producción minera, educación, CABA…"
              className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 text-ink"
            />
          </div>

          <div>
            <label htmlFor="organization_id" className="text-sm font-medium text-ink">
              Organismo
            </label>
            <select
              id="organization_id"
              name="organization_id"
              defaultValue={organizationId ?? ""}
              className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 text-ink"
            >
              <option value="">Todos los organismos</option>
              {organizations.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="source" className="text-sm font-medium text-ink">
              Fuente
            </label>
            <select
              id="source"
              name="source"
              defaultValue={source ?? ""}
              className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 text-ink"
            >
              <option value="">Todas las fuentes</option>
              {filters.sources.map((item) => (
                <option key={item.id} value={item.slug}>
                  {item.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="topic" className="text-sm font-medium text-ink">
              Tema
            </label>
            <select
              id="topic"
              name="topic"
              defaultValue={topic ?? ""}
              className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 text-ink"
            >
              <option value="">Todos los temas</option>
              {filters.topics.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="format" className="text-sm font-medium text-ink">
              Formato
            </label>
            <select
              id="format"
              name="format"
              defaultValue={format ?? ""}
              className="mt-1 w-full rounded-md border border-line bg-paper px-3 py-2 text-ink"
            >
              <option value="">Todos los formatos</option>
              {filters.formats.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end gap-3">
            <label className="flex items-center gap-2 text-sm text-ink">
              <input
                type="checkbox"
                name="available_only"
                value="true"
                defaultChecked={availableOnly}
                className="h-4 w-4"
              />
              Solo disponibles
            </label>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            type="submit"
            className="rounded-md bg-accent px-5 py-2 font-semibold text-white hover:bg-accent-deep"
          >
            Aplicar filtros
          </button>
          {activeFilters > 0 ? (
            <Link href="/datasets" className="text-sm text-accent underline">
              Limpiar filtros
            </Link>
          ) : null}
        </div>
      </form>

      <p className="text-sm text-muted" role="status">
        {formatNumber(results.total)} datasets encontrados
        {q ? (
          <>
            {" "}
            para <span className="font-medium text-ink">“{q}”</span>
          </>
        ) : null}
        . Página {formatNumber(results.page)} de{" "}
        {formatNumber(Math.max(results.pages, 1))}.
      </p>

      {results.items.length === 0 ? (
        <EmptyState title="No hay datasets que coincidan con estos filtros">
          Probá con otro término o quitá algún filtro. Si la búsqueda no
          devuelve nada, es porque el catálogo sincronizado no contiene esos
          datos: no completamos resultados con información inventada.
        </EmptyState>
      ) : (
        <ul className="space-y-4">
          {results.items.map((dataset) => (
            <DatasetCard key={dataset.id} dataset={dataset} />
          ))}
        </ul>
      )}

      <Pagination
        page={results.page}
        pages={results.pages}
        params={{
          q,
          source,
          topic,
          format,
          organization_id: organizationId,
          available_only: availableOnly ? undefined : "false",
        }}
      />
    </div>
  );
}
