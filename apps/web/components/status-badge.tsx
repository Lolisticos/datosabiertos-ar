type Tone = "ok" | "warn" | "danger" | "info" | "neutral";

const TONE_CLASSES: Record<Tone, string> = {
  ok: "bg-accent-soft text-accent-deep border-accent/30",
  warn: "bg-warn/10 text-warn border-warn/30",
  danger: "bg-danger/10 text-danger border-danger/30",
  info: "bg-info/10 text-info border-info/30",
  neutral: "bg-paper text-muted border-line",
};

// Small labelled pill for statuses (runs, checks, availability).
export function StatusBadge({
  tone = "neutral",
  children,
}: {
  tone?: Tone;
  children: React.ReactNode;
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}

export function toneForRunStatus(status: string): Tone {
  if (status === "succeeded") return "ok";
  if (status === "running") return "info";
  if (status === "partial") return "warn";
  if (status === "failed") return "danger";
  return "neutral";
}

export function toneForCheckStatus(status: string): Tone {
  if (status === "passed") return "ok";
  if (status === "warning") return "warn";
  if (status === "failed") return "danger";
  return "neutral";
}
