"use client";

import { useEffect, useRef } from "react";

import { colorForCourse } from "@/components/PlannerCourseCard";
import { usePlannerBuilderStore } from "@/store/plannerBuilderStore";
import type { Course } from "@/types/api";

interface CourseSearchDropdownProps {
  results: Course[];
  offeredByTerm: Map<number, { top: boolean; bottom: boolean }>;
  topTermLabel: string;
  bottomTermLabel: string;
  visible: boolean;
  onClose: () => void;
}

// Anchored dropdown beneath the search box, closed by clicking outside
// it -- replaces the old horizontal-scroll strip. Each row is a compact
// "add to term" control; once added, the course's real home is
// SlotCoursesPanel, not here.
export function CourseSearchDropdown({
  results,
  offeredByTerm,
  topTermLabel,
  bottomTermLabel,
  visible,
  onClose,
}: CourseSearchDropdownProps) {
  const toggleCourseSlot = usePlannerBuilderStore((s) => s.toggleCourseSlot);
  const selections = usePlannerBuilderStore((s) => s.selections);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  if (!visible || results.length === 0) return null;

  return (
    <div
      ref={ref}
      className="absolute left-0 right-0 top-full z-20 mt-1.5 max-h-96 overflow-y-auto rounded-2xl border border-hairline bg-elevated shadow-2xl"
    >
      {results.map((course) => {
        const offered = offeredByTerm.get(course.course_id) ?? { top: false, bottom: false };
        const sel = selections[course.course_id];
        const color = colorForCourse(course.course_id);
        return (
          <div
            key={course.course_id}
            className="flex items-center justify-between gap-3 border-b border-hairline/70 px-3.5 py-2.5 last:border-0 hover:bg-panel/60"
          >
            <div className="flex min-w-0 items-center gap-2.5">
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-sm"
                style={{ backgroundColor: color }}
                aria-hidden
              />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-paper">
                  {course.subject} {course.course_number}
                  <span className="ml-1.5 text-xs font-normal text-muted">
                    {course.credit_hours} CH
                  </span>
                </p>
                <p className="truncate text-xs text-muted">{course.title}</p>
              </div>
            </div>
            <div className="flex shrink-0 gap-1.5">
              {offered.top && (
                <button
                  onClick={() => toggleCourseSlot(course, "top")}
                  className={`rounded-md px-2 py-1 text-[11px] font-medium transition-colors ${
                    sel?.activeTop
                      ? "bg-accent text-canvas"
                      : "bg-panel text-muted hover:text-paper"
                  }`}
                >
                  {topTermLabel} {sel?.activeTop && "✓"}
                </button>
              )}
              {offered.bottom && (
                <button
                  onClick={() => toggleCourseSlot(course, "bottom")}
                  className={`rounded-md px-2 py-1 text-[11px] font-medium transition-colors ${
                    sel?.activeBottom
                      ? "bg-accent text-canvas"
                      : "bg-panel text-muted hover:text-paper"
                  }`}
                >
                  {bottomTermLabel} {sel?.activeBottom && "✓"}
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
