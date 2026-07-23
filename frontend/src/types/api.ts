// Mirrors backend/app/schemas exactly -- keep these in sync if the API changes.

export interface Term {
  term_code: string;
  description: string;
}

export interface Course {
  course_id: number;
  subject: string;
  course_number: string;
  title: string;
  credit_hours: number;
}

export interface CourseBrief {
  subject: string;
  course_number: string;
  title: string;
}

// start_time/end_time are "HH:MM:SS" strings (FastAPI's default time
// serialization), or null for an async/TBA meeting with no clock time.
export interface MeetingTime {
  meeting_type: string;
  start_time: string | null;
  end_time: string | null;
  monday: boolean;
  tuesday: boolean;
  wednesday: boolean;
  thursday: boolean;
  friday: boolean;
  saturday: boolean;
  sunday: boolean;
}

export interface Section {
  crn: string;
  section_number: string;
  seats_available: number;
  max_enrollment: number | null;
  enrollment: number | null;
  instructor: string | null;
  course: CourseBrief;
  meeting_times: MeetingTime[];
}

export interface Schedule {
  sections: Section[];
}

export interface ScheduleGenerateResponse {
  schedule_count: number;
  schedules: Schedule[];
}

export interface ScheduleGenerateRequest {
  term_code: string;
  course_ids: number[];
  max_results?: number;
  // Flat list of CRNs the student explicitly picked (e.g. via
  // CourseGroupPicker) -- narrows generation to only schedules containing
  // all of them. Safe to omit/leave empty for courses with nothing to
  // pick (single-section courses, or before the student has opened the
  // picker at all).
  locked_crns?: string[];
}

// -- Grouped sections (GET /courses/{course_id}/sections) --------------
// Mirrors app.schemas.section_groups exactly. See that module's docstring
// for what link_group_id/link_slot mean and where they come from.

// A section option within a slot -- same shape as `Section` above minus
// the `course` back-reference, since it's already nested under one.
export interface SectionOption {
  crn: string;
  section_number: string;
  seats_available: number;
  max_enrollment: number | null;
  enrollment: number | null;
  instructor: string | null;
  meeting_times: MeetingTime[];
}

// One required component within a link group (e.g. "CLAS,TUT" or "LAB").
// More than one option means these are interchangeable alternatives --
// e.g. three lab times a student picks one of.
export interface SectionSlot {
  link_slot: string;
  options: SectionOption[];
}

// One linked bundle of sections that must be satisfied together (e.g. a
// lecture slot + a lab slot). link_group_id is null for a standalone
// section that isn't linked to anything -- it will have exactly one slot
// with exactly one option.
export interface SectionGroup {
  link_group_id: number | null;
  slots: SectionSlot[];
}

export interface CourseSections {
  course_id: number;
  subject: string;
  course_number: string;
  title: string;
  credit_hours: number;
  groups: SectionGroup[];
}

// -- Plans (Planner tab) -------------------------------------------------
// Mirrors app.schemas.plan exactly. See app.models.plan / app.models.plan_item
// for the full reasoning behind this shape.

export interface PlanItemSectionCreate {
  term_code: string;
  crn: string;
  link_slot: string | null;
}

export interface PlanItemSectionRead extends PlanItemSectionCreate {
  id: number;
}

export interface PlanItemCreate {
  term_code: string;
  course_id: number;
  chosen_sections: PlanItemSectionCreate[];
}

export interface PlanItemRead {
  id: number;
  term_code: string;
  course_id: number;
  chosen_sections: PlanItemSectionRead[];
}

export interface PlanSummary {
  id: number;
  name: string;
  is_final: boolean;
  top_term_code: string | null;
  bottom_term_code: string | null;
  updated_at: string;
}

export interface PlanRead extends PlanSummary {
  share_token: string | null;
  created_at: string;
  items: PlanItemRead[];
}

export interface PlanCreate {
  name: string;
  top_term_code?: string | null;
  bottom_term_code?: string | null;
}

export interface PlanUpdate {
  name?: string;
  top_term_code?: string | null;
  bottom_term_code?: string | null;
}

export interface PlanItemsReplace {
  items: PlanItemCreate[];
}

export interface PlanFinalizeResponse {
  plan_id: number;
  upserted_count: number;
  removed_count: number;
}

export interface PlanShareResponse {
  share_token: string;
}
