"use client";

// Global error boundary: an unexpected render failure surfaces as a visible
// state with a retry, never a blank screen.
export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div role="alert" className="rounded-lg border border-danger/40 bg-danger/5 p-8">
      <h1 className="text-xl font-semibold text-danger">
        Ocurrió un error al renderizar esta página
      </h1>
      <p className="mt-2 text-sm text-ink">
        No se muestran datos porque el contenido no pudo construirse.{" "}
        {error.digest ? (
          <span className="text-muted">Referencia: {error.digest}.</span>
        ) : null}
      </p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-deep"
      >
        Reintentar
      </button>
    </div>
  );
}
