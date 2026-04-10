"use client";
import { useState, useMemo } from "react";
import {
  useReactTable, getCoreRowModel, getSortedRowModel,
  flexRender, type ColumnDef, type SortingState,
} from "@tanstack/react-table";
import { AppShell } from "@/components/layout/AppShell";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { useDataQuery, useProduct } from "@/hooks/useData";
import { useFilterStore } from "@/store/filters";
import { formatNumber, formatDate, downloadBlob } from "@/lib/utils";
import { dataApi } from "@/lib/api";
import { Download, ChevronUp, ChevronDown, ChevronsUpDown, Filter } from "lucide-react";
import { toast } from "sonner";
import type { Measurement } from "@/lib/types";

export default function ExplorerPage() {
  const { productId, dateFrom, dateTo } = useFilterStore();
  const [sorting, setSorting] = useState<SortingState>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(0);
  const pageSize = 100;

  const { data: result, isLoading } = useDataQuery({
    productId,
    dateFrom,
    dateTo,
    status: statusFilter || undefined,
    limit: pageSize,
    offset: page * pageSize,
  });

  const { data: product } = useProduct(productId);
  const rows = (result?.data ?? []) as Measurement[];
  const total = result?.total ?? 0;

  const metricCols = useMemo(
    () => product?.metrics?.map((m: { name: string; unit: string }) => m.name) ?? [],
    [product]
  );

  const columns = useMemo<ColumnDef<Measurement>[]>(
    () => [
      { accessorKey: "batch_id", header: "Batch", size: 130 },
      { accessorKey: "lot_id", header: "Lot", size: 100 },
      { accessorKey: "test_id", header: "Test", size: 120 },
      { accessorKey: "unit_id", header: "Unit", size: 120 },
      {
        accessorKey: "timestamp",
        header: "Timestamp",
        size: 160,
        cell: ({ getValue }) => formatDate(getValue() as string, "MMM d HH:mm"),
      },
      {
        accessorKey: "status",
        header: "Status",
        size: 90,
        cell: ({ getValue }) => {
          const s = getValue() as string;
          return <Badge variant={s === "passed" ? "success" : "danger"}>{s}</Badge>;
        },
      },
      ...metricCols.map((name: string) => ({
        accessorKey: name,
        header: name,
        size: 100,
        cell: ({ getValue }: { getValue: () => unknown }) => {
          const v = getValue();
          return typeof v === "number" ? formatNumber(v) : "—";
        },
      })),
    ],
    [metricCols]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    manualPagination: true,
    pageCount: Math.ceil(total / pageSize),
  });

  const handleExport = async () => {
    try {
      const res = await dataApi.export(productId, "csv", dateFrom, dateTo);
      downloadBlob(res.data, `${productId}_export.csv`);
      toast.success("Export ready");
    } catch {
      toast.error("Export failed");
    }
  };

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Data Explorer</h1>
            <p className="text-sm text-slate-500 mt-0.5">{total.toLocaleString()} records found</p>
          </div>
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Download className="h-4 w-4" />
            Export CSV
          </button>
        </div>

        {/* Filters */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 flex items-center gap-4">
          <Filter className="h-4 w-4 text-slate-400" />
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}
            className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-1.5 bg-white dark:bg-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All statuses</option>
            <option value="passed">Passed</option>
            <option value="failed">Failed</option>
          </select>
          <DateRangeInputs />
        </div>

        {/* Table */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
          {isLoading ? (
            <FullPageSpinner />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 dark:bg-slate-900/50">
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((h) => (
                        <th
                          key={h.id}
                          className="px-3 py-3 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider cursor-pointer select-none"
                          style={{ width: h.getSize() }}
                          onClick={h.column.getToggleSortingHandler()}
                        >
                          <span className="flex items-center gap-1">
                            {flexRender(h.column.columnDef.header, h.getContext())}
                            {h.column.getCanSort() && (
                              h.column.getIsSorted() === "asc" ? <ChevronUp className="h-3 w-3" /> :
                              h.column.getIsSorted() === "desc" ? <ChevronDown className="h-3 w-3" /> :
                              <ChevronsUpDown className="h-3 w-3 opacity-40" />
                            )}
                          </span>
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row, i) => (
                    <tr
                      key={row.id}
                      className={`border-b border-slate-100 dark:border-slate-700/50 last:border-0 hover:bg-slate-50 dark:hover:bg-slate-700/30 ${i % 2 === 0 ? "" : "bg-slate-50/40 dark:bg-slate-800/40"}`}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-3 py-2.5 font-mono text-xs">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-700 text-sm">
            <span className="text-slate-500">
              Rows {page * pageSize + 1}–{Math.min((page + 1) * pageSize, total)} of {total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 border border-slate-200 dark:border-slate-600 rounded-lg disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={(page + 1) * pageSize >= total}
                className="px-3 py-1 border border-slate-200 dark:border-slate-600 rounded-lg disabled:opacity-40 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function DateRangeInputs() {
  const { dateFrom, dateTo, setDateFrom, setDateTo } = useFilterStore();
  return (
    <div className="flex items-center gap-2">
      <input type="date" value={dateFrom ?? ""} onChange={(e) => setDateFrom(e.target.value)}
        className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-700" />
      <span className="text-slate-400 text-xs">to</span>
      <input type="date" value={dateTo ?? ""} onChange={(e) => setDateTo(e.target.value)}
        className="text-sm border border-slate-200 dark:border-slate-600 rounded-lg px-2 py-1.5 bg-white dark:bg-slate-700" />
    </div>
  );
}
