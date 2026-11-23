import Link from "next/link";

const NAV_ITEMS = [
  { href: "/fuentes", label: "Fuentes" },
  { href: "/datasets", label: "Datasets" },
  { href: "/historial", label: "Historial" },
];

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2">
          <span
            aria-hidden="true"
            className="flex h-8 w-8 items-end justify-center gap-0.5 rounded-md bg-accent pb-1.5"
          >
            <span className="h-2 w-1 rounded-sm bg-white/90" />
            <span className="h-3.5 w-1 rounded-sm bg-white/90" />
            <span className="h-5 w-1 rounded-sm bg-white/90" />
          </span>
          <span className="text-lg font-bold tracking-tight text-ink">
            DatosAbiertos <span className="text-accent">AR</span>
          </span>
        </Link>
        <nav aria-label="Navegación principal">
          <ul className="flex flex-wrap items-center gap-x-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-ink hover:bg-paper hover:text-accent-deep"
                >
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </header>
  );
}
