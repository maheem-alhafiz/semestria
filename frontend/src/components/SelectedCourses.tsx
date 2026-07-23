"use client";

import { ApiError, generateSchedules } from "@/lib/api";
import { CourseGroupPicker } from "@/components/CourseGroupPicker";
import { usePlannerStore } from "@/store/plannerStore";

export function SelectedCourses() {
  const termCode = usePlannerStore((s) => s.termCode);
  const selectedCourses = usePlannerStore((s) => s.selectedCourses);
  const removeCourse = usePlannerStore((s) => s.removeCourse);
  const sectionChoices = usePlannerStore((s) => s.sectionChoices);
  const setSchedules = usePlannerStore((s) => s.setSchedules);
  const isGenerating = usePlannerStore((s) => s.isGenerating);
  const setIsGenerating = usePlannerStore((s) => s.setIsGenerating);
  const setError = usePlannerStore((s) => s.setError);

  async function handleGenerate() {
    if (!termCode || selectedCourses.length === 0) return;
    setIsGenerating(true);
    setError(null);
    try {
      // Flatten every selected course's per-slot picks into one flat CRN
      // list -- safe to combine across courses since CRNs are unique
      // within a term (see backend's composite (term_code, crn) key), so
      // the scheduler can tell which course a locked CRN belongs to just
      // by which course's own sections contain it.
      const lockedCrns = Object.values(sectionChoices).flatMap((choicesForCourse) =>
        Object.values(choicesForCourse),
      );

      const response = await generateSchedules({
        term_code: termCode,
        course_ids: selectedCourses.map((c) => c.course_id),
        locked_crns: lockedCrns,
      });
      setSchedules(response.schedules);
      if (response.schedule_count === 0) {
        setError(
          "No conflict-free schedule exists for this combination of courses -- try removing one, or changing a section pick.",
        );
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Schedule generation failed.");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold text-slate-700">Selected Courses</h2>

      {selectedCourses.length === 0 ? (
        <p className="text-sm text-slate-400">
          No courses selected yet -- search above and add some.
        </p>
      ) : (
        <ul className="divide-y divide-slate-200 rounded-md border border-slate-200">
          {selectedCourses.map((course) => (
            <li key={course.course_id} className="px-3 py-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {course.subject} {course.course_number}
                  <span className="ml-2 font-normal text-slate-500">{course.title}</span>
                </span>
                <button
                  onClick={() => removeCourse(course.course_id)}
                  className="text-xs font-medium text-red-500 hover:text-red-600"
                >
                  Remove
                </button>
              </div>
              <CourseGroupPicker courseId={course.course_id} />
            </li>
          ))}
        </ul>
      )}

      <button
        onClick={handleGenerate}
        disabled={selectedCourses.length === 0 || isGenerating}
        className="w-full rounded-md bg-brand px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
      >
        {isGenerating ? "Generating…" : "Generate Schedules"}
      </button>
    </div>
  );
}
