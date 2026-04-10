"use client";
import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { Badge } from "@/components/ui/Badge";
import { FullPageSpinner } from "@/components/ui/Spinner";
import { useReportHistory, useGenerateReport } from "@/hooks/useData";
import { useFilterStore } from "@/store/filters";
import { formatDate, downloadBlob } from "@/lib/utils";
import { reportsApi } from "@/lib/api";
import { FileText, Mail, Download, Plus, Clock } from "lucide-react";
import { toast } from "sonner";
import type { Report } from "@/lib/types";

export default function ReportsPage() {
  const { productId, dateFrom, dateTo } = useFilterStore();
  const { data: reports = [], isLoading, refetch } = useReportHistory(productId);
  const generateMutation = useGenerateReport();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    report_type: "daily_validation",
    template: "daily_validation.html",
    recipients: "",
    send_email: false,
  });

  const handleGenerate = async () => {
    try {
      await generateMutation.mutateAsync({
        product_id: productId,
        report_type: form.report_type,
        template: form.template,
        date_from: dateFrom,
        date_to: dateTo,
        recipients: form.recipients.split(",").map((e) => e.trim()).filter(Boolean),
        send_email: form.send_email,
      });
      toast.success("Report generated successfully");
      setShowForm(false);
      refetch();
    } catch {
      toast.error("Report generation failed");
    }
  };

  const handleDownload = async (report: Report, fmt = "pdf") => {
    try {
      const res = await reportsApi.download(report.report_id, fmt);
      downloadBlob(res.data, `${report.report_id}_${report.product_id}.${fmt}`);
    } catch {
      toast.error("Download failed");
    }
  };

  return (
    <AppShell>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Reports</h1>
            <p className="text-sm text-slate-500 mt-0.5">Generate and manage validation reports</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Report
          </button>
        </div>

        {/* Generate Form */}
        {showForm && (
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4 flex items-center gap-2">
              <FileText className="h-4 w-4" />
              Generate Report
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField label="Report Type">
                <select
                  value={form.report_type}
                  onChange={(e) => setForm((f) => ({ ...f, report_type: e.target.value }))}
                  className="form-select"
                >
                  <option value="daily_validation">Daily Validation</option>
                  <option value="weekly_trend">Weekly Trend</option>
                  <option value="monthly_yield">Monthly Yield</option>
                </select>
              </FormField>
              <FormField label="Email Recipients (comma-separated)">
                <input
                  type="text"
                  value={form.recipients}
                  onChange={(e) => setForm((f) => ({ ...f, recipients: e.target.value }))}
                  placeholder="qa@company.com, eng@company.com"
                  className="form-input"
                />
              </FormField>
              <FormField label="">
                <label className="flex items-center gap-2 text-sm cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.send_email}
                    onChange={(e) => setForm((f) => ({ ...f, send_email: e.target.checked }))}
                    className="rounded"
                  />
                  Send email after generation
                </label>
              </FormField>
            </div>
            <div className="flex gap-3 mt-4">
              <button
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {generateMutation.isPending ? "Generating…" : "Generate Report"}
              </button>
              <button
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-slate-200 dark:border-slate-600 rounded-lg text-sm hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Reports List */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="px-5 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center gap-2">
            <Clock className="h-4 w-4 text-slate-400" />
            <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Report History</h2>
          </div>
          {isLoading ? (
            <FullPageSpinner />
          ) : reports.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-slate-400 text-sm">
              No reports yet. Click &quot;New Report&quot; to generate one.
            </div>
          ) : (
            <div className="divide-y divide-slate-100 dark:divide-slate-700">
              {reports.map((r: Report) => (
                <div key={r.report_id} className="flex items-center px-5 py-3.5 hover:bg-slate-50 dark:hover:bg-slate-700/40">
                  <FileText className="h-4 w-4 text-blue-500 mr-3 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">
                      {r.product_id} — {r.report_type}
                    </p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {formatDate(r.generated_at, "MMM d, yyyy HH:mm")} · ID: {r.report_id}
                    </p>
                  </div>
                  <Badge variant={r.status === "completed" ? "success" : "warning"} className="mr-4">
                    {r.status}
                  </Badge>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleDownload(r, "pdf")}
                      className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
                      title="Download PDF"
                    >
                      <Download className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDownload(r, "html")}
                      className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-700 rounded transition-colors"
                      title="Download HTML"
                    >
                      <FileText className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Scheduled Reports */}
        <ScheduledReports />
      </div>
    </AppShell>
  );
}

function ScheduledReports() {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
        <Clock className="h-4 w-4" />
        Scheduled Pipelines
      </h2>
      <div className="space-y-2 text-sm text-slate-600 dark:text-slate-300">
        {[
          { name: "Daily Validation", schedule: "Daily at 6:00 AM" },
          { name: "Weekly Trend Analysis", schedule: "Monday at 8:00 AM" },
          { name: "Monthly Yield Analysis", schedule: "1st of month at 7:00 AM" },
        ].map((s) => (
          <div key={s.name} className="flex items-center justify-between py-2 border-b border-slate-100 dark:border-slate-700 last:border-0">
            <span className="font-medium">{s.name}</span>
            <span className="text-xs text-slate-400">{s.schedule}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      {label && <label className="block text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wide">{label}</label>}
      {children}
    </div>
  );
}
