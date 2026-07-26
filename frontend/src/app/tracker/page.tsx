"use client";

import { useEffect, useMemo, useState } from "react";
import { useTrackerStore } from "@/store/trackerStore";
import { deleteAcademicRecord, addPastCourse, getTerms, updateAcademicRecord, searchCourses, deleteManualFulfillment } from "@/lib/api";
import type { Term, Course, RequirementGroupRead } from "@/types/api";
import { CourseDetailsModal } from "@/components/CourseDetailsModal";
import { CollapsedElectiveBucket, shouldCollapseGroup } from "@/components/CollapsedElectiveBucket";
import { AssignCourseModal } from "@/components/AssignCourseModal";

const getGradePoints = (grade: string | null): number | null => {
  if (!grade) return null;
  const scale: Record<string, number> = {
    "A+": 4.5, "A": 4.0, "B+": 3.5, "B": 3.0, "C+": 2.5, "C": 2.0, "D": 1.0, "F": 0.0,
  };
  return scale[grade.toUpperCase()] ?? null;
};

// Corrected U of M term code mapping
function getTermInfo(termCode: string, terms: Term[]): { year: string; termName: string } {
  const match = terms.find((t) => t.term_code === termCode);
  const description = match?.description ?? termCode; 
  const year = termCode.substring(0, 4);
  const termName = description.split(" ")[0] || termCode; 
  return { year, termName };
}

function calculateStats(records: any[]) {
  let gpaHours = 0;
  let qualityPoints = 0;
  let earnedHours = 0;
  let completedCourses = 0;

  records.forEach((r) => {
    const pts = getGradePoints(r.grade);
    if (pts !== null) {
      const cr = Number(r.credit_hours_snapshot);
      gpaHours += cr;
      qualityPoints += pts * cr;
      if (pts > 0) {
        earnedHours += cr;
        completedCourses += 1;
      }
    }
  });

  const gpa = gpaHours > 0 ? (qualityPoints / gpaHours).toFixed(2) : "0.00";
  return { gpa, earnedHours, completedCourses };
}

// "3/5 Courses", "12/20 CH", "3/5 Courses · 12/20 CH", or "Satisfied" /
// "Choose 1" for a ONE_OF group (which has no single meaningful count).
function formatGroupProgress(group: RequirementGroupRead): string {
  if (group.kind === "ONE_OF") {
    return group.is_satisfied ? "Satisfied" : "Choose 1";
  }

  const parts: string[] = [];
  if (group.kind === "ALL") {
    parts.push(`${group.completed_count}/${group.courses.length} Courses`);
  } else {
    if (group.courses_required !== null) {
      parts.push(`${group.completed_count}/${group.courses_required} Courses`);
    }
    if (group.credit_hours_required !== null) {
      parts.push(`${group.completed_credit_hours}/${group.credit_hours_required} CH`);
    }
  }
  return parts.length > 0 ? parts.join(" · ") : group.is_satisfied ? "Satisfied" : "Not started";
}

