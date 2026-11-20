import type { ReactNode } from "react";

export const inputClass =
  "h-11 w-full rounded-xl border border-line bg-white px-3 text-sm font-normal text-ink outline-none transition placeholder:text-muted/70 focus:border-accent focus:ring-4 focus:ring-accent/15";

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="grid gap-1.5 text-sm font-medium text-ink">
      {label}
      {children}
    </label>
  );
}
