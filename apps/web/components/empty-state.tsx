import type { ReactNode } from "react";

// Honest empty state: a real zero result, never placeholder content.
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <div
      role="status"
      className="rounded-lg border border-dashed border-line bg-white p-8 text-center"
    >
      <p className="text-lg font-semibold text-ink">{title}</p>
      {children ? (
        <div className="mt-2 text-sm text-muted">{children}</div>
      ) : null}
    </div>
  );
}
