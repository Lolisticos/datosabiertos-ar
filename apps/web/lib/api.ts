// Server-side API client. Every figure on the site is fetched at request
// time (`cache: "no-store"`) so coverage numbers always reflect the live API,
// per the platform rule against fabricated or stale data (S18).
//
// Failures are typed: network unreachable, non-2xx HTTP, or schema mismatch.
// Pages catch `ApiFailure` and render a visible error state instead of
// crashing or inventing content.
import {
  changePageSchema,
  datasetDetailSchema,
  datasetFiltersSchema,
  datasetPageSchema,
  facetsSchema,
  indicatorCoverageSchema,
  indicatorDetailSchema,
  indicatorPageSchema,
  observationPageSchema,
  organizationPageSchema,
  runPageSchema,
  runSchema,
  sourcesSchema,
  statsSchema,
  visualizationSchema,

  type ChangePage,
  type DatasetDetail,
  type DatasetFilters,
  type DatasetPage,
  type Facets,
  type IndicatorCoverage,
  type IndicatorDetail,
  type IndicatorPage,
  type Observation,
  type ObservationPage,
  type OrganizationPage,
  type RunPage,
  type Run,
  type Source,
  type Stats,
  type Visualization,
} from "./schemas";
import type { z } from "zod";

const API_BASE = (
  process.env.DATOSABIERTOS_API_BASE_URL ??
  process.env.NEXT_PUBLIC_API_BASE_URL ??
  "http://localhost:8008"
).replace(/\/$/, "");

export type ApiFailureKind = "network" | "http" | "schema";

export class ApiFailure extends Error {
  constructor(
    public readonly kind: ApiFailureKind,
    message: string,
    public readonly status?: number,
  ) {
    super(message);
    this.name = "ApiFailure";
  }
}

type FetchPolicy =
  | { noStore: true; revalidate?: never; tags?: never }
  | { noStore?: false; revalidate: number; tags?: string[] };

async function fetchJson(
  path: string,
  policy: FetchPolicy = { revalidate: 300, tags: ["catalogue"] },
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(
      `${API_BASE}${path}`,
      policy.noStore
        ? { cache: "no-store" }
        : { next: { revalidate: policy.revalidate, tags: policy.tags } },
    );
  } catch {
    throw new ApiFailure(
      "network",
      `No se pudo conectar con la API (${API_BASE}).`,
    );
  }
  if (!response.ok) {
    throw new ApiFailure(
      "http",
      `La API respondió ${response.status} para ${path}.`,
      response.status,
    );
  }
  try {
    return (await response.json()) as unknown;
  } catch {
    throw new ApiFailure("http", `La API devolvió JSON inválido para ${path}.`);
  }
}

function parseWith<Schema extends z.ZodType>(
  schema: Schema,
  payload: unknown,
  context: string,
): z.infer<Schema> {
  const result = schema.safeParse(payload);
  if (!result.success) {
    const issues = result.error.issues
      .slice(0, 3)
      .map((issue) => `${issue.path.join(".")}: ${issue.message}`)
      .join("; ");
    throw new ApiFailure(
      "schema",
      `La respuesta de ${context} no coincide con el contrato esperado (${issues}).`,
    );
  }
  return result.data;
}

function buildQuery(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const query = search.toString();
  return query ? `?${query}` : "";
}

// --- Getters ---------------------------------------------------------------

export function getStats(): Promise<Stats> {
  return fetchJson("/api/v1/stats/overview").then((payload) =>
    parseWith(statsSchema, payload, "stats/overview"),
  );
}

export function getSources(): Promise<Source[]> {
  return fetchJson("/api/v1/sources").then((payload) =>
    parseWith(sourcesSchema, payload, "sources"),
  );
}

export function getFacets(): Promise<Facets> {
  return fetchJson("/api/v1/facets").then((payload) =>
    parseWith(facetsSchema, payload, "facets"),
  );
}

export function getDatasetFilters(): Promise<DatasetFilters> {
  return fetchJson("/api/v1/datasets/filters").then((payload) =>
    parseWith(datasetFiltersSchema, payload, "datasets/filters"),
  );
}

export interface DatasetSearchParams {
  q?: string;
  source?: string;
  topic?: string;
  format?: string;
  organization_id?: string;
  available_only?: boolean;
  page?: number;
  page_size?: number;
}

export function searchDatasets(
  params: DatasetSearchParams,
): Promise<DatasetPage> {
  const query = buildQuery({
    q: params.q,
    source: params.source,
    topic: params.topic,
    format: params.format,
    organization_id: params.organization_id,
    available_only: params.available_only,
    page: params.page,
    page_size: params.page_size ?? 20,
  });
  return fetchJson(`/api/v1/datasets${query}`).then((payload) =>
    parseWith(datasetPageSchema, payload, "datasets"),
  );
}

