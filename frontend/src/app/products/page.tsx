"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { FullPageSpinner, Spinner } from "@/components/ui/Spinner";
import { useProducts } from "@/hooks/useData";
import { useGenerateSynthetic } from "@/hooks/useData";
import { formatNumber } from "@/lib/utils";
import { Cpu, Zap, Play, ChevronDown, ChevronRight } from "lucide-react";
import { toast } from "sonner";
import type { Product } from "@/lib/types";

export default function ProductsPage() {
  const { data: products = [], isLoading } = useProducts();
  const [expanded, setExpanded] = useState<string | null>(null);

  return (
    <AppShell>
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Products</h1>
          <p className="text-sm text-slate-500 mt-0.5">YAML-driven product configurations. Add new products by editing products.yaml.</p>
        </div>

        {isLoading ? (
          <FullPageSpinner />
        ) : (
          <div className="space-y-3">
            {products.map((p: Product) => (
              <ProductCard
                key={p.id}
                product={p}
                isExpanded={expanded === p.id}
                onToggle={() => setExpanded(expanded === p.id ? null : p.id)}
              />
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}

function ProductCard({ product, isExpanded, onToggle }: {
  product: Product;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const generateMutation = useGenerateSynthetic();
  const [numRecords, setNumRecords] = useState(50000);

  const handleGenerate = async () => {
    try {
      const result = await generateMutation.mutateAsync({
        product_id: product.id,
        num_records: numRecords,
        num_batches: Math.max(10, Math.floor(numRecords / 500)),
        anomaly_rate: 0.02,
      });
      toast.success(`Generated ${result.records_generated.toLocaleString()} records · Pass rate: ${result.pass_rate}%`);
    } catch {
      toast.error("Failed to generate synthetic data");
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
      <button
        className="w-full flex items-center px-5 py-4 text-left hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
        onClick={onToggle}
      >
        <Cpu className="h-5 w-5 text-blue-500 mr-3 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-slate-800 dark:text-slate-200">{product.name}</p>
          <p className="text-xs text-slate-400 mt-0.5">{product.id} · {product.description}</p>
        </div>
        <div className="flex items-center gap-3 mr-3">
          <Badge variant="info">{product.metrics.length} metrics</Badge>
          <Badge variant="default">{product.tests.length} tests</Badge>
        </div>
        {isExpanded ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />}
      </button>

      {isExpanded && (
        <div className="border-t border-slate-200 dark:border-slate-700 p-5 space-y-5">
          {/* Metrics */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {product.metrics.map((m) => (
                <div key={m.name} className="bg-slate-50 dark:bg-slate-900/40 rounded-lg p-3 text-sm">
                  <p className="font-semibold text-slate-700 dark:text-slate-200 capitalize">{m.name}</p>
                  <p className="text-xs text-slate-400 mt-0.5">{m.unit}</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {formatNumber(m.min_val)} – {formatNumber(m.max_val)}
                  </p>
                  <p className="text-xs text-blue-500 mt-0.5">nominal: {formatNumber(m.nominal)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Tests */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">Tests</h3>
            <div className="flex flex-wrap gap-2">
              {product.tests.map((t) => (
                <Badge key={t} variant="default">{t}</Badge>
              ))}
            </div>
          </div>

          {/* Synthetic Data Generator */}
          <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-4 border border-blue-100 dark:border-blue-900">
            <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-3 flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Generate Synthetic Data
            </h3>
            <div className="flex items-center gap-3">
              <div>
                <label className="text-xs text-blue-600 dark:text-blue-400 font-medium">Records</label>
                <input
                  type="number"
                  min={100}
                  max={1000000}
                  step={1000}
                  value={numRecords}
                  onChange={(e) => setNumRecords(Number(e.target.value))}
                  className="mt-1 block w-32 text-sm border border-blue-200 dark:border-blue-800 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
                className="mt-4 flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {generateMutation.isPending ? <Spinner className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                {generateMutation.isPending ? "Generating…" : "Generate"}
              </button>
            </div>
          </div>

          {/* Data source */}
          <div>
            <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1">Data Source</h3>
            <code className="text-xs text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-900 px-2 py-1 rounded">
              {product.data_source}
            </code>
          </div>
        </div>
      )}
    </div>
  );
}
