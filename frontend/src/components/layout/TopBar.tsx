"use client";
import { Moon, Sun, RefreshCw, Bell } from "lucide-react";
import { useTheme } from "next-themes";
import { useQueryClient } from "@tanstack/react-query";
import { useFilterStore } from "@/store/filters";
import { useProducts } from "@/hooks/useData";

export function TopBar() {
  const { theme, setTheme } = useTheme();
  const qc = useQueryClient();
  const { productId, setProductId } = useFilterStore();
  const { data: products = [] } = useProducts();

  return (
    <header className="h-14 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center px-6 gap-4">
      {/* Product Selector */}
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">Product</label>
        <select
          value={productId}
          onChange={(e) => setProductId(e.target.value)}
          className="text-sm border border-slate-200 dark:border-slate-600 rounded-md px-2 py-1.5 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {products.map((p: { id: string; name: string }) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      <div className="flex-1" />

      {/* Actions */}
      <button
        onClick={() => qc.invalidateQueries()}
        className="p-2 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
        title="Refresh data"
      >
        <RefreshCw className="h-4 w-4" />
      </button>

      <button
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        className="p-2 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
      >
        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>

      <button className="p-2 rounded-md text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors">
        <Bell className="h-4 w-4" />
      </button>
    </header>
  );
}
