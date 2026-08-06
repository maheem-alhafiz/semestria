"use client";

import { addDays, format, isSameDay, parseISO } from "date-fns";
import { useMemo, useState } from "react";

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

interface AssessmentsWeekViewProps {
  onAddForDay: (dueDate: string) => void;
  onOpenTask: (assessment: AssessmentRead) => void;
}

export function AssessmentsWeekView({ onAddForDay, onOpenTask }: AssessmentsWeekViewProps) {
  const viewedWeekStart = useAssessmentsStore((s) => s.viewedWeekStart);
  const assessments = useAssessmentsStore((s) => s.assessments);
  const courses = useAssessmentsStore((s) => s.courses);
  const topics = useAssessmentsStore((s) => s.topics);
  const saveTopic = useAssessmentsStore((s) => s.saveTopic);
  const term = useAssessmentsStore((s) => s.term);

  const weekStart = parseISO(viewedWeekStart);
  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => addDays(weekStart, i)), [viewedWeekStart]);

  const unscheduled = assessments.filter((a) => !a.due_date);

  return (
    <div className="mt-4 space-y-4">
      {/* 7-day grid */}
      <div className="grid grid-cols-7 gap-2">
        {days.map((day) => {
          const dayIso = format(day, "yyyy-MM-dd");
          const dayAssessments = assessments.filter(
            (a) => a.due_date && isSameDay(parseISO(a.due_date), day)
          );
          const isToday = isSameDay(day, new Date());
          return (
            <div
              key={dayIso}
              className={`min-h-[140px] rounded-2xl border p-2 ${
                isToday ? "border-accent" : "border-hairline"
              } bg-panel`}
            >
              <div className="flex items-center justify-between">
                <p className="text-xs font-medium text-muted">
                  {format(day, "EEE")} <span className="text-paper">{format(day, "d")}</span>
                </p>
                <button
                  onClick={() => onAddForDay(dayIso)}
                  className="text-xs text-muted hover:text-paper"
                  aria-label="Add assessment"
                >
                  +
                </button>
              </div>
              <div className="mt-1.5 space-y-1">
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
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Unscheduled bucket */}
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

      {/* Per-course topic notes for this week */}
      {courses.length > 0 && (
        <div className="rounded-2xl border border-hairline bg-panel p-3">
          <p className="text-xs font-medium text-muted">Topics covered this week</p>
          <div className="mt-2 space-y-2">
            {courses.map((c) => (
              <TopicRow
                key={c.course_id}
                courseId={c.course_id}
                courseLabel={`${c.subject} ${c.course_number}`}
                weekStartDate={viewedWeekStart}
                initialText={
                  topics.find(
                    (t) => t.course_id === c.course_id && t.week_start_date === viewedWeekStart
                  )?.topic_text ?? ""
                }
                termCode={term?.term_code ?? ""}
                onSave={saveTopic}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TopicRow({
  courseId,
  courseLabel,
  weekStartDate,
  initialText,
  termCode,
  onSave,
}: {
  courseId: number;
  courseLabel: string;
  weekStartDate: string;
  initialText: string;
  termCode: string;
  onSave: (payload: {
    term_code: string;
    course_id: number;
    week_start_date: string;
    topic_text: string;
  }) => Promise<void>;
}) {
  const [text, setText] = useState(initialText);
  const [saving, setSaving] = useState(false);

  return (
    <div className="flex items-start gap-2">
      <span className="w-20 shrink-0 pt-2 text-xs font-medium text-paper">{courseLabel}</span>
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onBlur={async () => {
          if (text === initialText) return;
          setSaving(true);
          try {
            await onSave({
              term_code: termCode,
              course_id: courseId,
              week_start_date: weekStartDate,
              topic_text: text,
            });
          } finally {
            setSaving(false);
          }
        }}
        placeholder="What did this course cover this week?"
        className="flex-1 rounded-lg border border-hairline bg-elevated px-2.5 py-1.5 text-xs text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent disabled:opacity-60"
        disabled={saving}
      />
    </div>
  );
}
