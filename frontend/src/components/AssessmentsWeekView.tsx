"use client";

/**
 * The old version put a small "+" button and an empty box in every day
 * cell, plus a per-course topic textbox pinned to whatever week you'd
 * navigated to. Both were bad for bulk entry: adding a whole syllabus's
 * worth of due dates meant clicking through every week one at a time.
 * This version is pure display -- the grid shows what's due, all adding
 * happens through one "+ Add assessment" button in the page header (see
 * app/assessments/page.tsx), and topics moved out entirely into
 * TopicsLogSection, which isn't tied to calendar navigation at all.
 */

import { addDays, format, isSameDay, parseISO } from "date-fns";
import { useMemo } from "react";

import { useAssessmentsStore } from "@/store/assessmentsStore";
import type { AssessmentRead } from "@/types/api";

const TYPE_BADGE: Record<string, string> = {
  ASSIGNMENT: "bg-accent/20 text-accent",
  QUIZ: "bg-warning/20 text-warning",
  EXAM: "bg-danger/20 text-danger",
  LAB: "bg-success/20 text-success",
  PROJECT: "bg-accent/20 text-accent",
  OTHER: "bg-muted/20 text-muted",
};

function courseLabel(courses: { course_id: number; subject: string; course_number: string }[], id: number) {
  const c = courses.find((c) => c.course_id === id);
  return c ? `${c.subject} ${c.course_number}` : "";
}

function formatTime(dueTime: string | null): string {
  if (!dueTime) return "";
  const parts = dueTime.split(":").map(Number);
  const h = parts[0] ?? 0;
  const m = parts[1] ?? 0;
  const period = h >= 12 ? "PM" : "AM";
  const hour12 = h % 12 === 0 ? 12 : h % 12;
  return ` · ${hour12}:${String(m).padStart(2, "0")} ${period}`;
}

interface AssessmentsWeekViewProps {
  onOpenTask: (assessment: AssessmentRead) => void;
}

export function AssessmentsWeekView({ onOpenTask }: AssessmentsWeekViewProps) {
  const viewedWeekStart = useAssessmentsStore((s) => s.viewedWeekStart);
  const assessments = useAssessmentsStore((s) => s.assessments);
  const courses = useAssessmentsStore((s) => s.courses);

  const days = useMemo(
    () => Array.from({ length: 7 }, (_, i) => addDays(parseISO(viewedWeekStart), i)),
    [viewedWeekStart]
  );

  const unscheduled = assessments.filter((a) => !a.due_date);

  return (
    <div className="mt-4 space-y-4">
      <div className="grid grid-cols-7 gap-2">
        {days.map((day) => {
          const dayIso = format(day, "yyyy-MM-dd");
          const dayAssessments = assessments.filter((a) => a.due_date && isSameDay(parseISO(a.due_date), day));
          const isToday = isSameDay(day, new Date());
          return (
            <div
              key={dayIso}
              className={`min-h-[110px] rounded-2xl border p-2 ${
                isToday ? "border-accent" : "border-hairline"
              } bg-panel`}
            >
              <p className="text-xs font-medium text-muted">
                {format(day, "EEE")} <span className="text-paper">{format(day, "d")}</span>
              </p>
              <div className="mt-1.5 space-y-1">
                {dayAssessments.length === 0 && <p className="text-[11px] text-muted/50">—</p>}
                {dayAssessments.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => onOpenTask(a)}
                    className={`block w-full truncate rounded-md px-1.5 py-1 text-left text-[11px] ${
                      a.is_done ? "opacity-50 line-through" : ""
                    } ${TYPE_BADGE[a.assessment_type] ?? "bg-muted/20 text-muted"}`}
                    title={a.title}
                  >
                    {courseLabel(courses, a.course_id)} · {a.title}
                    {formatTime(a.due_time)}
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {unscheduled.length > 0 && (
        <div className="rounded-2xl border border-hairline bg-panel p-3">
          <p className="text-xs font-medium text-muted">Unscheduled (no due date yet)</p>
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {unscheduled.map((a) => (
              <button
                key={a.id}
                onClick={() => onOpenTask(a)}
                className={`rounded-md px-2 py-1 text-[11px] ${
                  a.is_done ? "opacity-50 line-through" : ""
                } ${TYPE_BADGE[a.assessment_type] ?? "bg-muted/20 text-muted"}`}
              >
                {courseLabel(courses, a.course_id)} · {a.title}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
