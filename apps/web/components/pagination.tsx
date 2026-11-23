import Link from "next/link";
import { formatNumber } from "@/lib/format";

// Server-rendered pagination: plain links carrying the full query string, so
// every page of results is shareable and keyboard-navigable.
export function Pagination({
  page,
  pages,
  params,
  pageParam = "page",
}: {
  page: number;
  pages: number;
  params: Record<string, string | undefined>;
  pageParam?: string;
}) {
  if (pages <= 1) return null;

  function pageHref(target: number): string {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") search.set(key, value);
    }
    search.set(pageParam, String(target));
    return `?${search.toString()}`;
  }

  const windowStart = Math.max(1, Math.min(page - 2, pages - 4));
  const windowPages = Array.from(
    { length: Math.min(5, pages) },
    (_, index) => windowStart + index,
  );

  const linkClass =
    "rounded-md border border-line bg-white px-3 py-1.5 text-sm text-ink hover:border-accent";
  const currentClass =
    "rounded-md border border-accent bg-accent px-3 py-1.5 text-sm font-semibold text-white";

  return (
    <nav aria-label="Paginación de resultados" className="mt-6">
      <ul className="flex flex-wrap items-center gap-2">
        {page > 1 ? (
          <li>
            <Link className={linkClass} href={pageHref(page - 1)}>
              ← Anterior
            </Link>
          </li>
        ) : null}
        {windowPages.map((target) => (
          <li key={target}>
            {target === page ? (
              <span aria-current="page" className={currentClass}>
                {formatNumber(target)}
              </span>
            ) : (
              <Link className={linkClass} href={pageHref(target)}>
                {formatNumber(target)}
              </Link>
            )}
          </li>
        ))}
        {page < pages ? (
          <li>
            <Link className={linkClass} href={pageHref(page + 1)}>
              Siguiente →
            </Link>
          </li>
        ) : null}
      </ul>
      <p className="mt-2 text-xs text-muted">
        Página {formatNumber(page)} de {formatNumber(pages)}
      </p>
    </nav>
  );
}
