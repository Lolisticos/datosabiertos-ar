// Spanish (es-AR) labels for API enums. Keys come from the API contract
// (OpenAPI ChangeType / IngestionRunStatus enums); unknown values render
// verbatim so nothing is silently hidden.

export const CHANGE_TYPE_LABELS: Record<string, string> = {
  dataset_added: "Dataset incorporado",
  dataset_removed: "Dataset retirado del catálogo",
  resource_added: "Recurso agregado",
  resource_removed: "Recurso eliminado",
  content_changed: "Contenido modificado",
  schema_changed: "Esquema modificado",
  metadata_changed: "Metadatos modificados",
  fetch_failed: "Fallo de descarga",
  recovered: "Recuperado",
};

export const RUN_STATUS_LABELS: Record<string, string> = {
  running: "En curso",
  succeeded: "Exitosa",
  partial: "Parcial",
  failed: "Fallida",
};

export const CHECK_STATUS_LABELS: Record<string, string> = {
  passed: "Aprobada",
  failed: "No aprobada",
  warning: "Advertencia",
};

export const RUN_TYPE_LABELS: Record<string, string> = {
  catalog_discovery: "Descubrimiento de catálogo",
  metadata_sync: "Sincronización de metadatos",
  resource_fetch: "Descarga de recursos",
};

export const SOURCE_TYPE_LABELS: Record<string, string> = {
  ckan: "API CKAN",
  http: "HTTP",
  file: "Archivo",
};

export function labelFor(labels: Record<string, string>, key: string): string {
  return labels[key] ?? key;
}

/** All known change types, for filter dropdowns driven by the API enum. */
export const CHANGE_TYPES = Object.keys(CHANGE_TYPE_LABELS);

/** All known ingestion run statuses, for filter dropdowns. */
export const RUN_STATUSES = Object.keys(RUN_STATUS_LABELS);
