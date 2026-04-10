import { create } from "zustand";
import type { DataFilters } from "@/lib/types";
import { subDays, formatISO } from "date-fns";

interface FilterState extends DataFilters {
  setProductId: (id: string) => void;
  setDateFrom: (d: string) => void;
  setDateTo: (d: string) => void;
  setStatus: (s: string | undefined) => void;
  setTestIds: (ids: string[]) => void;
  reset: () => void;
}

const defaults: DataFilters = {
  productId: "soc_a8",
  dateFrom: formatISO(subDays(new Date(), 30), { representation: "date" }),
  dateTo: formatISO(new Date(), { representation: "date" }),
};

export const useFilterStore = create<FilterState>((set) => ({
  ...defaults,
  setProductId: (productId) => set({ productId }),
  setDateFrom: (dateFrom) => set({ dateFrom }),
  setDateTo: (dateTo) => set({ dateTo }),
  setStatus: (status) => set({ status }),
  setTestIds: (testIds) => set({ testIds }),
  reset: () => set(defaults),
}));
