import { formatNumber } from "@/lib/format";

// One coverage figure. The label must always state unit / period / scope so
// numbers never float without context.
export function Figure({
  value,
  label,
  note,
}: {
  value: number | string;
  label: string;
  note?: string;
}) {
  return (
    <div className="rounded-lg border border-line bg-white p-4">
      <p className="font-mono text-2xl font-semibold tabular-nums text-ink">
        {typeof value === "number" ? formatNumber(value) : value}
      </p>
      <p className="mt-1 text-sm font-medium text-ink">{label}</p>
      {note ? <p className="text-xs text-muted">{note}</p> : null}
    </div>
  );
}
