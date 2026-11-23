import Link from "next/link";

export default function NotFound() {
  return (
    <div role="alert" className="rounded-lg border border-line bg-white p-8">
      <h1 className="text-xl font-semibold text-ink">
        404 — La página no existe
      </h1>
      <p className="mt-2 text-sm text-muted">
        La dirección solicitada no corresponde a ninguna sección de
        DatosAbiertos AR.
      </p>
      <p className="mt-4 text-sm">
        <Link href="/" className="font-semibold text-accent underline">
          Volver al inicio
        </Link>
      </p>
    </div>
  );
}
