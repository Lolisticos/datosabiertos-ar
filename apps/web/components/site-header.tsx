"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Inicio" },
  { href: "/indicadores", label: "Indicadores" },
  { href: "/datasets", label: "Datos y fuentes" },
  { href: "/historial", label: "Actualizaciones" },
  { href: "/acerca", label: "Acerca" },
];

export function SiteHeader() {
  const pathname = usePathname();
  return (
    <header className="border-b border-line bg-white">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-8 gap-y-2 px-4 py-3 sm:px-6 lg:px-8">
        <Link href="/" className="flex min-h-11 items-center gap-2" aria-label="DatosAbiertos AR, inicio">
          <span
            aria-hidden="true"
            className="flex h-9 w-9 items-end justify-center gap-0.5 rounded-md bg-accent pb-2"
          >
            <span className="h-2 w-1 rounded-sm bg-white/90" />
            <span className="h-3.5 w-1 rounded-sm bg-white/90" />
            <span className="h-5 w-1 rounded-sm bg-white/90" />
          </span>
          <span className="text-[1.05rem] font-semibold tracking-tight text-ink">
            DatosAbiertos <span className="text-accent">AR</span>
          </span>
        </Link>
        <nav aria-label="Navegación principal" className="order-3 w-full overflow-x-auto md:order-none md:w-auto">
          <ul className="flex min-w-max items-center gap-x-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={
                    item.href === "/"
                      ? pathname === "/" ? "page" : undefined
                      : pathname.startsWith(item.href) ? "page" : undefined
                  }
                  className="flex min-h-10 items-center rounded-md px-3 text-sm font-medium text-muted hover:bg-paper hover:text-accent-deep aria-[current=page]:bg-accent-soft aria-[current=page]:text-accent-deep"
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
