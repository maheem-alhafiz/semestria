"use client";

import { addDays, format, parseISO } from "date-fns";
import { useEffect, useState } from "react";

import { AssessmentTaskModal, type AssessmentFormValues } from "@/components/AssessmentTaskModal";
import { AssessmentsWeekView } from "@/components/AssessmentsWeekView";
import { CourseGradeList } from "@/components/CourseGradeList";
import { TodosSection } from "@/components/TodosSection";
import { TopicsLogSection } from "@/components/TopicsLogSection";
import { getTerms } from "@/lib/api";
import { useAssessmentsStore } from "@/store/assessmentsStore";
import type { AssessmentRead, Term } from "@/types/api";

export default function AssessmentsPage() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [loadingTerms, setLoadingTerms] = useState(true);

  const term = useAssessmentsStore((s) => s.term);
  const setTerm = useAssessmentsStore((s) => s.setTerm);
  const loadGradeScale = useAssessmentsStore((s) => s.loadGradeScale);
  const viewedWeekStart = useAssessmentsStore((s) => s.viewedWeekStart);
  const goToNextWeek = useAssessmentsStore((s) => s.goToNextWeek);
  const goToPrevWeek = useAssessmentsStore((s) => s.goToPrevWeek);
  const courses = useAssessmentsStore((s) => s.courses);
  const addAssessment = useAssessmentsStore((s) => s.addAssessment);
  const editAssessment = useAssessmentsStore((s) => s.editAssessment);
  const removeAssessment = useAssessmentsStore((s) => s.removeAssessment);
  const isLoading = useAssessmentsStore((s) => s.isLoading);
  const error = useAssessmentsStore((s) => s.error);

  const [modalOpen, setModalOpen] = useState(false);
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
    loadGradeScale();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const weekStartDate = parseISO(viewedWeekStart);
  const weekEndDate = addDays(weekStartDate, 6);
  const weekLabel =
    term?.start_date != null
      ? `Week ${Math.max(1, Math.round((weekStartDate.getTime() - parseISO(term.start_date).getTime()) / (7 * 86400000)) + 1)}`
      : "Week";

  function openAddModal() {
    setEditing(null);
    setModalOpen(true);
  }

  function openEditModal(assessment: AssessmentRead) {
    setEditing(assessment);
    setModalOpen(true);
  }

  async function handleSave(values: AssessmentFormValues, keepOpen: boolean) {
    if (!term) return;
    setIsSaving(true);
    try {
      if (editing) {
        await editAssessment(editing.id, values);
        setModalOpen(false);
        setEditing(null);
      } else {
        await addAssessment({ term_code: term.term_code, ...values });
        if (!keepOpen) setModalOpen(false);
      }
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
            <button onClick={goToPrevWeek} className="rounded-lg px-2 py-1 text-sm text-muted hover:text-paper" aria-label="Previous week">
              ←
            </button>
            <span className="px-1.5 text-xs font-medium text-paper">
              {weekLabel} · {format(weekStartDate, "MMM d")}–{format(weekEndDate, "MMM d")}
            </span>
            <button onClick={goToNextWeek} className="rounded-lg px-2 py-1 text-sm text-muted hover:text-paper" aria-label="Next week">
              →
            </button>
          </div>

          <button
            onClick={openAddModal}
            disabled={courses.length === 0}
            className="rounded-xl bg-accent px-4 py-1.5 text-sm font-medium text-canvas disabled:opacity-40"
          >
            + Add assessment
          </button>
        </div>
      </div>

      {error && <p className="mt-3 text-sm text-danger">{error}</p>}

      {term && (
        <div className="mt-4">
          <CourseGradeList termCode={term.term_code} />
        </div>
      )}

      {isLoading && <p className="mt-4 text-sm text-muted">Loading…</p>}

      {!isLoading && courses.length > 0 && <AssessmentsWeekView onOpenTask={openEditModal} />}

      {!isLoading && (
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TopicsLogSection />
          <TodosSection />
        </div>
      )}

      <AssessmentTaskModal
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
            await removeAssessment(id);
            setModalOpen(false);
            setEditing(null);
          } finally {
            setIsSaving(false);
          }
        }}
        onSave={handleSave}
      />
    </main>
  );
}