export default function TrackerPage() {
  const {
    records,
    isLoading,
    fetchRecords,
    programs,
    selectedProgramId,
    programProgress,
    isLoadingPrograms,
    isLoadingProgress,
    fetchPrograms,
    selectProgram,
    fetchProgramProgress,
  } = useTrackerStore();
  const [isAddingCourse, setIsAddingCourse] = useState(false);
  const [terms, setTerms] = useState<Term[]>([]);
  
  
  // Course details modal state
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  
  // Form state for adding past course
  const [selectedTermCode, setSelectedTermCode] = useState("");
  const [courseIdInput, setCourseIdInput] = useState("");
  const [gradeInput, setGradeInput] = useState("Planned");

  // Search state
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<Course | null>(null);
  const [assigningGroup, setAssigningGroup] = useState<RequirementGroupRead | null>(null);
  const [swappingTargetCourseId, setSwappingTargetCourseId] = useState<number | null>(null);


  // Live search trigger
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    const delay = setTimeout(() => {
      const termToSearch = selectedTermCode || (terms[0]?.term_code ?? "202610");
      searchCourses(termToSearch, searchQuery)
        .then(setSearchResults)
        .catch(() => setSearchResults([]));
    }, 300);
    return () => clearTimeout(delay);
  }, [searchQuery, selectedTermCode, terms]);

  useEffect(() => {
    fetchRecords();
    fetchPrograms();
    getTerms().then(setTerms).catch(() => {});
  }, [fetchRecords, fetchPrograms]);

  const stats = useMemo(() => {
    let earnedCredits = 0;
    let gradedCredits = 0;
    let qualityPoints = 0;
    const earnedCourses = new Set<string>();

    records.forEach((record) => {
      const pts = getGradePoints(record.grade);
      if (pts !== null) {
        const credits = Number(record.credit_hours_snapshot);
        
        // Quality Points & CGPA include ALL attempts (U of M standard)
        gradedCredits += credits;
        qualityPoints += pts * credits;

        // Earned credits should only be awarded ONCE per unique course
        const courseKey = `${record.subject} ${record.course_number}`;
        if (pts > 0 && !earnedCourses.has(courseKey)) {
          earnedCredits += credits;
          earnedCourses.add(courseKey);
        }
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
      const { year, termName } = getTermInfo(r.term_code, terms);
      if (!grouped[year]) grouped[year] = {};
      if (!grouped[year][termName]) grouped[year][termName] = [];
      grouped[year][termName].push(r);
    });
    return grouped;
  }, [records, terms]);

  async function handleDeleteRecord(id: number) {
    try {
      await deleteAcademicRecord(id);
      fetchRecords(); // Refresh state
      if (selectedProgramId) fetchProgramProgress(selectedProgramId);
    } catch (err) {
      alert("Failed to delete record");
    }
  }

  async function handleGradeChange(recordId: number, newGrade: string) {
    const gradeVal = newGrade === "Planned" ? null : newGrade;
    try {
      await updateAcademicRecord(recordId, { grade: gradeVal });
      fetchRecords();
      if (selectedProgramId) fetchProgramProgress(selectedProgramId);
    } catch {
      alert("Failed to update grade");
    }
  }

  async function handleAddPastCourse(e: React.FormEvent) {
    e.preventDefault();
    if (!courseIdInput) {
      alert("Please search for and select a course first.");
      return;
    }
    try {
      await addPastCourse({
        term_code: selectedTermCode || (terms[0]?.term_code ?? "202610"),
        course_id: parseInt(courseIdInput, 10),
        grade: gradeInput === "Planned" ? null : gradeInput,
      });
      setIsAddingCourse(false);
      setCourseIdInput("");
      setSelectedCourse(null);
      setSearchQuery("");
      fetchRecords();
      if (selectedProgramId) fetchProgramProgress(selectedProgramId);
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
          <div className="flex items-center justify-between gap-2">
            <select
              value={selectedProgramId ?? ""}
              onChange={(e) => selectProgram(Number(e.target.value))}
              disabled={programs.length === 0}
              className="min-w-0 flex-1 truncate rounded-lg border border-hairline bg-elevated px-2 py-1 text-sm font-medium text-paper outline-none focus:border-accent"
            >
              {programs.length === 0 ? (
                <option value="">No degree programs yet</option>
              ) : (
                programs.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))
              )}
            </select>
          </div>

          <div className="space-y-6">
            {isLoadingPrograms || isLoadingProgress ? (
              <p className="text-xs text-muted">Loading requirements…</p>
            ) : !programProgress ? (
              <p className="text-xs text-muted">Select a degree program to see requirements.</p>
            ) : (
              [...programProgress.groups]
                .sort((a, b) => a.sort_order - b.sort_order)
                .map((group) => (
                  <div key={group.id}>
                    <div className="mb-2.5 flex items-center justify-between gap-2">
                      <h3 className="text-xs font-medium uppercase tracking-wider text-muted">
                        {group.label}
                      </h3>
                      <span
                        className={`shrink-0 text-[10px] font-medium ${
                          group.is_satisfied ? "text-accent" : "text-muted"
                        }`}
                      >
                        {group.is_satisfied ? "✓ " : ""}
                        {formatGroupProgress(group)}
                      </span>
                    </div>
                    {shouldCollapseGroup(group) ? (
                      <CollapsedElectiveBucket
                        group={group}
                        records={records}
                        onAssignClick={() => setAssigningGroup(group)}
                        onChanged={() => {
                          if (selectedProgramId) fetchProgramProgress(selectedProgramId);
                        }}
                      />
                    ) : (
                      <div className="space-y-2">
                        {group.courses.length === 0 &&
                          group.patterns.map((p, i) => (
                            <div
                              key={i}
                              className="rounded-lg border border-dashed border-hairline bg-transparent px-3 py-2 text-xs text-muted"
                            >
                              {`Any ${p.subject ?? ""} course, level ${p.level_min}–${p.level_max}`.trim()}
                            </div>
                          ))}
                        {group.courses.length > 0 && (
                          <div className="overflow-hidden rounded-xl border border-hairline bg-transparent divide-y divide-hairline">
                            {group.courses.map((course) => {
                              // Check if this specific course row was manually replaced/satisfied by a transcript record
                              const fulfillment = group.manual_fulfillments?.find(
                                (mf) => mf.replaced_course_id === course.course_id
                              );
                              
                              // Also check if it's auto-satisfied normally
                              const isAutoDone = group.completed_course_ids.includes(course.course_id);
                              
                              // Find the actual record if it was manually overridden
                              const assignedRecord = fulfillment
                                ? records.find((r) => r.id === fulfillment.academic_record_id)
                                : null;

                              return (
                                <div
                                  key={course.course_id}
                                  className="flex items-center justify-between bg-transparent px-4 py-2.5 text-sm transition-colors hover:bg-elevated/40"
                                >
                                  {fulfillment && assignedRecord ? (
                                    // Render the substituted/swapped course
                                    <div className="flex flex-1 items-center justify-between pr-2">
                                      <span className="font-medium text-paper">
                                        <span className="mr-1.5 text-accent">✓</span>
                                        <span className="line-through text-muted mr-2">
                                          {course.subject} {course.course_number}
                                        </span>
                                        <span className="text-accent font-semibold">
                                          {assignedRecord.subject} {assignedRecord.course_number}
                                        </span>
                                        <span className="ml-1.5 text-xs text-muted font-normal">
                                          (Swapped)
                                        </span>
                                      </span>
                                      <div className="flex items-center gap-2">
                                        <button
                                          onClick={async () => {
                                            try {
                                              await deleteManualFulfillment(fulfillment.id);
                                              if (selectedProgramId) fetchProgramProgress(selectedProgramId);
                                            } catch {
                                              alert("Failed to remove swap");
                                            }
                                          }}
                                          className="text-xs text-muted transition-colors hover:text-danger"
                                        >
                                          Reset
                                        </button>
                                      </div>
                                    </div>
                                  ) : (
                                    // Standard course row with a Swap option
                                    <>
                                      <span
                                        className={
                                          isAutoDone ? "font-medium text-muted line-through cursor-pointer" : "font-medium text-paper cursor-pointer"
                                        }
                                        onClick={() => setSelectedCourseId(course.course_id)}
                                      >
                                        {isAutoDone && <span className="mr-1.5 text-accent no-underline">✓</span>}
                                        {course.subject} {course.course_number}
                                      </span>
                                      <div className="flex items-center gap-3">
                                        <span className="text-xs text-muted">{course.credit_hours} CH</span>
                                        {!isAutoDone && (
                                          <button
                                            onClick={() => {
                                              setAssigningGroup(group);
                                              setSwappingTargetCourseId(course.course_id);
                                            }}
                                            className="rounded border border-hairline bg-elevated px-2 py-0.5 text-[11px] font-medium text-paper transition-colors hover:border-accent"
                                          >
                                            Swap
                                          </button>
                                        )}
                                      </div>
                                    </>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))
            )}
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
            Object.keys(transcript).sort().map((year) => {
              // Calculate AGPA and Year Stats
              const yearRecords = Object.values(transcript[year] || {}).flat();
              const yearStats = calculateStats(yearRecords);

              return (
                <div key={year} className="overflow-hidden rounded-2xl border border-hairline bg-panel shadow-sm">
                  <div className="flex items-end justify-between border-b border-hairline bg-elevated px-6 py-4">
                    <div>
                      <h2 className="text-2xl font-bold text-paper">{year}</h2>
                    </div>
                    {/* Year Stats Display */}
                    <div className="flex items-center gap-6 text-right">
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Courses</span>
                        <span className="text-sm font-medium text-paper">{yearStats.completedCourses}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-muted">Earned CH</span>
                        <span className="text-sm font-medium text-paper">{yearStats.earnedHours}</span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-[10px] font-bold uppercase tracking-wider text-accent">AGPA</span>
                        <span className="text-sm font-medium text-paper">{yearStats.gpa}</span>
                      </div>
                    </div>
                  </div>

                  {Object.keys(transcript[year] || {}).map((term) => {
                    // Calculate TGPA
                    const termRecords = transcript[year]?.[term] || [];
                    const termStats = calculateStats(termRecords);

                    return (
                      <div key={term} className="border-b border-hairline p-6 last:border-0">
                        <div className="mb-4 flex items-center justify-between">
                          <h3 className="text-sm font-semibold text-paper">{term}</h3>
                          {/* TGPA Display */}
                          <span className="rounded-lg bg-elevated px-2.5 py-1 text-xs font-medium text-muted">
                            TGPA: <span className="font-semibold text-paper">{termStats.gpa}</span>
                          </span>
                        </div>

                        {/* Table Container */}
                        <div className="overflow-hidden rounded-xl border border-hairline bg-elevated/20">
                          {/* Table Header */}
                          <div className="grid grid-cols-12 border-b border-hairline bg-elevated/50 px-4 py-2 text-[10px] font-medium uppercase tracking-wider text-muted">
                            <span className="col-span-3">Code</span>
                            <span className="col-span-5">Title</span>
                            <span className="col-span-1 text-center">CH</span>
                            <span className="col-span-2 text-center">Grade</span>
                            <span className="col-span-1 text-right">Points</span>
                          </div>

                          {/* Table Rows */}
                          <div className="divide-y divide-hairline">
                            {(transcript[year]?.[term] || []).map((record) => {
                              const pts = getGradePoints(record.grade);
                              const cr = Number(record.credit_hours_snapshot);
                              const rowPoints = pts !== null ? (pts * cr).toFixed(2) : "—";

                              return (
                                <div key={record.id} className="grid grid-cols-12 items-center px-4 py-2.5 text-sm transition-colors hover:bg-elevated/40 group">
                                  <span className="col-span-3 font-medium text-paper">
                                    {`${record.subject} ${record.course_number}`}
                                  </span>
                                  <span className="col-span-5 truncate text-muted">{record.title_snapshot}</span>
                                  <span className="col-span-1 text-center text-muted">{cr.toFixed(0)}</span>
                                  
                                  {/* Grade Dropdown */}
                                  <div className="col-span-2 flex justify-center">
                                    <select
                                      value={record.grade || "Planned"}
                                      onChange={(e) => handleGradeChange(record.id, e.target.value)}
                                      className="appearance-none rounded-lg border border-hairline bg-elevated px-2 py-1 text-xs text-paper outline-none transition-colors hover:border-muted focus:border-accent"
                                    >
                                      <option value="Planned">Planned</option>
                                      <option value="IP">IP</option>
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

                                  {/* Points & Delete Action */}
                                  <div className="col-span-1 flex items-center justify-end gap-2 text-right">
                                    <span className="text-muted">{rowPoints}</span>
                                    <button
                                      onClick={() => handleDeleteRecord(record.id)}
                                      className="opacity-0 group-hover:opacity-100 text-muted transition-opacity hover:text-danger"
                                      title="Remove"
                                    >
                                      ✕
                                    </button>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })
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
                  <option key={t.term_code} value={t.term_code}>{t.description}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-muted mb-1">Course</label>
              {selectedCourse ? (
                <div className="flex items-center justify-between rounded-xl border border-accent bg-elevated px-3 py-2 text-sm text-paper">
                  <span className="font-medium text-paper">
                    {selectedCourse.subject} {selectedCourse.course_number} <span className="ml-1 font-normal text-muted truncate">{selectedCourse.title}</span>
                  </span>
                  <button 
                    type="button" 
                    onClick={() => { setSelectedCourse(null); setCourseIdInput(""); }} 
                    className="text-muted transition-colors hover:text-danger"
                  >
                    ✕
                  </button>
                </div>
              ) : (
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search courses (e.g. MECH 2112)"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper outline-none focus:border-accent"
                  />
                  {searchResults.length > 0 && (
                    <div className="absolute z-10 mt-2 max-h-48 w-full overflow-y-auto rounded-xl border border-hairline bg-panel shadow-lg custom-scrollbar">
                      {searchResults.map((course) => (
                        <button
                          key={course.course_id}
                          type="button"
                          onClick={() => {
                            setSelectedCourse(course);
                            setCourseIdInput(course.course_id.toString());
                            setSearchQuery("");
                            setSearchResults([]);
                          }}
                          className="flex w-full flex-col px-4 py-2.5 text-left transition-colors hover:bg-elevated"
                        >
                          <span className="text-sm font-medium text-paper">{course.subject} {course.course_number}</span>
                          <span className="text-xs text-muted truncate">{course.title}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
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

      {/* Course Details Modal */}
      {selectedCourseId && (
        <CourseDetailsModal 
          courseId={selectedCourseId} 
          onClose={() => setSelectedCourseId(null)} 
        />
      )}

      {/* Assign Course Modal */}
      {assigningGroup && (
        <AssignCourseModal
          group={assigningGroup}
          records={records}
          replacedCourseId={swappingTargetCourseId}
          onClose={() => {
            setAssigningGroup(null);
            setSwappingTargetCourseId(null);
          }}
          onAssigned={() => {
            if (selectedProgramId) fetchProgramProgress(selectedProgramId);
          }}
        />
      )}
    </main>
  );
}