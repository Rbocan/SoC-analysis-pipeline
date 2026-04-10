import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(date: string | Date, fmt = "MMM d, yyyy") {
  const d = typeof date === "string" ? parseISO(date) : date;
  return format(d, fmt);
}

export function formatNumber(n: number, decimals = 2) {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString("en-US", { maximumFractionDigits: decimals });
}

export function formatPercent(n: number) {
  return `${formatNumber(n, 1)}%`;
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function statusColor(status: string) {
  return status === "passed"
    ? "text-green-600 bg-green-50"
    : "text-red-600 bg-red-50";
}

export const METRIC_COLORS = [
  "#2563eb", "#16a34a", "#d97706", "#dc2626", "#7c3aed", "#0891b2",
];
