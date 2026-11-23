import type { ReactNode } from "react";

export function DashboardHeader({
  eyebrow,
  title,
  description,
  metadata,
}: {
  eyebrow: string;
  title: string;
  description: string;
  metadata?: ReactNode;
}) {
  return (
    <header className="border-l-4 border-economy pl-4 sm:pl-5">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-economy">{eyebrow}</p>
      <h1 className="mt-1 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{title}</h1>
      <p className="mt-3 max-w-3xl text-base leading-7 text-muted">{description}</p>
      {metadata ? <div className="mt-4 flex flex-wrap items-center gap-3">{metadata}</div> : null}
    </header>
  );
}
