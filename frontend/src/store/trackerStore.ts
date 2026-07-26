import { create } from "zustand";
import { getAcademicRecord, getDegreePrograms, getDegreeProgramProgress } from "@/lib/api";
import type { AcademicRecordRead, DegreeProgramProgressRead, DegreeProgramSummary } from "@/types/api";

interface TrackerState {
  records: AcademicRecordRead[];
  isLoading: boolean;
  error: string | null;

  programs: DegreeProgramSummary[];
  selectedProgramId: number | null;
  programProgress: DegreeProgramProgressRead | null;
  isLoadingPrograms: boolean;
  isLoadingProgress: boolean;
  programsError: string | null;
  progressError: string | null;

  // Actions
  fetchRecords: () => Promise<void>;
  fetchPrograms: () => Promise<void>;
  fetchProgramProgress: (programId: number) => Promise<void>;
  selectProgram: (programId: number) => void;
}

export const useTrackerStore = create<TrackerState>((set, get) => ({
  records: [],
  isLoading: false,
  error: null,

  programs: [],
  selectedProgramId: null,
  programProgress: null,
  isLoadingPrograms: false,
  isLoadingProgress: false,
  programsError: null,
  progressError: null,

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

  fetchPrograms: async () => {
    set({ isLoadingPrograms: true, programsError: null });
    try {
      const data = await getDegreePrograms();
      set({ programs: data, isLoadingPrograms: false });

      // Auto-select the first program on initial load so the sidebar
      // isn't left empty -- only when nothing's been picked yet, so this
      // never clobbers a selection the user already made.
      const { selectedProgramId } = get();
      if (selectedProgramId === null && data.length > 0) {
        get().selectProgram(data[0].id);
      }
    } catch (err: any) {
      set({ programsError: err.message || "Failed to fetch degree programs", isLoadingPrograms: false });
    }
  },

  fetchProgramProgress: async (programId: number) => {
    set({ isLoadingProgress: true, progressError: null });
    try {
      const data = await getDegreeProgramProgress(programId);
      set({ programProgress: data, isLoadingProgress: false });
    } catch (err: any) {
      set({
        progressError: err.message || "Failed to fetch degree program progress",
        isLoadingProgress: false,
      });
    }
  },

  selectProgram: (programId: number) => {
    set({ selectedProgramId: programId });
    get().fetchProgramProgress(programId);
  },
}));
