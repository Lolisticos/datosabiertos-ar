import Link from "next/link";
import { ApiErrorState } from "@/components/api-error-state";
import { FreshnessBadge } from "@/components/data/freshness-badge";
import { ApiFailure, getIndicators, getStats } from "@/lib/api";
import { formatDateTime, formatNumber } from "@/lib/format";

export const metadata = { title: "Inicio" };

const valueFormatter = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });

export default async function HomePage() {
  let stats;
  let indicators;
  try {
    [stats, indicators] = await Promise.all([getStats(), getIndicators()]);
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }
  const published = indicators.items.filter((indicator) => indicator.latest_value !== null);
  const emae = published.find((indicator) => indicator.code === "emae-original-2004");

  return (
    <div className="space-y-14">
      <section className="grid items-center gap-8 py-4 lg:grid-cols-[1.1fr_0.9fr]" aria-labelledby="inicio-titulo">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent">Datos públicos de Argentina</p>
          <h1 id="inicio-titulo" className="mt-3 max-w-4xl text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl">Información oficial, clara y verificable</h1>
          <p className="mt-4 max-w-2xl text-lg leading-8 text-muted">Explorá indicadores, series históricas y fuentes públicas con contexto metodológico y trazabilidad hasta el recurso original.</p>
          <form action="/datasets" method="get" className="mt-7 flex max-w-2xl flex-col gap-2 sm:flex-row" role="search">
            <label htmlFor="busqueda" className="sr-only">Buscar datos por tema, territorio u organismo</label>
            <input id="busqueda" name="q" type="search" placeholder="Buscar datos, organismos o temas…" className="min-h-12 w-full flex-1 rounded-md border border-line bg-white px-4 text-ink shadow-sm" />
            <button type="submit" className="min-h-12 rounded-md bg-accent px-6 font-semibold text-white hover:bg-accent-deep">Buscar</button>
          </form>
        </div>
        <aside className="rounded-xl border border-accent/20 bg-white p-6 shadow-sm" aria-label="Compromiso de transparencia">
          <p className="text-sm font-semibold text-accent-deep">Qué vas a encontrar</p>
          <ul className="mt-4 space-y-3 text-sm text-ink">
            <li className="flex gap-3"><span aria-hidden="true" className="text-success">✓</span> Series oficiales sin valores inventados</li>
            <li className="flex gap-3"><span aria-hidden="true" className="text-success">✓</span> Fechas, unidades y metodología visibles</li>
            <li className="flex gap-3"><span aria-hidden="true" className="text-success">✓</span> Descargas y API para reutilización</li>
            <li className="flex gap-3"><span aria-hidden="true" className="text-success">✓</span> Historial de cambios y archivos RAW preservados</li>
          </ul>
        </aside>
      </section>

      <section aria-labelledby="tematicas-titulo">
        <div className="flex items-end justify-between gap-4">
          <div><p className="text-sm font-medium text-muted">Explorar</p><h2 id="tematicas-titulo" className="mt-1 text-2xl font-semibold">Por temática</h2></div>
          <Link href="/indicadores" className="text-sm font-semibold text-accent underline">Ver indicadores</Link>
        </div>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {emae ? (
            <Link href="/temas/economia/actividad" className="group rounded-lg border border-line bg-white p-5 hover:border-economy">
              <span className="inline-flex rounded-full bg-economy-soft px-2.5 py-1 text-xs font-semibold text-economy">Economía</span>
              <h3 className="mt-4 text-lg font-semibold group-hover:text-economy">Actividad económica</h3>
              <p className="mt-2 text-sm leading-6 text-muted">EMAE original mensual, con serie histórica, tabla y procedencia.</p>
            </Link>
          ) : (
            <p className="rounded-lg border border-line bg-white p-5 text-sm text-muted">Las temáticas aparecerán cuando tengan indicadores con observaciones verificadas.</p>
          )}
        </div>
      </section>

      {emae ? (
        <section aria-labelledby="destacados-titulo">
          <h2 id="destacados-titulo" className="text-2xl font-semibold">Indicadores destacados</h2>
          <article className="mt-5 grid gap-5 rounded-xl border border-line bg-white p-5 sm:grid-cols-[1fr_auto] sm:items-center">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-economy">Economía · Serie original</p>
              <h3 className="mt-1 text-xl font-semibold">{emae.name}</h3>
              <p className="mt-2 max-w-2xl text-sm text-muted">{emae.description}</p>
              <div className="mt-4 flex flex-wrap items-center gap-3"><FreshnessBadge date={emae.last_updated_at} /><Link href="/temas/economia/actividad" className="text-sm font-semibold text-accent underline">Abrir dashboard</Link></div>
            </div>
            <div className="min-w-48 border-t border-line pt-4 sm:border-l sm:border-t-0 sm:pl-6 sm:pt-0">
              <p className="text-3xl font-semibold text-ink">{valueFormatter.format(Number(emae.latest_value))}</p>
              <p className="mt-1 text-sm text-muted">{emae.unit}</p><p className="mt-1 text-xs text-muted">Período {emae.latest_period}</p>
            </div>
          </article>
        </section>
      ) : null}

      <section className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-xl border border-line bg-white p-6"><p className="text-sm font-medium text-muted">Explorar por territorio</p><h2 className="mt-1 text-xl font-semibold">Argentina</h2><p className="mt-2 text-sm leading-6 text-muted">La cobertura territorial se habilita únicamente cuando una serie incluye jurisdicciones comparables. El EMAE publicado tiene alcance nacional.</p></div>
        <div className="rounded-xl border border-line bg-white p-6"><p className="text-sm font-medium text-muted">Últimas actualizaciones</p><h2 className="mt-1 text-xl font-semibold">Actividad de las fuentes</h2><p className="mt-2 text-sm text-muted">Última sincronización exitosa: {formatDateTime(stats.last_successful_run?.finished_at ?? null)}.</p><Link href="/historial" className="mt-4 inline-block text-sm font-semibold text-accent underline">Ver historial de cambios</Link></div>
      </section>

      <section className="rounded-xl bg-accent-deep px-6 py-8 text-white sm:px-8" aria-labelledby="transparencia-inicio">
        <div className="grid gap-7 lg:grid-cols-[1fr_auto] lg:items-center">
          <div><h2 id="transparencia-inicio" className="text-2xl font-semibold">Transparencia desde el origen</h2><p className="mt-3 max-w-3xl text-sm leading-7 text-white/80">Conservamos {formatNumber(stats.raw_snapshots)} snapshots RAW. Cada transformación publicada registra su versión, hashes y fuente; los errores y valores ausentes permanecen visibles.</p></div>
          <div className="flex flex-wrap gap-3"><Link href="/acerca" className="rounded-md bg-white px-4 py-2.5 text-sm font-semibold text-accent-deep">Cómo funciona</Link><Link href="/datasets" className="rounded-md border border-white/40 px-4 py-2.5 text-sm font-semibold text-white">Acceso técnico</Link></div>
        </div>
      </section>
    </div>
  );
}
