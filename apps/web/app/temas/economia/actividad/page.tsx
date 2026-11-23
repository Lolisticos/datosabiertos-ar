import Link from "next/link";
import { ActivityChart } from "@/components/charts/activity-chart";
import { ChartCard } from "@/components/dashboard/chart-card";
import { DashboardHeader } from "@/components/dashboard/dashboard-header";
import { MetricCard } from "@/components/dashboard/metric-card";
import { FreshnessBadge } from "@/components/data/freshness-badge";
import { ObservationsTable } from "@/components/data/observations-table";
import { Breadcrumbs } from "@/components/navigation/breadcrumbs";
import { SourceAttribution } from "@/components/provenance/source-attribution";
import { ApiErrorState } from "@/components/api-error-state";
import {
  ApiFailure,
  getAllIndicatorObservations,
  getIndicator,
  getIndicatorCoverage,
  indicatorCsvUrl,
} from "@/lib/api";

export const metadata = {
  title: "Actividad económica — EMAE",
  description: "Serie original mensual del Estimador Mensual de Actividad Económica del INDEC.",
};

const CODE = "emae-original-2004";
const valueFormatter = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 2 });
const periodFormatter = new Intl.DateTimeFormat("es-AR", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

type Range = "5y" | "10y" | "all";

function selectRange<T extends { period_start: string }>(items: T[], range: Range): T[] {
  if (range === "all" || items.length === 0) return items;
  const latest = new Date(`${items.at(-1)!.period_start}T00:00:00Z`);
  latest.setUTCFullYear(latest.getUTCFullYear() - (range === "5y" ? 5 : 10));
  return items.filter((item) => new Date(`${item.period_start}T00:00:00Z`) >= latest);
}

export default async function ActivityDashboard({
  searchParams,
}: {
  searchParams: Promise<{ range?: string }>;
}) {
  const rawRange = (await searchParams).range;
  const range: Range = rawRange === "5y" || rawRange === "10y" ? rawRange : "all";
  let indicator;
  let observations;
  let coverage;
  try {
    [indicator, observations, coverage] = await Promise.all([
      getIndicator(CODE),
      getAllIndicatorObservations(CODE),
      getIndicatorCoverage(CODE),
    ]);
  } catch (error) {
    if (error instanceof ApiFailure) return <ApiErrorState error={error} />;
    throw error;
  }

  const visible = selectRange(observations, range);
  const latest = [...observations].reverse().find((item) => item.value !== null);

  return (
    <div className="space-y-7">
      <Breadcrumbs
        items={[
          { label: "Inicio", href: "/" },
          { label: "Indicadores", href: "/indicadores" },
          { label: "Economía" },
          { label: "Actividad económica" },
        ]}
      />
      <DashboardHeader
        eyebrow="Economía"
        title="Actividad económica"
        description="Evolución del Estimador Mensual de Actividad Económica (EMAE). Se muestra únicamente la serie original del INDEC, índice base 2004=100."
        metadata={
          <>
            <span className="text-sm font-medium text-ink">Fuente: INDEC</span>
            <FreshnessBadge date={indicator.downloaded_at} />
          </>
        }
      />

      {observations.length === 0 ? (
        <section className="rounded-lg border border-warn/30 bg-white p-6" role="status">
          <h2 className="font-semibold text-ink">Datos todavía no sincronizados</h2>
          <p className="mt-2 text-sm text-muted">
            El indicador y su metodología están configurados, pero no hay observaciones publicadas. No se muestran valores de ejemplo.
          </p>
        </section>
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-3">
            <MetricCard
              label="Último valor disponible"
              value={latest?.value ? valueFormatter.format(Number.parseFloat(latest.value)) : "Sin dato"}
              detail={latest ? `${periodFormatter.format(new Date(`${latest.period_start}T00:00:00Z`))} · ${indicator.unit}` : undefined}
            />
            <MetricCard
              label="Cobertura temporal"
              value={`${coverage.period.start?.slice(0, 4) ?? "—"}–${coverage.period.end?.slice(0, 4) ?? "—"}`}
              detail={`${coverage.observation_count} observaciones mensuales`}
            />
            <MetricCard
              label="Valores ausentes"
              value={coverage.missing_value_count}
              detail="Se muestran como ‘Sin dato’, nunca como cero"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-line bg-white px-4 py-3">
            <div className="flex items-center gap-2" aria-label="Período visible">
              <span className="mr-1 text-sm font-medium text-muted">Período</span>
              {(["5y", "10y", "all"] as const).map((item) => (
                <Link
                  key={item}
                  href={item === "all" ? "/temas/economia/actividad" : `/temas/economia/actividad?range=${item}`}
                  aria-current={range === item ? "page" : undefined}
                  className="rounded-md border border-line px-3 py-1.5 text-sm text-ink hover:border-accent aria-[current=page]:border-accent aria-[current=page]:bg-accent-soft aria-[current=page]:text-accent-deep"
                >
                  {item === "all" ? "Todo" : item === "5y" ? "5 años" : "10 años"}
                </Link>
              ))}
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
              <a className="font-semibold text-accent underline" href={indicatorCsvUrl(CODE)}>
                Descargar CSV
              </a>
              <a className="font-semibold text-accent underline" href={`${indicator.source_url ?? ""}`} target="_blank" rel="noopener noreferrer">
                Consultar JSON oficial
              </a>
            </div>
          </div>

          <ChartCard
            title="EMAE — serie original"
            description="Índice base 2004=100. El zoom permite recorrer la serie; los cortes indican datos ausentes."
          >
            <ActivityChart observations={visible} title={indicator.name} unit={indicator.unit} />
          </ChartCard>
          <ObservationsTable observations={visible} />
        </>
      )}

      <SourceAttribution indicator={indicator} />
    </div>
  );
}
