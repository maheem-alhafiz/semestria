"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError, searchCourses } from "@/lib/api";
import { useAssessmentsStore } from "@/store/assessmentsStore";
import type { Course } from "@/types/api";

interface AddAssessmentCourseSearchProps {
  termCode: string;
}

// Manual side of "auto-pull from Plan, but let me add one by hand" -- see
// backend app.models.assessment's docstring. Searches the same catalog
// endpoint the Planner uses (GET /courses?term_code=...&q=...).
export function AddAssessmentCourseSearch({ termCode }: AddAssessmentCourseSearchProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Course[]>([]);
  const [searching, setSearching] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const courses = useAssessmentsStore((s) => s.courses);
  const addCourse = useAssessmentsStore((s) => s.addCourse);
  const trackedIds = new Set(courses.map((c) => c.course_id));

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (!open || query.trim().length < 2) {
      setResults([]);
      return;
    }
    setSearching(true);
    const handle = setTimeout(() => {
      searchCourses(termCode, query.trim())
        .then(setResults)
        .catch(() => setResults([]))
        .finally(() => setSearching(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [query, open, termCode]);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="rounded-full border border-hairline px-3 py-1.5 text-xs font-medium text-muted transition-colors hover:border-accent hover:text-paper"
      >
        + Add course
      </button>

      {open && (
        <div className="absolute left-0 top-full z-30 mt-1.5 w-72 rounded-2xl border border-hairline bg-elevated p-2 shadow-2xl">
          <input
            autoFocus
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search e.g. MECH 2202"
            className="w-full rounded-xl border border-hairline bg-panel px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <div className="mt-1.5 max-h-64 overflow-y-auto">
            {searching && <p className="px-2 py-2 text-xs text-muted">Searching…</p>}
            {!searching && query.trim().length >= 2 && results.length === 0 && (
              <p className="px-2 py-2 text-xs text-muted">No courses found.</p>
            )}
            {results.map((course) => {
              const already = trackedIds.has(course.course_id);
              return (
                <button
                  key={course.course_id}
                  disabled={already}
                  onClick={async () => {
                    await addCourse(course.course_id);
                    setQuery("");
                    setResults([]);
                    setOpen(false);
                  }}
                  className="flex w-full items-center justify-between gap-2 rounded-lg px-2 py-2 text-left text-sm hover:bg-panel/60 disabled:opacity-40"
                >
                  <span className="min-w-0 truncate text-paper">
                    {course.subject} {course.course_number}
                    <span className="ml-1.5 truncate text-xs text-muted">{course.title}</span>
                  </span>
                  {already && <span className="shrink-0 text-[11px] text-muted">Added</span>}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
