import { create } from "zustand";
import { getAcademicRecord } from "@/lib/api";
import type { AcademicRecordRead } from "@/types/api";
interface TrackerState {
  records: AcademicRecordRead[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  fetchRecords: () => Promise<void>;
}

export const useTrackerStore = create<TrackerState>((set) => ({
  records: [],
  isLoading: false,
  error: null,

  fetchRecords: async () => {
    set({ isLoading: true, error: null });
    try {
      // This hits the backend endpoint we confirmed earlier
      const data = await getAcademicRecord();
      set({ records: data, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || "Failed to fetch academic record", isLoading: false });
    }
  },
}));