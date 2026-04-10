"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { HeatmapChart } from "@/components/charts/HeatmapChart";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { usePivot, useProduct } from "@/hooks/useData";
import { useFilterStore } from "@/store/filters";
import { Grid2X2, RefreshCw } from "lucide-react";

export default function PivotPage() {
  const { productId, dateFrom, dateTo } = useFilterStore();
  const { data: product } = useProduct(productId);

  const metricNames = product?.metrics?.map((m: { name: string }) => m.name) ?? ["voltage"];

  const [params, setParams] = useState({
    index: "batch_id",
    columns: "test_id",
    values: "voltage",
    agg_func: "mean",
  });

  const { data: pivot, isLoading, refetch } = usePivot({
    product_id: productId,
    date_from: dateFrom,
    date_to: dateTo,
    ...params,
  });

  const handleChange = (key: keyof typeof params, value: string) => {
    setParams((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Pivot Table</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              {pivot ? `${pivot.shape[0]} rows × ${pivot.shape[1]} columns` : "Configure and generate"}
            </p>
          </div>
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Compute
          </button>
        </div>

        {/* Configuration */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2">
            <Grid2X2 className="h-4 w-4" />
            Pivot Configuration
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <ConfigSelect
              label="Row (Index)"
              value={params.index}
              options={["batch_id", "lot_id", "test_id", "unit_id"]}
              onChange={(v) => handleChange("index", v)}
            />
            <ConfigSelect
              label="Column"
              value={params.columns}
              options={["test_id", "batch_id", "lot_id"]}
              onChange={(v) => handleChange("columns", v)}
            />
            <ConfigSelect
              label="Values"
              value={params.values}
              options={metricNames}
              onChange={(v) => handleChange("values", v)}
            />
            <ConfigSelect
              label="Aggregation"
              value={params.agg_func}
              options={["mean", "min", "max", "sum", "count"]}
              onChange={(v) => handleChange("agg_func", v)}
            />
          </div>
        </div>

        {/* Result */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
              Heatmap: {params.index} × {params.columns} → {params.agg_func}({params.values})
            </h2>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="inline-block w-4 h-3 bg-blue-200 rounded" />Blue = low
              <span className="inline-block w-4 h-3 bg-green-500 rounded ml-2" />Green = high
            </div>
          </div>
          {isLoading ? (
            <FullPageSpinner />
          ) : pivot?.data?.length ? (
            <HeatmapChart data={pivot.data as Record<string, unknown>[]} rowKey={params.index} height={400} />
          ) : (
            <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
              Click &quot;Compute&quot; to generate pivot table
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}

function ConfigSelect({
  label, value, options, onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wide">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </div>
  );
}
