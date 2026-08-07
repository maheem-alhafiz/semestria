"use client";

import { addDays, eachDayOfInterval, endOfMonth, endOfWeek, format, isSameDay, isSameMonth, parseISO, startOfMonth, startOfWeek } from "date-fns";
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

  const weekStart = parseISO(viewedWeekStart);
  const weekDays = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [weekStart]);

  const calendarDays = useMemo(() => {
    const mStart = startOfMonth(weekStart);
    const mEnd = endOfMonth(mStart);
    const cStart = startOfWeek(mStart, { weekStartsOn: 1 }); // Monday start
    const cEnd = endOfWeek(mEnd, { weekStartsOn: 1 });
    return eachDayOfInterval({ start: cStart, end: cEnd });
  }, [weekStart]);

  const unscheduled = assessments.filter((a) => !a.due_date);

  const agendaDays = weekDays.map((day) => {
    return {
      day,
      items: assessments.filter((a) => a.due_date && isSameDay(parseISO(a.due_date), day)),
    };
  }).filter((d) => d.items.length > 0);

  return (
    <div className="mt-4 flex flex-col items-start gap-6 lg:flex-row">
      {/* LEFT: Mini-Map */}
      <div className="w-full shrink-0 rounded-2xl border border-hairline bg-panel p-4 lg:w-72">
        <h3 className="text-sm font-semibold text-paper">{format(weekStart, "MMMM yyyy")}</h3>
        <div className="mt-4 grid grid-cols-7 gap-1 text-center text-xs font-medium text-muted">
          <div>M</div><div>T</div><div>W</div><div>T</div><div>F</div><div>S</div><div>S</div>
        </div>
        <div className="mt-2 grid grid-cols-7 gap-1">
          {calendarDays.map((day) => {
            const dayIso = format(day, "yyyy-MM-dd");
            const isCurrentMonth = isSameMonth(day, weekStart);
            const isToday = isSameDay(day, new Date());
            const isViewedWeek = day >= weekStart && day <= addDays(weekStart, 6);
            const hasAssessments = assessments.some(
              (a) => a.due_date && isSameDay(parseISO(a.due_date), day)
            );

            return (
              <div
                key={dayIso}
                className={`relative flex h-8 items-center justify-center rounded-md text-xs
                  ${isViewedWeek ? "bg-elevated text-paper" : ""}
                  ${!isCurrentMonth ? "opacity-30" : "text-muted"}
                  ${isToday ? "font-bold text-accent" : ""}
                `}
              >
                <span>{format(day, "d")}</span>
                {hasAssessments && (
                  <span className="absolute bottom-1 h-1 w-1 rounded-full bg-accent"></span>
                )}
              </div>
            );
          })}
        </div>

        {unscheduled.length > 0 && (
          <div className="mt-6 border-t border-hairline pt-4">
            <p className="text-xs font-medium text-muted">Unscheduled</p>
            <div className="mt-2 space-y-1.5">
              {unscheduled.map((a) => (
                <button
                  key={a.id}
                  onClick={() => onOpenTask(a)}
                  className={`block w-full truncate rounded-lg px-2 py-1.5 text-left text-xs ${
                    a.is_done ? "opacity-50 line-through" : ""
                  } ${TYPE_BADGE[a.assessment_type] ?? "bg-muted/20 text-muted"}`}
                >
                  <span className="font-medium">{courseLabel(courses, a.course_id)}</span> · {a.title}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* RIGHT: Agenda */}
      <div className="w-full flex-1 space-y-4">
        <div className="flex items-center justify-between border-b border-hairline pb-2">
          <h2 className="text-sm font-semibold text-paper">This Week</h2>
        </div>

        {agendaDays.length === 0 ? (
          <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed border-hairline bg-panel/50">
            <p className="text-sm text-muted">No assessments scheduled for this week.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {agendaDays.map(({ day, items }) => {
              const isToday = isSameDay(day, new Date());
              return (
                <div key={day.toISOString()} className="relative pl-4">
                  {/* Timeline indicator line */}
                  <div className={`absolute left-0 top-1.5 h-full w-[2px] rounded-full ${isToday ? "bg-accent" : "bg-hairline"}`}></div>
                  
                  <h3 className={`text-sm font-medium ${isToday ? "text-accent" : "text-paper"}`}>
                    {format(day, "EEEE, MMM d")}
                  </h3>
                  <div className="mt-2 space-y-2">
                    {items.map((a) => (
                      <button
                        key={a.id}
                        onClick={() => onOpenTask(a)}
                        className={`flex w-full flex-col gap-1 rounded-xl border border-hairline bg-panel p-3 text-left transition-colors hover:border-muted/50 ${
                          a.is_done ? "opacity-50" : ""
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className={`rounded-md px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${TYPE_BADGE[a.assessment_type] ?? "bg-muted/20 text-muted"}`}>
                            {a.assessment_type}
                          </span>
                          <span className="text-xs font-semibold text-muted">
                            {courseLabel(courses, a.course_id)}
                          </span>
                        </div>
                        <div className="flex items-center justify-between gap-4">
                          <span className={`text-sm font-medium ${a.is_done ? "line-through text-muted" : "text-paper"}`}>
                            {a.title}
                          </span>
                          {a.due_time && (
                            <span className="shrink-0 text-xs text-muted">
                              {formatTime(a.due_time).replace(" · ", "")}
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}