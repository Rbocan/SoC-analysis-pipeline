"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { TrendChart } from "@/components/charts/TrendChart";
import { PassFailChart } from "@/components/charts/PassFailChart";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { useMetrics, useTrend, useDataQuery, useProduct } from "@/hooks/useData";
import { useFilterStore } from "@/store/filters";
import { formatNumber, formatPercent } from "@/lib/utils";
import { Activity, Zap, Thermometer, CheckCircle, AlertTriangle } from "lucide-react";
import type { MetricStats, Measurement } from "@/lib/types";

export default function DashboardPage() {
  const { productId, dateFrom, dateTo } = useFilterStore();
  const [activeTrendMetric, setActiveTrendMetric] = useState("voltage");

  const { data: metrics, isLoading: metricsLoading } = useMetrics(productId, dateFrom, dateTo);
  const { data: trend, isLoading: trendLoading } = useTrend(productId, activeTrendMetric, "day", dateFrom, dateTo);
  const { data: queryResult } = useDataQuery({ productId, dateFrom, dateTo, limit: 500 });
  const { data: product } = useProduct(productId);

  const measurements = (queryResult?.data ?? []) as Measurement[];

  if (metricsLoading) return <AppShell><FullPageSpinner /></AppShell>;

  const passRate = metrics?.pass_rate ?? 0;
  const total = metrics?.total_records ?? 0;
  const primaryMetric = product?.metrics?.[0];
  const primaryStats = metrics?.[primaryMetric?.name ?? "voltage"] as MetricStats | undefined;
  const secondMetric = product?.metrics?.[2]; // temperature
  const secondStats = metrics?.[secondMetric?.name ?? "temperature"] as MetricStats | undefined;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Page header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Dashboard</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {product?.name} · {dateFrom} → {dateTo}
            </p>
          </div>
          <DateRangePicker />
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Pass Rate"
            value={formatPercent(passRate)}
            subtitle={`${total.toLocaleString()} units tested`}
            icon={CheckCircle}
            variant={passRate >= 95 ? "success" : passRate >= 85 ? "warning" : "danger"}
          />
          <MetricCard
            title="Total Tested"
            value={total.toLocaleString()}
            subtitle="units in period"
            icon={Activity}
          />
          {primaryMetric && primaryStats && (
            <MetricCard
              title={`Avg ${primaryMetric.name}`}
              value={`${formatNumber(primaryStats.mean ?? 0)} ${primaryMetric.unit}`}
              subtitle={`σ = ${formatNumber(primaryStats.std ?? 0)}`}
              icon={Zap}
            />
          )}
          {secondMetric && secondStats && (
            <MetricCard
              title={`Avg ${secondMetric.name}`}
              value={`${formatNumber(secondStats.mean ?? 0)} ${secondMetric.unit}`}
              subtitle={`Range: ${formatNumber(secondStats.min ?? 0)}–${formatNumber(secondStats.max ?? 0)}`}
              icon={Thermometer}
            />
          )}
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          {/* Trend Chart — takes 2/3 */}
          <div className="xl:col-span-2 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Metric Trend</h2>
              <div className="flex gap-1">
                {product?.metrics?.slice(0, 4).map((m: { name: string; unit: string }) => (
                  <button
                    key={m.name}
                    onClick={() => setActiveTrendMetric(m.name)}
                    className={`px-2 py-1 rounded text-xs font-medium transition-colors ${
                      activeTrendMetric === m.name
                        ? "bg-blue-600 text-white"
                        : "text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700"
                    }`}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
            </div>
            {trendLoading ? (
              <FullPageSpinner />
            ) : (
              <TrendChart
                data={trend?.data ?? []}
                metric={activeTrendMetric}
                unit={product?.metrics?.find((m: { name: string }) => m.name === activeTrendMetric)?.unit ?? ""}
                height={260}
              />
            )}
          </div>

          {/* Pass/Fail — takes 1/3 */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">Pass / Fail by Test</h2>
            <PassFailChart data={measurements} height={260} />
          </div>
        </div>

        {/* Metrics Table */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">Metric Statistics</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  {["Metric", "Mean", "Min", "Max", "Std Dev"].map((h) => (
                    <th key={h} className="text-left py-2 px-3 text-xs font-semibold text-slate-500 uppercase tracking-wide">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {product?.metrics?.map((m: { name: string; unit: string }) => {
                  const s = metrics?.[m.name] as MetricStats | undefined;
                  return (
                    <tr key={m.name} className="border-b border-slate-100 dark:border-slate-700/50 last:border-0">
                      <td className="py-2.5 px-3 font-medium capitalize">{m.name} <span className="text-slate-400 text-xs">({m.unit})</span></td>
                      <td className="py-2.5 px-3 font-mono">{s ? formatNumber(s.mean ?? 0) : "—"}</td>
                      <td className="py-2.5 px-3 font-mono">{s ? formatNumber(s.min ?? 0) : "—"}</td>
                      <td className="py-2.5 px-3 font-mono">{s ? formatNumber(s.max ?? 0) : "—"}</td>
                      <td className="py-2.5 px-3 font-mono">{s ? formatNumber(s.std ?? 0) : "—"}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function DateRangePicker() {
  const { dateFrom, dateTo, setDateFrom, setDateTo } = useFilterStore();
  return (
    <div className="flex items-center gap-2 text-sm">
      <input
        type="date"
        value={dateFrom ?? ""}
        onChange={(e) => setDateFrom(e.target.value)}
        className="border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
      <span className="text-slate-400">→</span>
      <input
        type="date"
        value={dateTo ?? ""}
        onChange={(e) => setDateTo(e.target.value)}
        className="border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </div>
  );
}
