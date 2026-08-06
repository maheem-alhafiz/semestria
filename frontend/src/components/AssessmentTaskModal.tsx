"use client";

import { useState } from "react";

import type { AssessmentCourseRead, AssessmentRead, AssessmentType } from "@/types/api";

const TYPE_OPTIONS: { value: AssessmentType; label: string }[] = [
  { value: "ASSIGNMENT", label: "Assignment" },
  { value: "QUIZ", label: "Quiz" },
  { value: "EXAM", label: "Exam" },
  { value: "LAB", label: "Lab" },
  { value: "PROJECT", label: "Project" },
  { value: "OTHER", label: "Other" },
];

interface AssessmentTaskModalProps {
  isOpen: boolean;
  courses: AssessmentCourseRead[];
  // Pre-fills the course dropdown and/or due date -- e.g. clicking "+" on
  // a specific course row, or on a specific day cell.
  defaultCourseId?: number | null;
  defaultDueDate?: string | null;
  editing?: AssessmentRead | null;
  isSaving: boolean;
  onCancel: () => void;
  onDelete?: (id: number) => void;
  onSave: (values: {
    course_id: number;
    title: string;
    assessment_type: AssessmentType;
    due_date: string | null;
    weight_percent: number | null;
    is_done: boolean;
    grade_received: number | null;
    notes: string | null;
  }) => void;
}

export function AssessmentTaskModal({
  isOpen,
  courses,
  defaultCourseId,
  defaultDueDate,
  editing,
  isSaving,
  onCancel,
  onDelete,
  onSave,
}: AssessmentTaskModalProps) {
  const [courseId, setCourseId] = useState<number | null>(
    editing?.course_id ?? defaultCourseId ?? courses[0]?.course_id ?? null
  );
  const [title, setTitle] = useState(editing?.title ?? "");
  const [type, setType] = useState<AssessmentType>(editing?.assessment_type ?? "ASSIGNMENT");
  const [dueDate, setDueDate] = useState(editing?.due_date ?? defaultDueDate ?? "");
  const [weight, setWeight] = useState(editing?.weight_percent?.toString() ?? "");
  const [isDone, setIsDone] = useState(editing?.is_done ?? false);
  const [grade, setGrade] = useState(editing?.grade_received?.toString() ?? "");
  const [notes, setNotes] = useState(editing?.notes ?? "");

  if (!isOpen) return null;

  const canSave = courseId !== null && title.trim().length > 0;

  function handleSave() {
    if (!canSave || courseId === null) return;
    onSave({
      course_id: courseId,
      title: title.trim(),
      assessment_type: type,
      due_date: dueDate || null,
      weight_percent: weight.trim() ? Number(weight) : null,
      is_done: isDone,
      grade_received: grade.trim() ? Number(grade) : null,
      notes: notes.trim() || null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-md rounded-2xl border border-hairline bg-panel p-5 shadow-2xl">
        <h2 className="text-sm font-semibold text-paper">
          {editing ? "Edit assessment" : "New assessment"}
        </h2>

        <div className="mt-3 space-y-3">
          <div>
            <label className="text-xs font-medium text-muted">Course</label>
            <select
              value={courseId ?? ""}
              onChange={(e) => setCourseId(Number(e.target.value))}
              className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper focus:outline-none focus:ring-1 focus:ring-accent"
            >
              {courses.map((c) => (
                <option key={c.course_id} value={c.course_id}>
                  {c.subject} {c.course_number}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="text-xs font-medium text-muted">Title</label>
            <input
              autoFocus
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Assignment 3, Midterm 1"
              className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs font-medium text-muted">Type</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value as AssessmentType)}
                className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper focus:outline-none focus:ring-1 focus:ring-accent"
              >
                {TYPE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex-1">
              <label className="text-xs font-medium text-muted">Due date</label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <div className="flex-1">
              <label className="text-xs font-medium text-muted">Weight (%)</label>
              <input
                type="number"
                step="0.01"
                value={weight}
                onChange={(e) => setWeight(e.target.value)}
                placeholder="e.g. 15"
                className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
            <div className="flex-1">
              <label className="text-xs font-medium text-muted">Grade received (%)</label>
              <input
                type="number"
                step="0.01"
                value={grade}
                onChange={(e) => setGrade(e.target.value)}
                placeholder="Once graded"
                className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>

          <label className="flex items-center gap-2 text-sm text-paper">
            <input
              type="checkbox"
              checked={isDone}
              onChange={(e) => setIsDone(e.target.checked)}
              className="h-4 w-4 rounded border-hairline accent-[var(--accent)]"
            />
            Done
          </label>

          <div>
            <label className="text-xs font-medium text-muted">Notes</label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
              className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between">
          <div>
            {editing && onDelete && (
              <button
                onClick={() => onDelete(editing.id)}
                className="rounded-xl px-3 py-1.5 text-sm text-danger transition-colors hover:opacity-80"
              >
                Delete
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={onCancel}
              className="rounded-xl px-3 py-1.5 text-sm text-muted transition-colors hover:text-paper"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving || !canSave}
              className="rounded-xl bg-accent px-4 py-1.5 text-sm font-medium text-canvas disabled:opacity-40"
            >
              {isSaving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
