import type {
  Course,
  CourseDetailRead,
  CourseSections,
  AcademicRecordCreate,
  AcademicRecordUpdate,
  AcademicRecordRead,
  DegreeProgramProgressRead,
  DegreeProgramSummary,
  PlanCreate,
  PlanFinalizeResponse,
  PlanItemsReplace,
  PlanRead,
  PlanShareResponse,
  PlanSummary,
  PlanUpdate,
  ScheduleGenerateRequest,
  ScheduleGenerateResponse,
  Term,
  ManualFulfillmentCreate,
  ManualFulfillmentRead,
  AssessmentRead,
  AssessmentCreate,
  AssessmentUpdate,
  TopicEntryRead,
  TopicEntryCreate,
  TopicEntryUpdate,
  TodoRead,
  TodoCreate,
  TodoUpdate,
  GradeScaleCutoffItem,
  AssessmentCourseRead,
  TrackedCourseCreate,
} from "@/types/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      // REQUIRED for the anonymous visitor_id cookie (see
      // app.core.visitor on the backend) to actually round-trip.
      // Without this, fetch() silently drops cookies on cross-origin
      // requests (frontend on one port, backend on another counts as
      // cross-origin even both on localhost) -- every request would
      // look like a brand-new visitor with no plans/history.
      credentials: "include",
      ...options,
    });
  } catch {
    throw new ApiError(0, "Couldn't reach the API. Is the backend running?");
  }

  if (!response.ok) {
    // FastAPI validation errors come back as {"detail": [...] | "..."}
    const body = await response.json().catch(() => null);
    const message =
      body && typeof body.detail === "string"
        ? body.detail
        : body?.detail
          ? JSON.stringify(body.detail)
          : `Request failed with status ${response.status}`;
    throw new ApiError(response.status, message);
  }

  // DELETE endpoints (e.g. /plans/{id}) return 204 No Content -- calling
  // .json() on an empty body throws, so short-circuit before that.
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function getTerms(): Promise<Term[]> {
  return apiFetch<Term[]>("/terms");
}

export function searchCourses(termCode: string, query: string): Promise<Course[]> {
  const params = new URLSearchParams({ term_code: termCode });
  if (query.trim()) params.set("q", query.trim());
  return apiFetch<Course[]>(`/courses?${params.toString()}`);
}

// Grouped sections for one course in one term -- see types/api.ts's
// CourseSections for the shape (groups -> slots -> options), which
// mirrors app.models.section.Section's link_group_id/link_slot columns.
export function getCourseSections(courseId: number, termCode: string): Promise<CourseSections> {
  const params = new URLSearchParams({ term_code: termCode });
  return apiFetch<CourseSections>(`/courses/${courseId}/sections?${params.toString()}`);
}

