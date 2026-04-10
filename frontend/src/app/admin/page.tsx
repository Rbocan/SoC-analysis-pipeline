"use client";
import { useState, useEffect } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { healthApi, productsApi } from "@/lib/api";
import { Settings, CheckCircle, XCircle, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import type { HealthStatus } from "@/lib/types";

export default function AdminPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchHealth = async () => {
    try {
      const res = await healthApi.check();
      setHealth(res.data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchHealth(); }, []);

  const reloadConfigs = async () => {
    try {
      await productsApi.reload();
      toast.success("Configs reloaded");
    } catch {
      toast.error("Reload failed — check admin permissions");
    }
  };

  return (
    <AppShell>
      <div className="space-y-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Admin</h1>
          <p className="text-sm text-slate-500 mt-0.5">System health, configuration, and audit logs</p>
        </div>

        {/* System Health */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 flex items-center gap-2">
              <Settings className="h-4 w-4" />
              System Health
            </h2>
            <button
              onClick={() => { setLoading(true); fetchHealth(); }}
              className="flex items-center gap-2 px-3 py-1.5 text-sm border border-slate-200 dark:border-slate-600 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Refresh
            </button>
          </div>

          {loading ? (
            <FullPageSpinner />
          ) : health ? (
            <div className="space-y-3">
              <div className="flex items-center gap-3 pb-3 border-b border-slate-100 dark:border-slate-700">
                <Badge variant={health.status === "ok" ? "success" : "danger"}>
                  {health.status.toUpperCase()}
                </Badge>
                <span className="text-sm text-slate-500">v{health.version} · {health.environment}</span>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {Object.entries(health.services).map(([name, status]) => (
                  <div key={name} className="flex items-center gap-2 p-3 bg-slate-50 dark:bg-slate-900/40 rounded-lg">
                    {status === "ok" ? (
                      <CheckCircle className="h-4 w-4 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-500" />
                    )}
                    <div>
                      <p className="text-xs font-semibold capitalize text-slate-700 dark:text-slate-200">{name}</p>
                      <p className={`text-xs ${status === "ok" ? "text-green-600" : "text-red-600"}`}>{status}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-sm text-red-500">Could not reach backend API</div>
          )}
        </div>

        {/* Config Management */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">Configuration Management</h2>
          <div className="flex items-center gap-4">
            <button
              onClick={reloadConfigs}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              <RefreshCw className="h-4 w-4" />
              Reload Product Configs
            </button>
            <p className="text-xs text-slate-400">
              Hot-reload products.yaml and pipelines.yaml without restarting the backend.
            </p>
          </div>
        </div>

        {/* Quick Reference */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">API Documentation</h2>
          <div className="flex gap-3">
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-sm hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
            >
              Swagger UI
            </a>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/redoc`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg text-sm hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
            >
              ReDoc
            </a>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
