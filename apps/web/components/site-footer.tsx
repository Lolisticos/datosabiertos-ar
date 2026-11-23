import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="mt-12 border-t border-line bg-white">
      <div className="mx-auto grid max-w-7xl gap-5 px-4 py-8 text-sm text-muted sm:px-6 md:grid-cols-[1fr_auto] lg:px-8">
        <div>
          <p className="font-semibold text-ink">DatosAbiertos AR</p>
          <p className="mt-1 max-w-3xl">
            Datos públicos oficiales con metodología, fecha de actualización y
            trazabilidad hasta el recurso original. Las ausencias nunca se
            presentan como cero.
          </p>
        </div>
        <nav aria-label="Enlaces del pie">
          <ul className="flex flex-wrap gap-x-4 gap-y-2">
            <li><Link className="underline hover:text-accent-deep" href="/fuentes">Fuentes</Link></li>
            <li><Link className="underline hover:text-accent-deep" href="/datasets">Catálogo</Link></li>
            <li><Link className="underline hover:text-accent-deep" href="/acerca">Metodología</Link></li>
          </ul>
        </nav>
      </div>
    </footer>
  );
}
