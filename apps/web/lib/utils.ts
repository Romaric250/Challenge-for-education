import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function citationLabel(item: {
  marker?: unknown;
  document?: unknown;
  page_start?: unknown;
  page_end?: unknown;
}) {
  const marker = typeof item.marker === "string" ? item.marker : "";
  const document = typeof item.document === "string" ? item.document : "";
  const start = typeof item.page_start === "number" ? item.page_start : null;
  const end = typeof item.page_end === "number" ? item.page_end : null;
  const pages =
    start === null ? "" : start === end || end === null ? `p. ${start}` : `pp. ${start}-${end}`;
  return [marker, document, pages].filter(Boolean).join(" ");
}
