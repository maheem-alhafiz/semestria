import { create } from "zustand";
import { persist } from "zustand/middleware";

import type { Course, CourseSections, PlanRead } from "@/types/api";

type Slot = "top" | "bottom";

interface CourseSelectionState {
  activeTop: boolean;
  activeBottom: boolean;
  topEnabled: boolean;
  bottomEnabled: boolean;
  topSectionChoices: Record<string, string>;
  bottomSectionChoices: Record<string, string>;
  // "This course is being taken via its distance/online section" --
  // per-slot, matching everything else here (a course could plausibly
  // be in-person in one term and distance in the other). See
  // lib/distanceSections.ts for how a group is classified as distance.
  topDistanceMode: boolean;
  bottomDistanceMode: boolean;
}

function emptySelection(): CourseSelectionState {
  return {
    activeTop: false,
    activeBottom: false,
    topEnabled: true,
    bottomEnabled: true,
    topSectionChoices: {},
    bottomSectionChoices: {},
    topDistanceMode: false,
    bottomDistanceMode: false,
  };
}

interface PlannerBuilderState {
  topTermCode: string | null;
  bottomTermCode: string | null;

  searchQuery: string;
  isSearching: boolean;
  searchResults: Course[];

  knownCourses: Record<number, Course>;

  selections: Record<number, CourseSelectionState>;

  courseSectionsCache: Record<string, CourseSections>;

  currentPlanId: number | null;
  planName: string;
  isSaving: boolean;
  error: string | null;

  setTopTerm: (termCode: string | null) => void;
  setBottomTerm: (termCode: string | null) => void;
  setSearchQuery: (query: string) => void;
  setIsSearching: (value: boolean) => void;
  setSearchResults: (courses: Course[]) => void;
  toggleCourseSlot: (course: Course, slot: Slot) => void;
  toggleCourseEnabled: (courseId: number, slot: Slot) => void;
  removeCourseEntirely: (courseId: number) => void;
  setCourseSections: (courseId: number, termCode: string, data: CourseSections) => void;
  setSectionChoice: (courseId: number, slot: Slot, slotKey: string, crn: string) => void;
  setDistanceMode: (courseId: number, slot: Slot, value: boolean) => void;
  setPlanName: (name: string) => void;
  setIsSaving: (value: boolean) => void;
  setError: (message: string | null) => void;
  loadPlan: (plan: PlanRead, coursesById: Record<number, Course>) => void;
  resetPlanner: () => void;
}

const initialState = {
  topTermCode: null as string | null,
  bottomTermCode: null as string | null,
  searchQuery: "",
  isSearching: false,
  searchResults: [] as Course[],
  knownCourses: {} as Record<number, Course>,
  selections: {} as Record<number, CourseSelectionState>,
  courseSectionsCache: {} as Record<string, CourseSections>,
  currentPlanId: null as number | null,
  planName: "Untitled Plan",
  isSaving: false,
  error: null as string | null,
};

