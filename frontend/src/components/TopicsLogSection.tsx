"use client";

import { format, parseISO } from "date-fns";
import { useState } from "react";

import { TopicEntryModal } from "@/components/TopicEntryModal";
import { useAssessmentsStore } from "@/store/assessmentsStore";
import type { TopicEntryRead } from "@/types/api";

export function TopicsLogSection() {
  const topics = useAssessmentsStore((s) => s.topics);
  const courses = useAssessmentsStore((s) => s.courses);
  const addTopic = useAssessmentsStore((s) => s.addTopic);
  const editTopic = useAssessmentsStore((s) => s.editTopic);
  const removeTopic = useAssessmentsStore((s) => s.removeTopic);
  const term = useAssessmentsStore((s) => s.term);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TopicEntryRead | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  const sorted = [...topics].sort((a, b) => a.week_start_date.localeCompare(b.week_start_date));

  function courseLabel(courseId: number) {
    const c = courses.find((c) => c.course_id === courseId);
    return c ? `${c.subject} ${c.course_number}` : "";
  }

  async function handleSave(values: { course_id: number; entry_date: string; topic_text: string }, keepOpen: boolean) {
    if (!term) return;
    setIsSaving(true);
    try {
      if (editing) {
        await editTopic(editing.id, values);
      } else {
        await addTopic({ term_code: term.term_code, ...values });
      }
      if (!keepOpen) {
        setModalOpen(false);
        setEditing(null);
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="rounded-2xl border border-hairline bg-panel p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-paper">Topics covered</h2>
        <button
          onClick={() => {
            setEditing(null);
            setModalOpen(true);
          }}
          disabled={courses.length === 0}
          className="rounded-full border border-hairline px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-paper disabled:opacity-40"
        >
          + Log topic
        </button>
      </div>

      {sorted.length === 0 ? (
        <p className="mt-3 text-sm text-muted">
          Nothing logged yet. Add topics anytime -- no need to visit each week on the calendar.
        </p>
      ) : (
        <div className="mt-3 space-y-1.5">
          {sorted.map((topic) => (
            <button
              key={topic.id}
              onClick={() => {
                setEditing(topic);
                setModalOpen(true);
              }}
              className="flex w-full items-start gap-3 rounded-xl px-2 py-1.5 text-left text-sm hover:bg-elevated"
            >
              <span className="w-24 shrink-0 text-xs text-muted">
                Week of {format(parseISO(topic.week_start_date), "MMM d")}
              </span>
              <span className="w-20 shrink-0 text-xs font-medium text-paper">
                {courseLabel(topic.course_id)}
              </span>
              <span className="min-w-0 flex-1 truncate text-paper">{topic.topic_text}</span>
            </button>
          ))}
        </div>
      )}

      <TopicEntryModal
        isOpen={modalOpen}
        courses={courses}
        editing={editing}
        isSaving={isSaving}
        onCancel={() => {
          setModalOpen(false);
          setEditing(null);
        }}
        onDelete={async (id) => {
          setIsSaving(true);
          try {
            await removeTopic(id);
            setModalOpen(false);
            setEditing(null);
          } finally {
            setIsSaving(false);
          }
        }}
        onSave={handleSave}
      />
    </div>
  );
}
