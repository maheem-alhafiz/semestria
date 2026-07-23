import { create } from "zustand";

import type { Course, CourseSections, Schedule } from "@/types/api";

// Key format for a single required slot within a course, unique across
// that course's groups: `${link_group_id ?? "solo"}:${link_slot}`.
// Built the same way in both the store and the picker component -- see
// CourseGroupPicker.tsx.
type SlotKey = string;

interface PlannerState {
  termCode: string | null;
  searchResults: Course[];
  selectedCourses: Course[];
  schedules: Schedule[];

  // Cache of GET /courses/{id}/sections responses, keyed by course_id.
  // Populated lazily by CourseGroupPicker the first time a course is
  // expanded -- avoids re-fetching every render, and avoids fetching for
  // courses the student never opens the picker for.
  courseSections: Record<number, CourseSections>;

  // The student's chosen CRN for each required slot of each selected
  // course: selectedCourses -> course_id -> SlotKey -> crn. A slot with
  // only one option doesn't strictly need an entry here (it has nothing
  // to choose), but picker components may still write the default so the
  // schedule-generation step always has an explicit answer to read.
  sectionChoices: Record<number, Record<SlotKey, string>>;

  isSearching: boolean;
  isGenerating: boolean;
  error: string | null;

  setTermCode: (termCode: string) => void;
  setSearchResults: (courses: Course[]) => void;
  setIsSearching: (value: boolean) => void;
  addCourse: (course: Course) => void;
  removeCourse: (courseId: number) => void;
  setCourseSections: (courseId: number, sections: CourseSections) => void;
  setSectionChoice: (courseId: number, slotKey: SlotKey, crn: string) => void;
  setSchedules: (schedules: Schedule[]) => void;
  setIsGenerating: (value: boolean) => void;
  setError: (message: string | null) => void;
}

export const usePlannerStore = create<PlannerState>((set) => ({
  termCode: null,
  searchResults: [],
  selectedCourses: [],
  schedules: [],
  courseSections: {},
  sectionChoices: {},

  isSearching: false,
  isGenerating: false,
  error: null,

  // Switching terms invalidates everything downstream: last term's search
  // results, selections, schedules, cached section groups, and choices
  // don't mean anything in a new term (courseSections/sectionChoices are
  // keyed by course_id alone, and the same course_id in a different term
  // can have entirely different sections/CRNs).
  setTermCode: (termCode) =>
    set({
      termCode,
      searchResults: [],
      selectedCourses: [],
      schedules: [],
      courseSections: {},
      sectionChoices: {},
    }),

  setSearchResults: (searchResults) => set({ searchResults }),
  setIsSearching: (isSearching) => set({ isSearching }),

  addCourse: (course) =>
    set((state) =>
      state.selectedCourses.some((c) => c.course_id === course.course_id)
        ? state
        : { selectedCourses: [...state.selectedCourses, course], schedules: [] },
    ),

  removeCourse: (courseId) =>
    set((state) => {
      const { [courseId]: _removedChoices, ...restChoices } = state.sectionChoices;
      return {
        selectedCourses: state.selectedCourses.filter((c) => c.course_id !== courseId),
        sectionChoices: restChoices,
        schedules: [], // stale once the selection changes
      };
    }),

  setCourseSections: (courseId, sections) =>
    set((state) => ({
      courseSections: { ...state.courseSections, [courseId]: sections },
    })),

  setSectionChoice: (courseId, slotKey, crn) =>
    set((state) => ({
      sectionChoices: {
        ...state.sectionChoices,
        [courseId]: { ...state.sectionChoices[courseId], [slotKey]: crn },
      },
      schedules: [], // stale once a pick changes
    })),

  setSchedules: (schedules) => set({ schedules }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setError: (error) => set({ error }),
}));
