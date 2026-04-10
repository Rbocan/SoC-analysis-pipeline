"use client";
import { useMemo } from "react";
import { cn } from "@/lib/utils";

interface HeatmapChartProps {
  data: Record<string, unknown>[];
  rowKey: string;
  height?: number;
}

function interpolateColor(value: number, min: number, max: number): string {
  if (max === min) return "hsl(220, 70%, 60%)";
  const t = (value - min) / (max - min);
  // Blue → Green gradient
  const h = 220 - t * 140; // 220 (blue) to 80 (green)
  const s = 70;
  const l = 80 - t * 30; // lighter for low, darker for high
  return `hsl(${h}, ${s}%, ${l}%)`;
}

export function HeatmapChart({ data, rowKey, height = 300 }: HeatmapChartProps) {
  const { columns, allValues } = useMemo(() => {
    if (!data?.length) return { columns: [], allValues: { min: 0, max: 1 } };
    const cols = Object.keys(data[0]).filter((k) => k !== rowKey);
    const nums = data.flatMap((row) =>
      cols.map((c) => (typeof row[c] === "number" ? (row[c] as number) : NaN))
    ).filter((n) => !isNaN(n));
    return {
      columns: cols,
      allValues: { min: Math.min(...nums), max: Math.max(...nums) },
    };
  }, [data, rowKey]);

  if (!data?.length) {
    return <div className="flex items-center justify-center h-48 text-slate-400 text-sm">No pivot data</div>;
  }

  const cellSize = Math.min(48, Math.max(32, Math.floor((height - 40) / data.length)));

  return (
    <div className="overflow-auto" style={{ maxHeight: height }}>
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="px-2 py-1 text-left sticky left-0 bg-white dark:bg-slate-800 z-10 min-w-[100px]">
              {rowKey}
            </th>
            {columns.map((col) => (
              <th key={col} className="px-1 py-1 text-center font-medium text-slate-600 dark:text-slate-300 min-w-[60px]">
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.slice(0, 50).map((row, i) => (
            <tr key={i}>
              <td className="px-2 py-0.5 font-mono sticky left-0 bg-white dark:bg-slate-800 z-10 text-slate-700 dark:text-slate-200">
                {String(row[rowKey]).slice(0, 16)}
              </td>
              {columns.map((col) => {
                const val = typeof row[col] === "number" ? (row[col] as number) : null;
                return (
                  <td
                    key={col}
                    className="px-1 py-0.5 text-center font-mono border border-slate-100 dark:border-slate-700"
                    style={{
                      background: val !== null ? interpolateColor(val, allValues.min, allValues.max) : "#f1f5f9",
                      height: cellSize,
                      color: val !== null ? "#1e293b" : "#94a3b8",
                    }}
                    title={`${col}: ${val?.toFixed(3) ?? "—"}`}
                  >
                    {val !== null ? val.toFixed(2) : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {data.length > 50 && (
        <p className="text-xs text-slate-400 mt-2 px-2">Showing first 50 of {data.length} rows</p>
      )}
    </div>
  );
}
