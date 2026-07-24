"use client";

import { useEffect } from "react";

import { colorForCourse } from "@/components/PlannerCourseCard";
import { isDistanceGroup } from "@/lib/distanceSections";
import { ApiError, getCourseSections } from "@/lib/api";
import { usePlannerBuilderStore } from "@/store/plannerBuilderStore";
import type { Course, SectionOption } from "@/types/api";

const MEETING_TYPE_LABELS: Record<string, string> = {
  CLAS: "Lecture",
  TUT: "Tutorial",
  LAB: "Lab",
  EXAM: "Exam",
  SEM: "Seminar",
  WEB: "Online",
};

function meetingTypeLabel(type: string): string {
  return MEETING_TYPE_LABELS[type] ?? type;
}

const FULL_DAY_NAMES: [key: keyof SectionOption["meeting_times"][number], label: string][] = [
  ["monday", "Mon"],
  ["tuesday", "Tue"],
  ["wednesday", "Wed"],
  ["thursday", "Thu"],
  ["friday", "Fri"],
  ["saturday", "Sat"],
  ["sunday", "Sun"],
];

function formatClockTime(hhmmss: string): string {
  const [hStr, mStr] = hhmmss.split(":");
  const h = Number(hStr);
  const m = Number(mStr);
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmmss;
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${m.toString().padStart(2, "0")}${period}`;
}

function compactOptionSummary(option: SectionOption): string {
  const mt = option.meeting_times[0];
  const days = mt ? FULL_DAY_NAMES.filter(([key]) => mt[key]).map(([, label]) => label) : [];
  const dayPart = days.length > 0 ? days.join("") : "TBA";
  const timePart =
    mt?.start_time && mt?.end_time
      ? `${formatClockTime(mt.start_time)}-${formatClockTime(mt.end_time)}`
      : "no scheduled time";
  return `${option.section_number} · ${dayPart} ${timePart}`;
}

function dropdownOptionLabel(option: SectionOption): string {
  const mt = option.meeting_times[0];
  const type = mt ? meetingTypeLabel(mt.meeting_type) : "";
  const days = mt ? FULL_DAY_NAMES.filter(([key]) => mt[key]).map(([, label]) => label) : [];
  const dayPart = days.length > 0 ? days.join("/") : "TBA";
  const timePart =
    mt?.start_time && mt?.end_time
      ? `${formatClockTime(mt.start_time)}-${formatClockTime(mt.end_time)}`
      : "no scheduled time";
  const instructorPart = option.instructor ? ` · ${option.instructor}` : "";
  return `${option.section_number} ${type} — ${dayPart} ${timePart}${instructorPart} · CRN ${option.crn}`;
}

interface CourseEntryProps {
  course: Course;
  termCode: string;
  slot: "top" | "bottom";
}

function CourseEntry({ course, termCode, slot }: CourseEntryProps) {
  const data = usePlannerBuilderStore(
    (s) => s.courseSectionsCache[`${course.course_id}:${termCode}`],
  );
  const setCourseSections = usePlannerBuilderStore((s) => s.setCourseSections);
  const setSectionChoice = usePlannerBuilderStore((s) => s.setSectionChoice);
  const setDistanceMode = usePlannerBuilderStore((s) => s.setDistanceMode);
  const distanceMode = usePlannerBuilderStore(
    (s) =>
      (slot === "top"
        ? s.selections[course.course_id]?.topDistanceMode
        : s.selections[course.course_id]?.bottomDistanceMode) ?? false,
  );
  const choices = usePlannerBuilderStore(
    (s) =>
      (slot === "top"
        ? s.selections[course.course_id]?.topSectionChoices
        : s.selections[course.course_id]?.bottomSectionChoices) ?? {},
  );
  
  const toggleCourseEnabled = usePlannerBuilderStore((s) => s.toggleCourseEnabled);
  const removeCourseEntirely = usePlannerBuilderStore((s) => s.removeCourseEntirely);
  const enabled = usePlannerBuilderStore((s) => {
    const sel = s.selections[course.course_id];
    return slot === "top" ? (sel?.topEnabled ?? true) : (sel?.bottomEnabled ?? true);
  });
  
  const setError = usePlannerBuilderStore((s) => s.setError);

  useEffect(() => {
    if (data) return;
    let cancelled = false;
    getCourseSections(course.course_id, termCode)
      .then((result) => {
        if (!cancelled) setCourseSections(course.course_id, termCode, result);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Couldn't load sections.");
      });
    return () => {
      cancelled = true;
    };
  }, [course.course_id, termCode, data, setCourseSections, setError]);

  const regularGroups = data ? data.groups.filter((g) => !isDistanceGroup(g)) : [];
  const distanceGroups = data ? data.groups.filter((g) => isDistanceGroup(g)) : [];
  const hasDistanceOption = distanceGroups.length > 0;
  const visibleGroups = distanceMode ? distanceGroups : regularGroups;

  // Seed every visible multi-option slot's default choice into real
  // store state once data loads (or once distanceMode flips) -- a
  // <select> already showing its default value never fires onChange, so
  // without this the store could stay empty even though a section is
  // clearly showing as selected on screen. Only seeds from the currently
  // VISIBLE group set, so switching distance mode doesn't leave stale
  // choices from the other mode sitting around unused.
  useEffect(() => {
    if (!data) return;
    const current = usePlannerBuilderStore.getState().selections[course.course_id];
    const currentChoices =
      (slot === "top" ? current?.topSectionChoices : current?.bottomSectionChoices) ?? {};
    for (const group of visibleGroups) {
      for (const slotDef of group.slots) {
        const key = `${group.link_group_id ?? "solo"}:${slotDef.link_slot}`;
        if (!currentChoices[key] && slotDef.options[0]) {
          setSectionChoice(course.course_id, slot, key, slotDef.options[0].crn);
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, distanceMode, course.course_id, slot, setSectionChoice]);

  const color = colorForCourse(course.course_id);
  const primaryInstructor = visibleGroups[0]?.slots[0]?.options[0]?.instructor ?? null;

  return (
    <div className={`rounded-xl border border-hairline bg-elevated px-3 py-2.5 transition-opacity ${enabled ? "" : "opacity-50"}`}>
      <div className="flex items-start gap-2.5">
        <button
          onClick={() => toggleCourseEnabled(course.course_id, slot)}
          className={`mt-1.5 h-3 w-3 shrink-0 rounded-sm border transition-colors ${
            enabled ? "border-transparent" : "border-muted bg-transparent"
          }`}
          style={enabled ? { backgroundColor: color } : {}}
          aria-label={`Toggle ${course.subject} ${course.course_number} on calendar`}
          title={enabled ? "Hide from calendar" : "Show on calendar"}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline justify-between gap-2">
            <p className="truncate text-sm font-medium text-paper">
              {`${course.subject} ${course.course_number}`}{" "}
              <span className="font-normal text-muted">{course.title}</span>
            </p>
            <span className="shrink-0 text-xs text-muted">{course.credit_hours} CH</span>
          </div>
          {primaryInstructor && <p className="text-xs text-muted">{primaryInstructor}</p>}

          {hasDistanceOption && (
            <button
              onClick={() => setDistanceMode(course.course_id, slot, !distanceMode)}
              className={`mt-1 rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
                distanceMode
                  ? "bg-accent text-canvas"
                  : "bg-panel text-muted hover:text-paper"
              }`}
            >
              Distance {distanceMode && "✓"}
            </button>
          )}

          {!data ? (
            <p className="mt-1 text-xs text-muted">Loading sections…</p>
          ) : (
            <div className="mt-1.5 space-y-1">
              {visibleGroups.map((group) =>
                group.slots.map((slotDef) => {
                  const key = `${group.link_group_id ?? "solo"}:${slotDef.link_slot}`;
                  const hasChoice = slotDef.options.length > 1;
                  const selected = choices[key] ?? slotDef.options[0]?.crn;
                  const label = meetingTypeLabel(
                    slotDef.options[0]?.meeting_times[0]?.meeting_type ?? slotDef.link_slot,
                  );

                  if (!hasChoice) {
                    const option = slotDef.options[0];
                    return (
                      <div
                        key={key}
                        className="rounded-lg border border-hairline bg-panel px-2.5 py-1.5 text-xs text-muted"
                      >
                        {label}: {option ? compactOptionSummary(option) : "—"}
                      </div>
                    );
                  }

                  return (
                    <select
                      key={key}
                      value={selected}
                      onChange={(e) => setSectionChoice(course.course_id, slot, key, e.target.value)}
                      className="w-full rounded-lg border border-hairline bg-panel px-2.5 py-1.5 pr-8 text-xs text-paper focus:outline-none focus:ring-1 focus:ring-accent"
                    >
                      {slotDef.options.map((option) => (
                        <option key={option.crn} value={option.crn}>
                          {dropdownOptionLabel(option)}
                        </option>
                      ))}
                    </select>
                  );
                }),
              )}
              {visibleGroups.length === 0 && (
                <p className="text-xs text-muted">
                  {distanceMode ? "No distance section found." : "No sections found."}
                </p>
              )}
            </div>
          )}
        </div>

        <button
          onClick={() => removeCourseEntirely(course.course_id)}
          className="shrink-0 px-1 text-sm text-muted transition-colors hover:text-danger"
          aria-label={`Remove ${course.subject} ${course.course_number} entirely`}
          title="Remove completely"
        >
          ×
        </button>
      </div>
    </div>
  );
}

interface SlotCoursesPanelProps {
  slot: "top" | "bottom";
  termCode: string | null;
}

export function SlotCoursesPanel({ slot, termCode }: SlotCoursesPanelProps) {
  const selections = usePlannerBuilderStore((s) => s.selections);
  const knownCourses = usePlannerBuilderStore((s) => s.knownCourses);

  const courses = Object.entries(selections)
    .filter(([, sel]) => (slot === "top" ? sel.activeTop : sel.activeBottom))
    .map(([id]) => knownCourses[Number(id)])
    .filter((c): c is Course => Boolean(c))
    .sort((a, b) => (a.subject + a.course_number).localeCompare(b.subject + b.course_number));

  if (!termCode) {
    return (
      <div className="rounded-2xl border border-hairline bg-panel px-3 py-4">
        <p className="text-xs text-muted">Select a term to add courses here.</p>
      </div>
    );
  }

  return (
    <div className="custom-scrollbar max-h-[600px] space-y-2 overflow-y-auto rounded-2xl border border-hairline bg-panel p-3">
      {courses.length === 0 ? (
        <p className="text-xs text-muted">No courses added yet - search above and add some.</p>
      ) : (
        courses.map((course) => (
          <CourseEntry key={course.course_id} course={course} termCode={termCode} slot={slot} />
        ))
      )}
    </div>
  );
}
