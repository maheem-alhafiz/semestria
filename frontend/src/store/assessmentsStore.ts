import { create } from "zustand";
import { startOfWeek } from "date-fns";

import {
  addAssessmentCourse,
  createAssessment,
  createTodo,
  createTopic,
  deleteAssessment,
  deleteTodo,
  deleteTopic,
  getAssessmentCourses,
  getAssessments,
  getGradeScales,
  getTodos,
  getTopics,
  removeAssessmentCourse,
  setGradeScale,
  updateAssessment,
  updateTodo,
  updateTopic,
} from "@/lib/api";
import type {
  AssessmentCourseRead,
  AssessmentCreate,
  AssessmentRead,
  AssessmentUpdate,
  GradeScaleCutoffItem,
  Term,
  TodoCreate,
  TodoRead,
  TodoUpdate,
  TopicEntryCreate,
  TopicEntryRead,
  TopicEntryUpdate,
} from "@/types/api";

function isoDate(d: Date): string {
  // YYYY-MM-DD in LOCAL time, not UTC -- date-fns's default toISOString()
  // equivalent would shift near midnight for negative-UTC-offset users.
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

interface AssessmentsState {
  term: Term | null;
  viewedWeekStart: string; // Monday, YYYY-MM-DD

  courses: AssessmentCourseRead[];
  assessments: AssessmentRead[];
  topics: TopicEntryRead[];
  todos: TodoRead[];
  // Maps course_id to its specific grade scale
  gradeScales: Record<number, GradeScaleCutoffItem[]>;

  isLoading: boolean;
  error: string | null;

  setTerm: (term: Term) => void;
  goToNextWeek: () => void;
  goToPrevWeek: () => void;
  goToWeekOf: (date: Date) => void;

  loadAll: (termCode: string) => Promise<void>;
  loadGradeScales: () => Promise<void>;
  saveGradeScale: (courseId: number, cutoffs: GradeScaleCutoffItem[]) => Promise<void>;

  addCourse: (courseId: number) => Promise<void>;
  removeCourse: (courseId: number) => Promise<void>;

  addAssessment: (payload: AssessmentCreate) => Promise<void>;
  editAssessment: (id: number, payload: AssessmentUpdate) => Promise<void>;
  removeAssessment: (id: number) => Promise<void>;

  addTopic: (payload: TopicEntryCreate) => Promise<void>;
  editTopic: (id: number, payload: TopicEntryUpdate) => Promise<void>;
  removeTopic: (id: number) => Promise<void>;

  addTodo: (payload: TodoCreate) => Promise<void>;
  editTodo: (id: number, payload: TodoUpdate) => Promise<void>;
  removeTodo: (id: number) => Promise<void>;
}

export const useAssessmentsStore = create<AssessmentsState>((set, get) => ({
  term: null,
  viewedWeekStart: isoDate(startOfWeek(new Date(), { weekStartsOn: 1 })),

  courses: [],
  assessments: [],
  topics: [],
  todos: [],
  gradeScales: {},

  isLoading: false,
  error: null,

  setTerm: (term) => {
    // Jump the visible week to the term's actual start (Monday of that
    // week) so switching terms doesn't leave you staring at whatever week
    // the previous term happened to be on. Falls back to today's week if
    // this term has no derived start_date yet (see Term's backend
    // docstring on when that's null).
    const anchor = term.start_date ? new Date(`${term.start_date}T00:00:00`) : new Date();
    set({ term, viewedWeekStart: isoDate(startOfWeek(anchor, { weekStartsOn: 1 })) });
    get().loadAll(term.term_code);
  },

  goToNextWeek: () => {
    const current = new Date(`${get().viewedWeekStart}T00:00:00`);
    current.setDate(current.getDate() + 7);
    set({ viewedWeekStart: isoDate(current) });
  },

  goToPrevWeek: () => {
    const current = new Date(`${get().viewedWeekStart}T00:00:00`);
    current.setDate(current.getDate() - 7);
    set({ viewedWeekStart: isoDate(current) });
  },

  goToWeekOf: (date) => {
    set({ viewedWeekStart: isoDate(startOfWeek(date, { weekStartsOn: 1 })) });
  },

  loadAll: async (termCode) => {
    set({ isLoading: true, error: null });
    try {
      const [courses, assessments, topics, todos] = await Promise.all([
        getAssessmentCourses(termCode),
        getAssessments(termCode),
        getTopics(termCode),
        getTodos(termCode),
      ]);
      set({ courses, assessments, topics, todos, isLoading: false });
    } catch (err: any) {
      set({ error: err.message || "Failed to load assessments.", isLoading: false });
    }
  },

  loadGradeScales: async () => {
    try {
      const scales = await getGradeScales();
      const map: Record<number, GradeScaleCutoffItem[]> = {};
      for (const s of scales) {
        map[s.course_id] = s.cutoffs;
      }
      set({ gradeScales: map });
    } catch {
      // Non-fatal -- course cards just won't show a predicted letter/GPA.
    }
  },

  saveGradeScale: async (courseId, cutoffs) => {
    const updated = await setGradeScale(courseId, cutoffs);
    set((state) => ({
      gradeScales: { ...state.gradeScales, [courseId]: updated.cutoffs },
    }));
  },

  addCourse: async (courseId) => {
    const term = get().term;
    if (!term) return;
    const course = await addAssessmentCourse({ term_code: term.term_code, course_id: courseId });
    set((s) => ({
      courses: [...s.courses, course].sort(
        (a, b) => a.subject.localeCompare(b.subject) || a.course_number.localeCompare(b.course_number)
      ),
    }));
  },

  removeCourse: async (courseId) => {
    const term = get().term;
    if (!term) return;
    await removeAssessmentCourse(term.term_code, courseId);
    set((s) => ({ courses: s.courses.filter((c) => c.course_id !== courseId) }));
  },

  addAssessment: async (payload) => {
    const created = await createAssessment(payload);
    set((s) => ({ assessments: [...s.assessments, created] }));
  },

  editAssessment: async (id, payload) => {
    const updated = await updateAssessment(id, payload);
    set((s) => ({ assessments: s.assessments.map((a) => (a.id === id ? updated : a)) }));
  },

  removeAssessment: async (id) => {
    await deleteAssessment(id);
    set((s) => ({ assessments: s.assessments.filter((a) => a.id !== id) }));
  },

  addTopic: async (payload) => {
    const created = await createTopic(payload);
    set((s) => ({ topics: [...s.topics, created] }));
  },

  editTopic: async (id, payload) => {
    const updated = await updateTopic(id, payload);
    set((s) => ({ topics: s.topics.map((t) => (t.id === id ? updated : t)) }));
  },

  removeTopic: async (id) => {
    await deleteTopic(id);
    set((s) => ({ topics: s.topics.filter((t) => t.id !== id) }));
  },

  addTodo: async (payload) => {
    const created = await createTodo(payload);
    set((s) => ({ todos: [...s.todos, created] }));
  },

  editTodo: async (id, payload) => {
    const updated = await updateTodo(id, payload);
    set((s) => ({ todos: s.todos.map((t) => (t.id === id ? updated : t)) }));
  },

  removeTodo: async (id) => {
    await deleteTodo(id);
    set((s) => ({ todos: s.todos.filter((t) => t.id !== id) }));
  },
}));