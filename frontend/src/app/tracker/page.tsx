"use client";

import { useEffect, useMemo, useState } from "react";
import { useTrackerStore } from "@/store/trackerStore";
import { deleteAcademicRecord, addPastCourse, getTerms } from "@/lib/api";
import type { Term } from "@/types/api";

const getGradePoints = (grade: string | null): number | null => {
  if (!grade) return null;
  const scale: Record<string, number> = {
    "A+": 4.5, "A": 4.0, "B+": 3.5, "B": 3.0, "C+": 2.5, "C": 2.0, "D": 1.0, "F": 0.0,
  };
  return scale[grade.toUpperCase()] ?? null;
};

// Corrected U of M term code mapping
const parseTermCode = (termCode: string) => {
  const year = termCode.substring(0, 4);
  const suffix = termCode.substring(4);
  let termName = termCode;
  if (suffix === "10") termName = "Fall";
  else if (suffix === "30") termName = "Summer";
  else if (suffix === "50") termName = "Winter";
  
  return { year, termName };
};

export default function TrackerPage() {
  const { records, isLoading, fetchRecords } = useTrackerStore();
  const [isAddingCourse, setIsAddingCourse] = useState(false);
  const [terms, setTerms] = useState<Term[]>([]);
  
  // Form state for adding past course
  const [selectedTermCode, setSelectedTermCode] = useState("");
  const [courseIdInput, setCourseIdInput] = useState("");
  const [gradeInput, setGradeInput] = useState("Planned");

  useEffect(() => {
    fetchRecords();
    getTerms().then(setTerms).catch(() => {});
  }, [fetchRecords]);

  const stats = useMemo(() => {
    let earnedCredits = 0;
    let gradedCredits = 0;
    let qualityPoints = 0;

    records.forEach((record) => {
      const pts = getGradePoints(record.grade);
      if (pts !== null) {
        const credits = Number(record.credit_hours_snapshot);
        if (pts > 0) earnedCredits += credits; 
        gradedCredits += credits;
        qualityPoints += pts * credits;
      }
    });

    const cgpa = gradedCredits > 0 ? (qualityPoints / gradedCredits).toFixed(2) : "0.00";
    return {
      earnedCredits: earnedCredits.toFixed(1),
      qualityPoints: qualityPoints.toFixed(2),
      cgpa,
    };
  }, [records]);

  const transcript = useMemo(() => {
    const grouped: Record<string, Record<string, typeof records>> = {};
    records.forEach((r) => {
      const { year, termName } = parseTermCode(r.term_code);
      if (!grouped[year]) grouped[year] = {};
      if (!grouped[year][termName]) grouped[year][termName] = [];
      grouped[year][termName].push(r);
    });
    return grouped;
  }, [records]);

  async function handleDeleteRecord(id: number) {
    try {
      await deleteAcademicRecord(id);
      fetchRecords(); // Refresh state
    } catch (err) {
      alert("Failed to delete record");
    }
  }

  async function handleAddPastCourse(e: React.FormEvent) {
    e.preventDefault();
    try {
      await addPastCourse({
        term_code: selectedTermCode || (terms[0]?.term_code ?? "202610"),
        course_id: parseInt(courseIdInput, 10),
        grade: gradeInput === "Planned" ? null : gradeInput,
      });
      setIsAddingCourse(false);
      setCourseIdInput("");
      fetchRecords();
    } catch (err: any) {
      alert(err.message || "Failed to add course");
    }
  }

  if (isLoading) {
    return (
      <main className="mx-auto flex max-w-[1600px] items-center justify-center px-6 py-20">
        <p className="text-muted">Loading academic record...</p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-[1600px] space-y-6 px-6 py-10">
      <header className="mb-2 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-paper">Degree Tracker</h1>
          <p className="text-sm text-muted">Track your progress and plan your prerequisite chains.</p>
        </div>
        <button
          onClick={() => setIsAddingCourse(true)}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-canvas transition-colors hover:opacity-90"
        >
          Add past course
        </button>
      </header>

      {/* Top Dashboard: Dynamic Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-2xl border border-hairline bg-panel p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">Total Credits Earned</p>
          <p className="mt-1 text-3xl font-semibold text-paper">{stats.earnedCredits}</p>
        </div>
        <div className="rounded-2xl border border-hairline bg-panel p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">Total Quality Points</p>
          <p className="mt-1 text-3xl font-semibold text-paper">{stats.qualityPoints}</p>
        </div>
        <div className="rounded-2xl border border-hairline bg-panel p-5 shadow-sm">
          <p className="text-xs font-medium uppercase tracking-wider text-muted">CGPA</p>
          <p className="mt-1 text-3xl font-semibold text-accent">{stats.cgpa}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-12">
        {/* Left Column: Requirements Sidebar */}
        <div className="sticky top-24 space-y-5 rounded-2xl border border-hairline bg-panel p-5 shadow-sm lg:col-span-4 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto custom-scrollbar">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-medium text-paper">Mechanical Engineering B.Sc.</h2>
            <span className="rounded bg-elevated px-2 py-0.5 text-[10px] uppercase text-muted">Pending Catalog Sync</span>
          </div>
          
          <div className="space-y-6">
            <div>
              <h3 className="mb-2.5 text-xs font-medium uppercase tracking-wider text-muted">Preliminary Core</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between rounded-lg border border-hairline bg-transparent px-3 py-2 text-sm">
                  <span className="font-medium text-paper">MATH 1510</span>
                  <span className="text-xs text-muted">3.0 CH</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Dynamic Chronological Transcript */}
        <div className="space-y-6 lg:col-span-8">
          {Object.keys(transcript).length === 0 ? (
            <div className="rounded-2xl border border-dashed border-hairline bg-panel/50 p-10 text-center">
              <p className="text-paper">Your transcript is empty.</p>
              <p className="text-sm text-muted">Go to the Planner tab and &quot;Finalize&quot; a plan to see it here.</p>
            </div>
          ) : (
            Object.keys(transcript).sort().map((year) => (
              <div key={year} className="overflow-hidden rounded-2xl border border-hairline bg-panel shadow-sm">
                <div className="flex items-end justify-between border-b border-hairline bg-elevated px-6 py-4">
                  <div>
                    <h2 className="text-2xl font-bold text-paper">{year}</h2>
                  </div>
                </div>

                {Object.keys(transcript[year] || {}).map((term) => (
                  <div key={term} className="border-b border-hairline p-6 last:border-0">
                    <div className="mb-4 flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-paper">{term}</h3>
                    </div>

                    {/* Unified Semester Box with Clean Dividers */}
                    <div className="divide-y divide-hairline rounded-xl border border-hairline bg-elevated/20">
                      {(transcript[year]?.[term] || []).map((record) => (
                        <div key={record.id} className="flex items-center justify-between px-4 py-3 transition-colors hover:bg-elevated/50">
                          <div className="flex flex-1 items-center gap-4">
                            <span className="flex-1 truncate text-sm font-medium text-paper">{record.title_snapshot}</span>
                          </div>
                          <div className="flex items-center gap-4 md:gap-8">
                            <span className="w-12 text-sm text-muted">{Number(record.credit_hours_snapshot).toFixed(1)} CH</span>
                            
                            <span className="text-sm font-medium text-paper">{record.grade || "Planned"}</span>

                            {/* Delete single record button */}
                            <button
                              onClick={() => handleDeleteRecord(record.id)}
                              className="text-muted transition-colors hover:text-danger"
                              title="Remove from tracker"
                            >
                              ✕
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Modal for Adding Past Course */}
      {isAddingCourse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/80 p-4 backdrop-blur-sm">
          <form onSubmit={handleAddPastCourse} className="w-full max-w-md rounded-2xl border border-hairline bg-panel p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-medium text-paper">Add Past Course</h3>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-muted mb-1">Term</label>
              <select
                value={selectedTermCode}
                onChange={(e) => setSelectedTermCode(e.target.value)}
                className="w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper outline-none focus:border-accent"
              >
                {terms.map((t) => (
                  <option key={t.term_code} value={t.term_code}>{t.description} ({t.term_code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-muted mb-1">Course ID (Internal Database ID)</label>
              <input
                type="number"
                placeholder="e.g. 123"
                value={courseIdInput}
                onChange={(e) => setCourseIdInput(e.target.value)}
                required
                className="w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-muted mb-1">Grade</label>
              <select
                value={gradeInput}
                onChange={(e) => setGradeInput(e.target.value)}
                className="w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper outline-none focus:border-accent"
              >
                <option value="Planned">Planned / In Progress</option>
                <option value="A+">A+</option>
                <option value="A">A</option>
                <option value="B+">B+</option>
                <option value="B">B</option>
                <option value="C+">C+</option>
                <option value="C">C</option>
                <option value="D">D</option>
                <option value="F">F</option>
              </select>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setIsAddingCourse(false)}
                className="rounded-xl px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-elevated"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-canvas transition-colors hover:opacity-90"
              >
                Add Course
              </button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}