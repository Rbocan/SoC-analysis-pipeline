import axios from "axios";
import { storage } from "./storage";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: `${API_BASE}/api`,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token from storage
apiClient.interceptors.request.use((config) => {
  const token = storage.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-logout on 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      storage.remove("access_token");
      if (typeof window !== "undefined") window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) =>
    apiClient.post("/auth/login", { username, password }),
  register: (data: { username: string; email: string; password: string; role?: string }) =>
    apiClient.post("/auth/register", data),
  profile: () => apiClient.get("/auth/profile"),
  permissions: () => apiClient.get("/auth/permissions"),
};

// ── Products ──────────────────────────────────────────────────────────────────
export const productsApi = {
  list: () => apiClient.get("/products/"),
  get: (id: string) => apiClient.get(`/products/${id}`),
  reload: () => apiClient.post("/products/reload"),
};

// ── Data ──────────────────────────────────────────────────────────────────────
export const dataApi = {
  query: (params: Record<string, unknown>) => apiClient.post("/data/query", params),
  metrics: (productId: string, dateFrom?: string, dateTo?: string) =>
    apiClient.get("/data/metrics", { params: { product_id: productId, date_from: dateFrom, date_to: dateTo } }),
  pivot: (params: Record<string, unknown>) => apiClient.post("/data/pivot", params),
  export: (productId: string, format = "csv", dateFrom?: string, dateTo?: string) =>
    apiClient.get("/data/export", {
      params: { product_id: productId, format, date_from: dateFrom, date_to: dateTo },
      responseType: "blob",
    }),
  trend: (productId: string, metric: string, period = "day", dateFrom?: string, dateTo?: string) =>
    apiClient.get("/data/trend", {
      params: { product_id: productId, metric, period, date_from: dateFrom, date_to: dateTo },
    }),
  anomalies: (productId: string, metric: string, zThreshold = 3.0) =>
    apiClient.get("/data/anomalies", { params: { product_id: productId, metric, z_threshold: zThreshold } }),
};

// ── Reports ───────────────────────────────────────────────────────────────────
export const reportsApi = {
  generate: (params: Record<string, unknown>) => apiClient.post("/reports/generate", params),
  history: (productId?: string) =>
    apiClient.get("/reports/history", { params: productId ? { product_id: productId } : {} }),
  email: (reportId: string, recipients: string[]) =>
    apiClient.post("/reports/email", { report_id: reportId, recipients }),
  download: (reportId: string, fmt = "pdf") =>
    apiClient.get(`/reports/download/${reportId}`, { params: { fmt }, responseType: "blob" }),
  schedule: () => apiClient.get("/reports/schedule"),
};

// ── Synthetic ─────────────────────────────────────────────────────────────────
export const syntheticApi = {
  generate: (params: Record<string, unknown>) => apiClient.post("/synthetic/generate", params),
  generateAll: (numRecords = 50000) =>
    apiClient.post("/synthetic/generate-all", null, { params: { num_records: numRecords } }),
  config: () => apiClient.get("/synthetic/config"),
};

// ── Health ────────────────────────────────────────────────────────────────────
export const healthApi = {
  check: () => apiClient.get("/health/"),
};
