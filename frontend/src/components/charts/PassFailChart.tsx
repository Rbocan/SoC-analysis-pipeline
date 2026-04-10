"use client";
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from "recharts";
import type { Measurement } from "@/lib/types";

interface PassFailChartProps {
  data: Measurement[];
  height?: number;
}

export function PassFailChart({ data, height = 240 }: PassFailChartProps) {
  if (!data?.length) {
    return <div className="flex items-center justify-center h-48 text-slate-400 text-sm">No data</div>;
  }

  // Aggregate by test_id
  const byTest: Record<string, { passed: number; failed: number }> = {};
  for (const row of data) {
    if (!byTest[row.test_id]) byTest[row.test_id] = { passed: 0, failed: 0 };
    byTest[row.test_id][row.status === "passed" ? "passed" : "failed"]++;
  }

  const chartData = Object.entries(byTest).map(([test_id, counts]) => ({
    test_id,
    ...counts,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 4, right: 16, bottom: 24, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="test_id" tick={{ fontSize: 11 }} angle={-20} textAnchor="end" tickLine={false} />
        <YAxis tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
          labelStyle={{ fontWeight: 600 }}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Bar dataKey="passed" fill="#16a34a" name="Passed" radius={[4, 4, 0, 0]} />
        <Bar dataKey="failed" fill="#dc2626" name="Failed" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
