"use client";

import { useEffect, useState } from "react";

import { useAssessmentsStore } from "@/store/assessmentsStore";
import type { GradeScaleCutoffItem, LetterGrade } from "@/types/api";

const LETTERS: LetterGrade[] = ["A+", "A", "B+", "B", "C+", "C", "D", "Fail"];

const SUGGESTED_DEFAULT_CUTOFFS: Record<LetterGrade, string> = {
  "A+": "90",
  "A": "80",
  "B+": "75",
  "B": "70",
  "C+": "65",
  "C": "60",
  "D": "50",
  "Fail": "0",
};

export function GradeScaleModal({ courseId, isOpen, onClose }: { courseId: number | null; isOpen: boolean; onClose: () => void }) {
  const gradeScales = useAssessmentsStore((s) => s.gradeScales);
  const saveGradeScale = useAssessmentsStore((s) => s.saveGradeScale);
  const courses = useAssessmentsStore((s) => s.courses);

  const [values, setValues] = useState<Record<LetterGrade, string>>(SUGGESTED_DEFAULT_CUTOFFS);
  const [saving, setSaving] = useState(false);

  const course = courses.find((c) => c.course_id === courseId);

  useEffect(() => {
    if (isOpen && courseId !== null) {
      const existingScale = gradeScales[courseId];
      if (existingScale && existingScale.length > 0) {
        setValues(defaultValues(existingScale));
      } else {
        setValues(SUGGESTED_DEFAULT_CUTOFFS);
      }
    }
  }, [isOpen, courseId, gradeScales]);

  if (!isOpen || courseId === null) return null;

  async function handleSave() {
    if (courseId === null) return; // TS strict check
    
    setSaving(true);
    try {
      const cutoffs: GradeScaleCutoffItem[] = LETTERS.map((letter) => ({
        letter_grade: letter,
        min_percent: Number(values[letter]) || 0,
      }));
      await saveGradeScale(courseId, cutoffs);
      onClose();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-hairline bg-panel p-5 shadow-2xl">
        <h2 className="text-sm font-semibold text-paper">
          {course ? `${course.subject} ${course.course_number} Grade Scale` : "Grade scale"}
        </h2>
        <p className="mt-1 text-xs text-muted">
          Enter the minimum percentage required for each letter grade based on this course&apos;s syllabus.
        </p>

        <div className="mt-3 space-y-1.5">
          {LETTERS.map((letter) => (
            <div key={letter} className="flex items-center gap-2">
              <span className="w-10 text-sm text-paper">{letter}</span>
              <input
                type="number"
                step="0.1"
                value={values[letter]}
                onChange={(e) => setValues((v) => ({ ...v, [letter]: e.target.value }))}
                className="flex-1 rounded-lg border border-hairline bg-elevated px-2.5 py-1.5 text-sm text-paper focus:outline-none focus:ring-1 focus:ring-accent"
              />
              <span className="text-xs text-muted">%+</span>
            </div>
          ))}
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-xl px-3 py-1.5 text-sm text-muted hover:text-paper">
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="rounded-xl bg-accent px-4 py-1.5 text-sm font-medium text-canvas disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}

function defaultValues(gradeScale: GradeScaleCutoffItem[]): Record<LetterGrade, string> {
  const map = Object.fromEntries(gradeScale.map((c) => [c.letter_grade, String(c.min_percent)])) as Record<
    LetterGrade,
    string
  >;
  for (const letter of LETTERS) {
    if (!(letter in map)) map[letter] = "";
  }
  return map;
}