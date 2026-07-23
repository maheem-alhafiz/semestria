"use client";

import { usePlannerBuilderStore } from "@/store/plannerBuilderStore";
import type { Course } from "@/types/api";

// Muted, desaturated palette matching Semestria's course-chip aesthetic
// (sage/tan/mustard/teal rather than vivid saturated defaults) --
// assigned deterministically by course_id so a course's color stays
// stable across renders/reloads without needing to store it. Exported
// for reuse in TermCalendar and SlotCoursesPanel, so every
// representation of a given course (search dropdown, calendar block,
// panel entry) shows the same color.
//
// NOTE: approximated from visual inspection of reference screenshots,
// not sampled exact hex values. Swap for Semestria's actual CSS custom
// properties if you have them, for a pixel-accurate match.
const COURSE_COLORS = [
  "#8FBC94", "#D9A066", "#E0C068", "#7EC8D9", "#B08FC7",
  "#E08F8F", "#7E93C8", "#A8B36A", "#C98F6B", "#7FC7A6",
];

export function colorForCourse(courseId: number): string {
  return COURSE_COLORS[courseId % COURSE_COLORS.length] ?? "#8FBC94";
}

interface PlannerCourseCardProps {
  course: Course;
  offeredTop: boolean;
  offeredBottom: boolean;
  topTermLabel: string;
  bottomTermLabel: string;
}

// Pure "add to a term" control, rendered inside CourseSearchDropdown's
// rows. Once toggled on, a course's real editing surface -- section
// dropdowns, removal -- lives in SlotCoursesPanel, not here.
export function PlannerCourseCard({
  course,
  offeredTop,
  offeredBottom,
  topTermLabel,
  bottomTermLabel,
}: PlannerCourseCardProps) {
  const selection = usePlannerBuilderStore((s) => s.selections[course.course_id]);
  const toggleCourseSlot = usePlannerBuilderStore((s) => s.toggleCourseSlot);

  const activeTop = selection?.activeTop ?? false;
  const activeBottom = selection?.activeBottom ?? false;
  const color = colorForCourse(course.course_id);

  return (
    <div className="rounded-xl border border-hairline bg-elevated px-3 py-2.5">
      <div className="flex items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ backgroundColor: color }}
            aria-hidden
          />
          <span className="truncate text-sm font-medium text-paper">
            {course.subject} {course.course_number}
            <span className="ml-2 font-normal text-muted">{course.title}</span>
          </span>
        </div>
        <span className="shrink-0 text-xs text-muted">{course.credit_hours} CH</span>
      </div>

      <div className="mt-2 flex gap-2">
        {offeredTop && (
          <button
            onClick={() => toggleCourseSlot(course, "top")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeTop ? "bg-accent text-canvas" : "bg-panel text-muted hover:text-paper"
            }`}
          >
            {topTermLabel} {activeTop && "✓"}
          </button>
        )}
        {offeredBottom && (
          <button
            onClick={() => toggleCourseSlot(course, "bottom")}
            className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
              activeBottom ? "bg-accent text-canvas" : "bg-panel text-muted hover:text-paper"
            }`}
          >
            {bottomTermLabel} {activeBottom && "✓"}
          </button>
        )}
      </div>
    </div>
  );
}
