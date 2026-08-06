"use client";

import { addDays, format, parseISO } from "date-fns";
import { useEffect, useState } from "react";

import { AddAssessmentCourseSearch } from "@/components/AddAssessmentCourseSearch";
import { AssessmentTaskModal } from "@/components/AssessmentTaskModal";
import { AssessmentsWeekView } from "@/components/AssessmentsWeekView";
import { getTerms } from "@/lib/api";
import { useAssessmentsStore } from "@/store/assessmentsStore";
import type { AssessmentRead, AssessmentType, Term } from "@/types/api";

interface TaskFormValues {
  course_id: number;
  title: string;
  assessment_type: AssessmentType;
  due_date: string | null;
  weight_percent: number | null;
  is_done: boolean;
  grade_received: number | null;
  notes: string | null;
}

export default function AssessmentsPage() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [loadingTerms, setLoadingTerms] = useState(true);

  const term = useAssessmentsStore((s) => s.term);
  const setTerm = useAssessmentsStore((s) => s.setTerm);
  const viewedWeekStart = useAssessmentsStore((s) => s.viewedWeekStart);
  const goToNextWeek = useAssessmentsStore((s) => s.goToNextWeek);
  const goToPrevWeek = useAssessmentsStore((s) => s.goToPrevWeek);
  const courses = useAssessmentsStore((s) => s.courses);
  const removeCourse = useAssessmentsStore((s) => s.removeCourse);
  const addAssessment = useAssessmentsStore((s) => s.addAssessment);
  const editAssessment = useAssessmentsStore((s) => s.editAssessment);
  const removeAssessment = useAssessmentsStore((s) => s.removeAssessment);
  const isLoading = useAssessmentsStore((s) => s.isLoading);
  const error = useAssessmentsStore((s) => s.error);

  const [modalOpen, setModalOpen] = useState(false);
  const [modalDefaults, setModalDefaults] = useState<{ courseId?: number | null; dueDate?: string | null }>({});
  const [editing, setEditing] = useState<AssessmentRead | null>(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    getTerms()
      .then((data) => {
        setTerms(data);
        const first = data[0];
        if (first && !term) setTerm(first);
      })
      .catch(() => {})
      .finally(() => setLoadingTerms(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const weekStartDate = parseISO(viewedWeekStart);
  const weekEndDate = addDays(weekStartDate, 6);
  const weekLabel =
    term?.start_date != null
      ? `Week ${Math.max(1, Math.round((weekStartDate.getTime() - parseISO(term.start_date).getTime()) / (7 * 86400000)) + 1)}`
      : "Week";

  function openAddModal(defaults: { courseId?: number | null; dueDate?: string | null } = {}) {
    setEditing(null);
    setModalDefaults(defaults);
    setModalOpen(true);
  }

  function openEditModal(assessment: AssessmentRead) {
    setEditing(assessment);
    setModalDefaults({});
    setModalOpen(true);
  }

  async function handleSave(values: TaskFormValues) {
    if (!term) return;
    setIsSaving(true);
    try {
      if (editing) {
        await editAssessment(editing.id, values);
      } else {
        await addAssessment({ term_code: term.term_code, ...values });
      }
      setModalOpen(false);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-[1600px] px-6 py-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-xl font-semibold text-paper">Assessments</h1>

        <div className="flex items-center gap-3">
          <select
            value={term?.term_code ?? ""}
            onChange={(e) => {
              const next = terms.find((t) => t.term_code === e.target.value);
              if (next) setTerm(next);
            }}
            disabled={loadingTerms || terms.length === 0}
            className="rounded-xl border border-hairline bg-elevated px-3 py-1.5 text-sm text-paper disabled:opacity-50"
          >
            {terms.map((t) => (
              <option key={t.term_code} value={t.term_code}>
                {t.description}
              </option>
            ))}
          </select>

          <div className="flex items-center gap-1.5 rounded-xl border border-hairline bg-elevated px-1.5 py-1">
            <button
              onClick={goToPrevWeek}
              className="rounded-lg px-2 py-1 text-sm text-muted hover:text-paper"
              aria-label="Previous week"
            >
              ←
            </button>
            <span className="px-1.5 text-xs font-medium text-paper">
              {weekLabel} · {format(weekStartDate, "MMM d")}–{format(weekEndDate, "MMM d")}
            </span>
            <button
              onClick={goToNextWeek}
              className="rounded-lg px-2 py-1 text-sm text-muted hover:text-paper"
              aria-label="Next week"
            >
              →
            </button>
          </div>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-danger">{error}</p>}

      {/* Tracked courses row */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        {courses.map((c) => (
          <div
            key={c.course_id}
            className="flex items-center gap-1.5 rounded-full border border-hairline bg-panel px-3 py-1.5 text-xs text-paper"
          >
            <button onClick={() => openAddModal({ courseId: c.course_id })} className="hover:text-accent">
              {c.subject} {c.course_number}
            </button>
            {c.source === "manual" && (
              <button
                onClick={() => removeCourse(c.course_id)}
                className="text-muted hover:text-danger"
                aria-label={`Remove ${c.subject} ${c.course_number}`}
              >
                ×
              </button>
            )}
          </div>
        ))}
        {term && <AddAssessmentCourseSearch termCode={term.term_code} />}
      </div>

      {isLoading && <p className="mt-4 text-sm text-muted">Loading…</p>}

      {!isLoading && courses.length === 0 && term && (
        <p className="mt-6 text-sm text-muted">
          No courses tracked yet for {term.description}. They&apos;ll auto-pull from any Plan that
          includes this term, or add one manually above.
        </p>
      )}

      {!isLoading && courses.length > 0 && (
        <AssessmentsWeekView
          onAddForDay={(dueDate) => openAddModal({ dueDate })}
          onOpenTask={openEditModal}
        />
      )}

      <AssessmentTaskModal
        isOpen={modalOpen}
        courses={courses}
        defaultCourseId={modalDefaults.courseId}
        defaultDueDate={modalDefaults.dueDate}
        editing={editing}
        isSaving={isSaving}
        onCancel={() => setModalOpen(false)}
        onDelete={async (id) => {
          setIsSaving(true);
          try {
            await removeAssessment(id);
            setModalOpen(false);
          } finally {
            setIsSaving(false);
          }
        }}
        onSave={handleSave}
      />
    </main>
  );
}
