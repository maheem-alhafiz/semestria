import type {
  Course,
  CourseSections,
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

export { ApiError };
