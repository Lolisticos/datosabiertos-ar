// Runtime validation for every API payload. Schemas mirror the OpenAPI
// contract of the DatosAbiertos AR API (GET /openapi.json). Unknown fields
// are stripped (zod default) so additive API changes stay compatible; a
// structural mismatch throws and degrades to a visible error state.
import { z } from "zod";

const nullableString = z.string().nullable();

export const referencedSourceSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  source_type: z.string(),
  base_url: z.string(),
});

export const referencedOrganizationSchema = z.object({
  id: z.string(),
  name: z.string(),
  acronym: nullableString,
  official_url: nullableString,
});

export const dateRangeSchema = z.object({
  start: nullableString.optional(),
  end: nullableString.optional(),
});

export const datasetListItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: nullableString,
  topic: nullableString,
  license: nullableString,
  organization: referencedOrganizationSchema.nullable(),
  source: referencedSourceSchema,
  formats: z.array(z.string()),
  resource_count: z.number(),
  coverage: dateRangeSchema,
  last_source_update: nullableString,
  last_successful_sync: nullableString,
  is_available: z.boolean(),
  landing_url: nullableString,
});

function pageSchema<Item extends z.ZodType>(itemSchema: Item) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    pages: z.number(),
  });
}

export const resourceSchema = z.object({
  id: z.string(),
  external_id: z.string(),
  name: nullableString,
  format: nullableString,
  url: z.string(),
  mime_type: nullableString,
  file_size: z.number().nullable(),
  checksum: nullableString,
  last_modified: nullableString,
  is_available: z.boolean(),
});

export const qualityCheckSchema = z.object({
  id: z.string(),
  check_type: z.string(),
  status: z.string(),
  details: z.record(z.string(), z.unknown()),
  checked_at: z.string(),
});

export const referencedDatasetSchema = z.object({
  id: z.string(),
  title: z.string(),
});

export const referencedResourceSchema = z.object({
  id: z.string(),
  format: nullableString.optional(),
});

export const changeSchema = z.object({
  id: z.string(),
  change_type: z.string(),
  detected_at: z.string(),
  dataset: referencedDatasetSchema.nullable().optional(),
  resource: referencedResourceSchema.nullable().optional(),
  change_summary: z.record(z.string(), z.unknown()),
});

export const changeListItemSchema = changeSchema.extend({
  source_slug: nullableString.optional(),
});

export const runSchema = z.object({
  id: z.string(),
  source: referencedSourceSchema.nullable(),
  run_type: z.string(),
  status: z.string(),
  triggered_by: z.string(),
  transformation_version: nullableString,
  started_at: z.string(),
  finished_at: nullableString,
  records_read: z.number(),
  records_accepted: z.number(),
  records_rejected: z.number(),
  error_summary: nullableString,
  quality_checks: z.array(qualityCheckSchema),
});

export const provenanceSchema = z.object({
  raw_snapshot_count: z.number(),
  last_snapshot_at: nullableString,
  source_landing_url: nullableString,
  dataset_landing_url: nullableString,
});

export const datasetDetailSchema = datasetListItemSchema.extend({
  raw_metadata: z.record(z.string(), z.unknown()).nullable(),
  resources: z.array(resourceSchema),
  quality_checks: z.array(qualityCheckSchema),
  changes: z.array(changeSchema),
  provenance: provenanceSchema,
  latest_run: runSchema.nullable(),
});

export const sourceSchema = z.object({
  id: z.string(),
  slug: z.string(),
  name: z.string(),
  base_url: z.string(),
  source_type: z.string(),
  license: nullableString,
  notes: nullableString,
  is_active: z.boolean(),
  organization: referencedOrganizationSchema.nullable(),
  dataset_count: z.number(),
  last_successful_run_at: nullableString,
  last_run_status: nullableString,
});

export const sourcesSchema = z.array(sourceSchema);

export const statsSchema = z.object({
  datasets: z.number(),
  datasets_available: z.number(),
  resources: z.number(),
  sources: z.number(),
  organizations: z.number(),
  topics: z.number(),
  raw_snapshots: z.number(),
  changes_last_7_days: z.number(),
  latest_source_update: nullableString,
  last_run: runSchema.nullable(),
  last_successful_run: runSchema.nullable(),
  coverage_note: z.string(),
});

export const facetSchema = z.object({
  value: z.string(),
  count: z.number(),
});

export const facetsSchema = z.object({
  topics: z.array(facetSchema),
  formats: z.array(facetSchema),
  organizations: z.array(facetSchema),
});

export const datasetFiltersSchema = z.object({
  topics: z.array(z.string()),
  formats: z.array(z.string()),
  sources: z.array(referencedSourceSchema),
});

export const visualizationSchema = z.object({
  available: z.boolean(),
  visualizations: z.array(z.string()),
  reason: z.string(),
  dataset_id: z.string(),
});

export const datasetPageSchema = pageSchema(datasetListItemSchema);
export const runPageSchema = pageSchema(runSchema);
export const changePageSchema = pageSchema(changeListItemSchema);

export type ReferencedSource = z.infer<typeof referencedSourceSchema>;
export type ReferencedOrganization = z.infer<typeof referencedOrganizationSchema>;
export type DatasetListItem = z.infer<typeof datasetListItemSchema>;
export type DatasetDetail = z.infer<typeof datasetDetailSchema>;
export type DatasetPage = z.infer<typeof datasetPageSchema>;
export type Resource = z.infer<typeof resourceSchema>;
export type QualityCheck = z.infer<typeof qualityCheckSchema>;
export type Change = z.infer<typeof changeSchema>;
export type ChangeListItem = z.infer<typeof changeListItemSchema>;
export type ChangePage = z.infer<typeof changePageSchema>;
export type Run = z.infer<typeof runSchema>;
export type RunPage = z.infer<typeof runPageSchema>;
export type Source = z.infer<typeof sourceSchema>;
export type Stats = z.infer<typeof statsSchema>;
export type Facet = z.infer<typeof facetSchema>;
export type Facets = z.infer<typeof facetsSchema>;
export type DatasetFilters = z.infer<typeof datasetFiltersSchema>;
export type Visualization = z.infer<typeof visualizationSchema>;
