import type { ApiFailure } from "@/lib/api";

// Visible degradation for API failures: network down, non-2xx, or a payload
// that no longer matches the zod contract. Never fakes content.
export function ApiErrorState({ error }: { error: ApiFailure }) {
  const title =
    error.kind === "network"
      ? "La API no está disponible"
      : error.kind === "schema"
        ? "La respuesta de la API cambió de formato"
        : "La API devolvió un error";
  return (
    <div
      role="alert"
      className="rounded-lg border border-danger/40 bg-danger/5 p-6"
    >
      <h2 className="text-lg font-semibold text-danger">{title}</h2>
      <p className="mt-2 text-sm text-ink">{error.message}</p>
      <p className="mt-3 text-sm text-muted">
        No se muestran datos porque no pudimos verificarlos contra la fuente
        oficial. Reintentá en unos segundos.
      </p>
    </div>
  );
}
