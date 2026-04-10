"use client";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, ReferenceLine, Area, AreaChart,
} from "recharts";
import { format, parseISO } from "date-fns";
import type { TrendPoint } from "@/lib/types";
import { METRIC_COLORS } from "@/lib/utils";

interface TrendChartProps {
  data: TrendPoint[];
  metric: string;
  unit?: string;
  height?: number;
}

const fmt = (ts: string) => {
  try { return format(parseISO(ts), "MMM d"); } catch { return ts; }
};

const CustomTooltip = ({ active, payload, label, unit }: {
  active?: boolean;
  payload?: { value: number; name: string }[];
  label?: string;
  unit?: string;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 shadow-lg text-sm">
      <p className="font-semibold text-slate-700 dark:text-slate-200 mb-1">{label && fmt(label)}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: METRIC_COLORS[0] }}>
          {p.name}: <span className="font-medium">{p.value?.toFixed(4)} {unit}</span>
        </p>
      ))}
    </div>
  );
};

export function TrendChart({ data, metric, unit = "", height = 260 }: TrendChartProps) {
  if (!data?.length) {
    return (
      <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
        No trend data available
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
        <defs>
          <linearGradient id="colorMean" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={METRIC_COLORS[0]} stopOpacity={0.15} />
            <stop offset="95%" stopColor={METRIC_COLORS[0]} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={fmt}
          tick={{ fontSize: 11 }}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          tickLine={false}
          axisLine={false}
          tickFormatter={(v) => `${v}${unit}`}
        />
        <Tooltip content={<CustomTooltip unit={unit} />} />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Area
          type="monotone"
          dataKey="min"
          stroke="transparent"
          fill={METRIC_COLORS[0]}
          fillOpacity={0.08}
          name="Range"
          legendType="none"
        />
        <Area
          type="monotone"
          dataKey="mean"
          stroke={METRIC_COLORS[0]}
          strokeWidth={2}
          fill="url(#colorMean)"
          name={`Avg ${metric}`}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
