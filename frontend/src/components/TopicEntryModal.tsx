"use client";

import { useState } from "react";

import type { AssessmentCourseRead, TopicEntryRead } from "@/types/api";

interface TopicEntryModalProps {
  isOpen: boolean;
  courses: AssessmentCourseRead[];
  editing?: TopicEntryRead | null;
  isSaving: boolean;
  onCancel: () => void;
  onDelete?: (id: number) => void;
  onSave: (values: { course_id: number; entry_date: string; topic_text: string }, keepOpen: boolean) => void;
}

export function TopicEntryModal({
  isOpen,
  courses,
  editing,
  isSaving,
  onCancel,
  onDelete,
  onSave,
}: TopicEntryModalProps) {
  const [courseId, setCourseId] = useState<number | null>(editing?.course_id ?? courses[0]?.course_id ?? null);
  const [entryDate, setEntryDate] = useState(editing?.week_start_date ?? "");
  const [topicText, setTopicText] = useState(editing?.topic_text ?? "");

  if (!isOpen) return null;

  const canSave = courseId !== null && entryDate.length > 0 && topicText.trim().length > 0;

  function buildValues() {
    if (!canSave || courseId === null) return null;
    return { course_id: courseId, entry_date: entryDate, topic_text: topicText.trim() };
  }

  function handleSave() {
    const values = buildValues();
    if (!values) return;
    onSave(values, false);
  }

  function handleSaveAndAddAnother() {
    const values = buildValues();
    if (!values) return;
    onSave(values, true);
    setTopicText("");
    // Course + date carry over -- entering a whole syllabus's weekly
    // topic list is usually one course, one week at a time, incrementing.
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-hairline bg-panel p-5 shadow-2xl">
        <h2 className="text-sm font-semibold text-paper">{editing ? "Edit topic" : "Log a topic"}</h2>

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
            <label className="text-xs font-medium text-muted">Date within that week</label>
            <input
              type="date"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              className="mt-1 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div>
            <label className="text-xs font-medium text-muted">What was covered</label>
            <textarea
              autoFocus
              value={topicText}
              onChange={(e) => setTopicText(e.target.value)}
              rows={2}
              placeholder="e.g. Intro to thermodynamics, first law"
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
            <button onClick={onCancel} className="rounded-xl px-3 py-1.5 text-sm text-muted hover:text-paper">
              Cancel
            </button>
            {!editing && (
              <button
                onClick={handleSaveAndAddAnother}
                disabled={isSaving || !canSave}
                className="rounded-xl border border-hairline px-3 py-1.5 text-sm font-medium text-paper disabled:opacity-40"
              >
                Save &amp; add another
              </button>
            )}
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
