import type { Observation } from "@/lib/schemas";

const valueFormatter = new Intl.NumberFormat("es-AR", { maximumFractionDigits: 3 });
const periodFormatter = new Intl.DateTimeFormat("es-AR", {
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

export function ObservationsTable({ observations }: { observations: Observation[] }) {
  return (
    <section className="rounded-lg border border-line bg-white" aria-labelledby="tabla-observaciones">
      <div className="border-b border-line px-4 py-4 sm:px-5">
        <h2 id="tabla-observaciones" className="text-lg font-semibold">Observaciones</h2>
        <p className="mt-1 text-sm text-muted">Alternativa tabular completa al gráfico para el período seleccionado.</p>
      </div>
      <div className="max-h-[34rem] overflow-auto">
        <table className="w-full min-w-[34rem] border-collapse text-left text-sm">
          <caption className="sr-only">Serie original mensual del EMAE, índice base 2004 igual a 100</caption>
          <thead className="sticky top-0 bg-paper text-muted">
            <tr>
              <th scope="col" className="px-4 py-3 font-medium sm:px-5">Período</th>
              <th scope="col" className="px-4 py-3 text-right font-medium">Valor</th>
              <th scope="col" className="px-4 py-3 font-medium sm:px-5">Unidad</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {[...observations].reverse().map((observation) => (
              <tr key={observation.id} className="hover:bg-paper/70">
                <th scope="row" className="px-4 py-3 font-medium text-ink sm:px-5">
                  {periodFormatter.format(new Date(`${observation.period_start}T00:00:00Z`))}
                </th>
                <td className="px-4 py-3 text-right font-mono text-ink">
                  {observation.value === null ? (
                    <span className="font-sans text-muted">Sin dato</span>
                  ) : (
                    valueFormatter.format(Number.parseFloat(observation.value))
                  )}
                </td>
                <td className="px-4 py-3 text-muted sm:px-5">{observation.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
