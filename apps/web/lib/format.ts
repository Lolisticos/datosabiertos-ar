// Formatting helpers. UI copy is es-AR; dates render in Argentina time with
// the instant kept in a `title` attribute (ISO 8601) for exactness.

const dateTimeFormatter = new Intl.DateTimeFormat("es-AR", {
  dateStyle: "medium",
  timeStyle: "short",
  timeZone: "America/Argentina/Buenos_Aires",
});

const dateFormatter = new Intl.DateTimeFormat("es-AR", {
  dateStyle: "medium",
  timeZone: "UTC", // date-only values (coverage) carry no time component
});

const numberFormatter = new Intl.NumberFormat("es-AR");

/** "23 nov 2026, 16:29" for an ISO instant; null-safe. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "Sin registro";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return dateTimeFormatter.format(date);
}

/** "27 abr 2023" for an ISO date (YYYY-MM-DD) or instant; null-safe. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "Sin registro";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return dateFormatter.format(date);
}

/** "1.293" (es-AR thousands separator). */
export function formatNumber(value: number): string {
  return numberFormatter.format(value);
}

/** Exact ISO instant for `title` tooltips. */
export function isoTitle(iso: string | null | undefined): string | undefined {
  return iso ?? undefined;
}
