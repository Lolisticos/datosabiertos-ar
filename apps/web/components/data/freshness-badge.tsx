import { formatDateTime, isoTitle } from "@/lib/format";

export function FreshnessBadge({ date }: { date: string | null }) {
  return (
    <span
      className="inline-flex rounded-full border border-accent/25 bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent-deep"
      title={isoTitle(date)}
    >
      Actualizado {formatDateTime(date)}
    </span>
  );
}