export function generateSchedules(
  payload: ScheduleGenerateRequest,
): Promise<ScheduleGenerateResponse> {
  return apiFetch<ScheduleGenerateResponse>("/schedules/generate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// -- Plans (Planner tab) --------------------------------------------------

export function createPlan(payload: PlanCreate): Promise<PlanRead> {
  return apiFetch<PlanRead>("/plans", { method: "POST", body: JSON.stringify(payload) });
}

export function listPlans(): Promise<PlanSummary[]> {
  return apiFetch<PlanSummary[]>("/plans");
}

export function getPlan(planId: number): Promise<PlanRead> {
  return apiFetch<PlanRead>(`/plans/${planId}`);
}

export function updatePlan(planId: number, payload: PlanUpdate): Promise<PlanRead> {
  return apiFetch<PlanRead>(`/plans/${planId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deletePlan(planId: number): Promise<void> {
  return apiFetch<void>(`/plans/${planId}`, { method: "DELETE" });
}

// Wholesale-replaces a plan's course selections -- see PlanItemsReplace's
// doc comment in types/api.ts. This is what "Save" in the Planner tab
// calls.
export function savePlanItems(planId: number, payload: PlanItemsReplace): Promise<PlanRead> {
  return apiFetch<PlanRead>(`/plans/${planId}/items`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function finalizePlan(planId: number): Promise<PlanFinalizeResponse> {
  return apiFetch<PlanFinalizeResponse>(`/plans/${planId}/finalize`, { method: "POST" });
}

export function sharePlan(planId: number): Promise<PlanShareResponse> {
  return apiFetch<PlanShareResponse>(`/plans/${planId}/share`, { method: "POST" });
}

export function getSharedPlan(token: string): Promise<PlanRead> {
  return apiFetch<PlanRead>(`/plans/shared/${token}`);
}

// -- Academic Record (Degree Tracker) -------------------------------------

export function getAcademicRecord(): Promise<AcademicRecordRead[]> {
  return apiFetch<AcademicRecordRead[]>("/academic-record");
}

export function addPastCourse(payload: AcademicRecordCreate): Promise<AcademicRecordRead> {
  return apiFetch<AcademicRecordRead>("/academic-record", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAcademicRecord(
  recordId: number,
  payload: AcademicRecordUpdate,
): Promise<AcademicRecordRead> {
  return apiFetch<AcademicRecordRead>(`/academic-record/${recordId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAcademicRecord(recordId: number): Promise<void> {
  return apiFetch<void>(`/academic-record/${recordId}`, { method: "DELETE" });
}

// -- Degree Programs (Degree Tracker requirements) ------------------------

export function getCourseDetail(courseId: number): Promise<CourseDetailRead> {
  return apiFetch<CourseDetailRead>(`/courses/${courseId}`);
}

export function getDegreePrograms(): Promise<DegreeProgramSummary[]> {
  return apiFetch<DegreeProgramSummary[]>("/degree-programs");
}

export function getDegreeProgramProgress(programId: number): Promise<DegreeProgramProgressRead> {
  return apiFetch<DegreeProgramProgressRead>(`/degree-programs/${programId}/progress`);
}

// --- Add to src/lib/api.ts (imports: add ManualFulfillmentCreate, ManualFulfillmentRead to the type import block) ---

export function createManualFulfillment(
  payload: ManualFulfillmentCreate,
): Promise<ManualFulfillmentRead> {
  return apiFetch<ManualFulfillmentRead>("/manual-fulfillments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteManualFulfillment(fulfillmentId: number): Promise<void> {
  return apiFetch<void>(`/manual-fulfillments/${fulfillmentId}`, { method: "DELETE" });
}


// -- Assessments tab -----------------------------------------------------

export function getAssessmentCourses(termCode: string): Promise<AssessmentCourseRead[]> {
  const params = new URLSearchParams({ term_code: termCode });
  return apiFetch<AssessmentCourseRead[]>(`/assessments/courses?${params}`);
}

export function addAssessmentCourse(
  payload: TrackedCourseCreate
): Promise<AssessmentCourseRead> {
  return apiFetch<AssessmentCourseRead>("/assessments/courses", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function removeAssessmentCourse(termCode: string, courseId: number): Promise<void> {
  return apiFetch<void>(`/assessments/courses/${termCode}/${courseId}`, { method: "DELETE" });
}

export function getAssessments(termCode: string): Promise<AssessmentRead[]> {
  const params = new URLSearchParams({ term_code: termCode });
  return apiFetch<AssessmentRead[]>(`/assessments?${params}`);
}

export function createAssessment(payload: AssessmentCreate): Promise<AssessmentRead> {
  return apiFetch<AssessmentRead>("/assessments", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateAssessment(
  assessmentId: number,
  payload: AssessmentUpdate
): Promise<AssessmentRead> {
  return apiFetch<AssessmentRead>(`/assessments/${assessmentId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteAssessment(assessmentId: number): Promise<void> {
  return apiFetch<void>(`/assessments/${assessmentId}`, { method: "DELETE" });
}

// -- Topics log ------------------------------------------------------------

export function getTopics(termCode: string): Promise<TopicEntryRead[]> {
  const params = new URLSearchParams({ term_code: termCode });
  return apiFetch<TopicEntryRead[]>(`/assessments/topics?${params}`);
}

export function createTopic(payload: TopicEntryCreate): Promise<TopicEntryRead> {
  return apiFetch<TopicEntryRead>("/assessments/topics", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTopic(topicId: number, payload: TopicEntryUpdate): Promise<TopicEntryRead> {
  return apiFetch<TopicEntryRead>(`/assessments/topics/${topicId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteTopic(topicId: number): Promise<void> {
  return apiFetch<void>(`/assessments/topics/${topicId}`, { method: "DELETE" });
}

// -- To-dos ------------------------------------------------------------

export function getTodos(termCode: string): Promise<TodoRead[]> {
  const params = new URLSearchParams({ term_code: termCode });
  return apiFetch<TodoRead[]>(`/assessments/todos?${params}`);
}

export function createTodo(payload: TodoCreate): Promise<TodoRead> {
  return apiFetch<TodoRead>("/assessments/todos", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateTodo(todoId: number, payload: TodoUpdate): Promise<TodoRead> {
  return apiFetch<TodoRead>(`/assessments/todos/${todoId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteTodo(todoId: number): Promise<void> {
  return apiFetch<void>(`/assessments/todos/${todoId}`, { method: "DELETE" });
}

// -- Grade scale (personal percent-to-letter cutoffs) ----------------------

export function getGradeScale(): Promise<GradeScaleCutoffItem[]> {
  return apiFetch<GradeScaleCutoffItem[]>("/assessments/grade-scale");
}

export function setGradeScale(cutoffs: GradeScaleCutoffItem[]): Promise<GradeScaleCutoffItem[]> {
  return apiFetch<GradeScaleCutoffItem[]>("/assessments/grade-scale", {
    method: "PUT",
    body: JSON.stringify({ cutoffs }),
  });
}

export { ApiError };