export function getDataset(id: string): Promise<DatasetDetail> {
  return fetchJson(`/api/v1/datasets/${id}`).then((payload) =>
    parseWith(datasetDetailSchema, payload, `datasets/${id}`),
  );
}

export function getVisualization(id: string): Promise<Visualization> {
  return fetchJson(`/api/v1/datasets/${id}/visualization`).then((payload) =>
    parseWith(visualizationSchema, payload, `datasets/${id}/visualization`),
  );
}

export interface RunSearchParams {
  source?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

export function getRuns(params: RunSearchParams): Promise<RunPage> {
  const query = buildQuery({
    source: params.source,
    status: params.status,
    page: params.page,
    page_size: params.page_size ?? 10,
  });
  return fetchJson(`/api/v1/ingestion-runs${query}`, { noStore: true }).then((payload) =>
    parseWith(runPageSchema, payload, "ingestion-runs"),
  );
}

export function getRun(id: string): Promise<Run> {
  return fetchJson(`/api/v1/ingestion-runs/${id}`, { noStore: true }).then((payload) =>
    parseWith(runSchema, payload, `ingestion-runs/${id}`),
  );
}

export interface ChangeSearchParams {
  change_type?: string;
  dataset_id?: string;
  page?: number;
  page_size?: number;
}

export function getChanges(params: ChangeSearchParams): Promise<ChangePage> {
  const query = buildQuery({
    change_type: params.change_type,
    dataset_id: params.dataset_id,
    page: params.page,
    page_size: params.page_size ?? 10,
  });
  return fetchJson(`/api/v1/changes${query}`, { noStore: true }).then((payload) =>
    parseWith(changePageSchema, payload, "changes"),
  );
}

export type OrganizationOption = { id: string; name: string };

function getOrganizations(page: number): Promise<OrganizationPage> {
  return fetchJson(`/api/v1/organizations?page=${page}&page_size=100`).then(
    (payload) => parseWith(organizationPageSchema, payload, "organizations"),
  );
}

// Fetches the compact organization dimension, never the full dataset catalogue.
export async function getOrganizationOptions(): Promise<OrganizationOption[]> {
  const first = await getOrganizations(1);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, first.pages - 1) }, (_, index) =>
      getOrganizations(index + 2),
    ),
  );
  return [first, ...rest]
    .flatMap((page) => page.items)
    .map(({ id, name }) => ({ id, name }));
}

const INDICATOR_CACHE: FetchPolicy = { revalidate: 3600, tags: ["indicators"] };

export function getIndicators(page = 1): Promise<IndicatorPage> {
  return fetchJson(`/api/v1/indicators?page=${page}&page_size=100`, INDICATOR_CACHE).then(
    (payload) => parseWith(indicatorPageSchema, payload, "indicators"),
  );
}

export function getIndicator(code: string): Promise<IndicatorDetail> {
  return fetchJson(`/api/v1/indicators/${encodeURIComponent(code)}`, INDICATOR_CACHE).then(
    (payload) => parseWith(indicatorDetailSchema, payload, `indicators/${code}`),
  );
}

export function getIndicatorCoverage(code: string): Promise<IndicatorCoverage> {
  return fetchJson(
    `/api/v1/indicators/${encodeURIComponent(code)}/coverage`,
    INDICATOR_CACHE,
  ).then((payload) =>
    parseWith(indicatorCoverageSchema, payload, `indicators/${code}/coverage`),
  );
}

function getObservationPage(code: string, page: number): Promise<ObservationPage> {
  return fetchJson(
    `/api/v1/indicators/${encodeURIComponent(code)}/observations?page=${page}&page_size=100`,
    INDICATOR_CACHE,
  ).then((payload) =>
    parseWith(observationPageSchema, payload, `indicators/${code}/observations`),
  );
}

export async function getAllIndicatorObservations(code: string): Promise<Observation[]> {
  const first = await getObservationPage(code, 1);
  const rest = await Promise.all(
    Array.from({ length: Math.max(0, first.pages - 1) }, (_, index) =>
      getObservationPage(code, index + 2),
    ),
  );
  return [first, ...rest].flatMap((page) => page.items);
}

export function indicatorCsvUrl(code: string): string {
  return `${API_BASE}/api/v1/indicators/${encodeURIComponent(code)}/observations.csv`;
}

export const apiBase = API_BASE;