export const usePlannerBuilderStore = create<PlannerBuilderState>()(
  persist(
    (set) => ({
      ...initialState,

      setTopTerm: (termCode) =>
        set((state) => ({
          topTermCode: termCode,
          selections: Object.fromEntries(
            Object.entries(state.selections).map(([id, sel]) => [
              id,
              { ...sel, activeTop: false, topSectionChoices: {}, topDistanceMode: false },
            ]),
          ),
        })),

      setBottomTerm: (termCode) =>
        set((state) => ({
          bottomTermCode: termCode,
          selections: Object.fromEntries(
            Object.entries(state.selections).map(([id, sel]) => [
              id,
              { ...sel, activeBottom: false, bottomSectionChoices: {}, bottomDistanceMode: false },
            ]),
          ),
        })),

      setSearchQuery: (searchQuery) => set({ searchQuery }),
      setIsSearching: (isSearching) => set({ isSearching }),

      setSearchResults: (courses) =>
        set((state) => ({
          searchResults: courses,
          knownCourses: {
            ...state.knownCourses,
            ...Object.fromEntries(courses.map((c) => [c.course_id, c])),
          },
        })),

      toggleCourseSlot: (course, slot) =>
        set((state) => {
          const existing = state.selections[course.course_id] ?? emptySelection();
          const key = slot === "top" ? "activeTop" : "activeBottom";
          const choicesKey = slot === "top" ? "topSectionChoices" : "bottomSectionChoices";
          const distanceKey = slot === "top" ? "topDistanceMode" : "bottomDistanceMode";
          const turningOn = !existing[key];
          return {
            knownCourses: { ...state.knownCourses, [course.course_id]: course },
            selections: {
              ...state.selections,
              [course.course_id]: {
                ...existing,
                [key]: turningOn,
                ...(turningOn ? {} : { [choicesKey]: {}, [distanceKey]: false }),
              },
            },
          };
        }),

      toggleCourseEnabled: (courseId, slot) =>
        set((state) => {
          const existing = state.selections[courseId];
          if (!existing) return state;
          const key = slot === "top" ? "topEnabled" : "bottomEnabled";
          return {
            selections: {
              ...state.selections,
              [courseId]: { ...existing, [key]: !existing[key] },
            },
          };
        }),

      removeCourseEntirely: (courseId) =>
        set((state) => {
          const { [courseId]: _removed, ...rest } = state.selections;
          return { selections: rest };
        }),

      setCourseSections: (courseId, termCode, data) =>
        set((state) => ({
          courseSectionsCache: { ...state.courseSectionsCache, [`${courseId}:${termCode}`]: data },
        })),

      setSectionChoice: (courseId, slot, slotKey, crn) =>
        set((state) => {
          const existing = state.selections[courseId] ?? emptySelection();
          const choicesKey = slot === "top" ? "topSectionChoices" : "bottomSectionChoices";
          return {
            selections: {
              ...state.selections,
              [courseId]: {
                ...existing,
                [choicesKey]: { ...existing[choicesKey], [slotKey]: crn },
              },
            },
          };
        }),

      // Switching a course's distance mode clears that slot's section
      // choices -- the previously-picked lecture/lab CRNs (or previously
      // picked distance CRN) belong to the OTHER mode's group set and
      // would otherwise linger as orphaned, invisible store entries.
      setDistanceMode: (courseId, slot, value) =>
        set((state) => {
          const existing = state.selections[courseId] ?? emptySelection();
          const distanceKey = slot === "top" ? "topDistanceMode" : "bottomDistanceMode";
          const choicesKey = slot === "top" ? "topSectionChoices" : "bottomSectionChoices";
          return {
            selections: {
              ...state.selections,
              [courseId]: {
                ...existing,
                [distanceKey]: value,
                [choicesKey]: {},
              },
            },
          };
        }),

      setPlanName: (planName) => set({ planName }),
      setIsSaving: (isSaving) => set({ isSaving }),
      setError: (error) => set({ error }),

      // Populates the entire planner from a fetched Plan (the "Load"
      // button on the Plans list page) -- reconstructs slot activation
      // and section choices from PlanItem/PlanItemSection rows.
      // `coursesById` must already contain every course_id referenced in
      // `plan.items` (the caller fetches/joins course details first).
      //
      // KNOWN LIMITATION: PlanItemSection only stores link_slot, not
      // link_group_id, so this can't perfectly reconstruct the
      // `${link_group_id}:${link_slot}` key format used elsewhere. Works
      // correctly for every course with at most one link_group per term;
      // could restore the wrong group's option if a course ever has two
      // link_groups sharing an identically-named slot. Distance mode is
      // NOT restored here either -- a reloaded plan defaults back to
      // in-person mode even if it was originally saved in distance mode;
      // acceptable for now since re-toggling is a one-click fix, but
      // worth revisiting if this turns out to matter in practice.
      loadPlan: (plan, coursesById) => {
        const selections: Record<number, CourseSelectionState> = {};
        const knownCourses: Record<number, Course> = {};

        for (const item of plan.items) {
          const course = coursesById[item.course_id];
          if (!course) continue;
          knownCourses[item.course_id] = course;

          const isTop = item.term_code === plan.top_term_code;
          const isBottom = item.term_code === plan.bottom_term_code;
          const choices = Object.fromEntries(
            item.chosen_sections.map((s) => [`${s.link_slot ?? "solo"}`, s.crn] as const),
          );

          const existing = selections[item.course_id] ?? emptySelection();
          selections[item.course_id] = {
            ...existing,
            activeTop: existing.activeTop || isTop,
            activeBottom: existing.activeBottom || isBottom,
            topSectionChoices: isTop ? choices : existing.topSectionChoices,
            bottomSectionChoices: isBottom ? choices : existing.bottomSectionChoices,
          };
        }

        set({
          currentPlanId: plan.id,
          planName: plan.name,
          topTermCode: plan.top_term_code,
          bottomTermCode: plan.bottom_term_code,
          selections,
          knownCourses,
          searchResults: [],
          courseSectionsCache: {},
          error: null,
        });
      },

      resetPlanner: () => set({ ...initialState }),
    }),
    {
      name: "planner-builder-storage",
      // Transient UI flags and the last search's results shouldn't
      // survive a refresh -- only the actual "plan in progress" data is
      // worth restoring, so a closed laptop doesn't mean starting over.
      //partialize: (state) => ({
        //topTermCode: state.topTermCode,
        //bottomTermCode: state.bottomTermCode,
        //knownCourses: state.knownCourses,
        //selections: state.selections,
        //courseSectionsCache: state.courseSectionsCache,
        //currentPlanId: state.currentPlanId,
        //planName: state.planName,
      //}),
      partialize: (state) => ({
        topTermCode: state.topTermCode,
        bottomTermCode: state.bottomTermCode,
        knownCourses: state.knownCourses,
        selections: state.selections,
        // Removed courseSectionsCache so the UI always fetches fresh section data on reload
        currentPlanId: state.currentPlanId,
        planName: state.planName,
      }),
    },
  ),
);
