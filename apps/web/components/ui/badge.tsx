import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "good" | "warn";
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium",
        tone === "good" && "bg-mist text-accent-strong",
        tone === "warn" && "bg-[#f8ead2] text-[#7a4b12]",
        tone === "neutral" && "bg-paper text-muted",
      )}
    >
      {children}
    </span>
  );
}
