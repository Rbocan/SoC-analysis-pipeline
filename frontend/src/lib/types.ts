// ── Auth ──────────────────────────────────────────────────────────────────────
export interface User {
  id: number;
  username: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
  created_at: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ── Products ──────────────────────────────────────────────────────────────────
export interface MetricSpec {
  name: string;
  unit: string;
  min_val: number;
  max_val: number;
  nominal: number;
  distribution: string;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  metrics: MetricSpec[];
  tests: string[];
  data_source: string;
}

// ── Measurements ──────────────────────────────────────────────────────────────
export interface Measurement {
  product_id: string;
  batch_id: string;
  lot_id: string;
  test_id: string;
  unit_id: string;
  timestamp: string;
  status: "passed" | "failed";
  voltage?: number;
  frequency?: number;
  temperature?: number;
  power?: number;
  [key: string]: unknown;
}

export interface QueryResult {
  total: number;
  offset: number;
  limit: number;
  data: Measurement[];
}

export interface MetricStats {
  mean: number | null;
  min: number | null;
  max: number | null;
  std: number | null;
}

export interface MetricsSummary {
  pass_rate: number;
  total_records: number;
  [metric: string]: number | MetricStats | null;
}

// ── Trend ─────────────────────────────────────────────────────────────────────
export interface TrendPoint {
  timestamp: string;
  mean: number;
  min: number;
  max: number;
  std: number;
  count: number;
}

export interface TrendResult {
  metric: string;
  period: string;
  data: TrendPoint[];
}

// ── Pivot ─────────────────────────────────────────────────────────────────────
export interface PivotResult {
  index: string;
  columns: string;
  values: string;
  agg_func: string;
  data: Record<string, unknown>[];
  shape: [number, number];
}

// ── Reports ───────────────────────────────────────────────────────────────────
export interface Report {
  report_id: string;
  product_id: string;
  report_type: string;
  template: string;
  status: string;
  file_path: string | null;
  generated_at: string;
}

// ── Health ────────────────────────────────────────────────────────────────────
export interface HealthStatus {
  status: string;
  version: string;
  environment: string;
  services: Record<string, string>;
}

// ── Filters ───────────────────────────────────────────────────────────────────
export interface DataFilters {
  productId: string;
  dateFrom?: string;
  dateTo?: string;
  testIds?: string[];
  batchIds?: string[];
  status?: string;
}
