"use client";

import { useState } from "react";

import { ApiError, searchCourses } from "@/lib/api";
import { usePlannerStore } from "@/store/plannerStore";

export function CourseSearch() {
  const [query, setQuery] = useState("");

  const termCode = usePlannerStore((s) => s.termCode);
  const searchResults = usePlannerStore((s) => s.searchResults);
  const setSearchResults = usePlannerStore((s) => s.setSearchResults);
  const isSearching = usePlannerStore((s) => s.isSearching);
  const setIsSearching = usePlannerStore((s) => s.setIsSearching);
  const selectedCourses = usePlannerStore((s) => s.selectedCourses);
  const addCourse = usePlannerStore((s) => s.addCourse);
  const setError = usePlannerStore((s) => s.setError);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!termCode) {
      setError("Select a term before searching for courses.");
      return;
    }
    setIsSearching(true);
    setError(null);
    try {
      setSearchResults(await searchCourses(termCode, query));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Course search failed.");
    } finally {
      setIsSearching(false);
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          type="text"
          placeholder="e.g. MECH 2202 or Thermodynamics"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          disabled={!termCode}
          className="flex-1 rounded-md border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!termCode || isSearching}
          className="rounded-md bg-brand px-4 py-1.5 text-sm font-medium text-white disabled:opacity-40"
        >
          {isSearching ? "Searching…" : "Search"}
        </button>
      </form>

      {searchResults.length > 0 && (
        <ul className="max-h-72 divide-y divide-slate-200 overflow-y-auto rounded-md border border-slate-200">
          {searchResults.map((course) => {
            const alreadyAdded = selectedCourses.some((c) => c.course_id === course.course_id);
            return (
              <li
                key={course.course_id}
                className="flex items-center justify-between gap-3 px-3 py-2 text-sm"
              >
                <span className="truncate">
                  <span className="font-medium">
                    {course.subject} {course.course_number}
                  </span>
                  <span className="text-slate-500"> — {course.title}</span>
                </span>
                <button
                  onClick={() => addCourse(course)}
                  disabled={alreadyAdded}
                  className="shrink-0 rounded-md border border-brand px-2 py-1 text-xs font-medium text-brand disabled:border-slate-300 disabled:text-slate-400"
                >
                  {alreadyAdded ? "Added" : "Add"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
