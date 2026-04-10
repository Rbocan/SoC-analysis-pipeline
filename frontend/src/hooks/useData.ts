"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { dataApi, productsApi, reportsApi, syntheticApi } from "@/lib/api";
import type { DataFilters } from "@/lib/types";

export function useProducts() {
  return useQuery({
    queryKey: ["products"],
    queryFn: () => productsApi.list().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useProduct(id: string) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: () => productsApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMetrics(productId: string, dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["metrics", productId, dateFrom, dateTo],
    queryFn: () => dataApi.metrics(productId, dateFrom, dateTo).then((r) => r.data),
    enabled: !!productId,
    refetchInterval: 60_000,
  });
}

export function useTrend(productId: string, metric: string, period = "day", dateFrom?: string, dateTo?: string) {
  return useQuery({
    queryKey: ["trend", productId, metric, period, dateFrom, dateTo],
    queryFn: () => dataApi.trend(productId, metric, period, dateFrom, dateTo).then((r) => r.data),
    enabled: !!productId && !!metric,
  });
}

export function useDataQuery(filters: DataFilters & { limit?: number; offset?: number }) {
  return useQuery({
    queryKey: ["data", filters],
    queryFn: () =>
      dataApi
        .query({
          product_id: filters.productId,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          test_ids: filters.testIds,
          batch_ids: filters.batchIds,
          status: filters.status,
          limit: filters.limit ?? 100,
          offset: filters.offset ?? 0,
        })
        .then((r) => r.data),
    enabled: !!filters.productId,
  });
}

export function usePivot(params: {
  product_id: string;
  index: string;
  columns: string;
  values: string;
  agg_func: string;
  date_from?: string;
  date_to?: string;
}) {
  return useQuery({
    queryKey: ["pivot", params],
    queryFn: () => dataApi.pivot(params).then((r) => r.data),
    enabled: !!params.product_id,
  });
}

export function useAnomalies(productId: string, metric: string) {
  return useQuery({
    queryKey: ["anomalies", productId, metric],
    queryFn: () => dataApi.anomalies(productId, metric).then((r) => r.data),
    enabled: !!productId,
  });
}

export function useReportHistory(productId?: string) {
  return useQuery({
    queryKey: ["reports", productId],
    queryFn: () => reportsApi.history(productId).then((r) => r.data),
  });
}

export function useGenerateReport() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: Record<string, unknown>) => reportsApi.generate(params).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  });
}

export function useGenerateSynthetic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (params: Record<string, unknown>) => syntheticApi.generate(params).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["metrics"] });
      qc.invalidateQueries({ queryKey: ["data"] });
    },
  });
}
