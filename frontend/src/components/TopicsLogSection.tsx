"use client";

import { format, parseISO } from "date-fns";
import { useMemo, useState } from "react";

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

  // Group by course, then sort weeks within each course
  const groupedTopics = useMemo(() => {
    const groups = new Map<number, TopicEntryRead[]>();
    for (const t of topics) {
      if (!groups.has(t.course_id)) groups.set(t.course_id, []);
      groups.get(t.course_id)!.push(t);
    }
    
    // Sort each course's topics chronologically by week
    for (const [_, courseTopics] of groups) {
      courseTopics.sort((a, b) => a.week_start_date.localeCompare(b.week_start_date));
    }
    return groups;
  }, [topics]);

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
      <div className="flex items-center justify-between border-b border-hairline pb-3">
        <h2 className="text-sm font-semibold text-paper">Topics covered</h2>
        <button
          onClick={() => {
            setEditing(null);
            setModalOpen(true);
          }}
          disabled={courses.length === 0}
          className="rounded-full border border-hairline px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-paper disabled:opacity-40"
        >
          + Add topic
        </button>
      </div>

      {topics.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          Nothing logged yet. Add topics anytime -- no need to visit each week on the calendar.
        </p>
      ) : (
        <div className="mt-4 space-y-6">
          {Array.from(groupedTopics.entries()).map(([courseId, courseTopics]) => (
            <div key={courseId}>
              <h3 className="mb-2 text-xs font-bold uppercase tracking-wider text-muted">
                {courseLabel(courseId)}
              </h3>
              <div className="space-y-1.5 border-l-2 border-hairline pl-3">
                {courseTopics.map((topic) => (
                  <button
                    key={topic.id}
                    onClick={() => {
                      setEditing(topic);
                      setModalOpen(true);
                    }}
                    className="flex w-full flex-col items-start gap-0.5 rounded-xl px-2 py-1.5 text-left text-sm hover:bg-elevated"
                  >
                    <span className="text-[10px] font-medium text-muted">
                      Week of {format(parseISO(topic.week_start_date), "MMM d")}
                    </span>
                    <span className="text-paper">{topic.topic_text}</span>
                  </button>
                ))}
              </div>
            </div>
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