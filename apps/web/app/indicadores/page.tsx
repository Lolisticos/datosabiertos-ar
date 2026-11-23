import Link from "next/link";
import { ApiErrorState } from "@/components/api-error-state";
import { Breadcrumbs } from "@/components/navigation/breadcrumbs";
import { ApiFailure, getIndicators } from "@/lib/api";

export const metadata = { title: "Indicadores" };

export default async function IndicatorsPage() {
  let indicators;
  try {
    indicators = await getIndicators();
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }
  const published = indicators.items.filter((indicator) => indicator.latest_value !== null);
  return (
    <div>
      <Breadcrumbs items={[{ label: "Inicio", href: "/" }, { label: "Indicadores" }]} />
      <h1 className="text-3xl font-semibold tracking-tight">Indicadores</h1>
      <p className="mt-2 max-w-3xl text-muted">Series estadísticas oficiales normalizadas, con unidad, metodología y procedencia verificable.</p>
      {published.length ? (
        <ul className="mt-6 grid gap-4 sm:grid-cols-2">
          {published.map((indicator) => (
            <li key={indicator.code} className="rounded-lg border border-line bg-white p-5">
              <p className="text-xs font-semibold uppercase tracking-wider text-economy">{indicator.topic}</p>
              <h2 className="mt-1 text-lg font-semibold">
                <Link className="hover:text-accent hover:underline" href="/temas/economia/actividad">{indicator.name}</Link>
              </h2>
              <p className="mt-2 text-sm text-muted">{indicator.description}</p>
              <p className="mt-4 text-sm text-ink">Último período: {indicator.latest_period} · {indicator.unit}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-6 rounded-lg border border-line bg-white p-5 text-muted">No hay indicadores con observaciones publicadas. No se muestran series vacías.</p>
      )}
    </div>
  );
}
