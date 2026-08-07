"use client";

import { useState } from "react";

import { AddAssessmentCourseSearch } from "@/components/AddAssessmentCourseSearch";
import { GradeScaleModal } from "@/components/GradeScaleModal";
import { projectCourseGrade, projectTermGpa } from "@/lib/gradeMath";
import { useAssessmentsStore } from "@/store/assessmentsStore";

export function CourseGradeList({ termCode }: { termCode: string }) {
  const courses = useAssessmentsStore((s) => s.courses);
  const assessments = useAssessmentsStore((s) => s.assessments);
  const gradeScales = useAssessmentsStore((s) => s.gradeScales);
  const removeCourse = useAssessmentsStore((s) => s.removeCourse);

  const [scaleModalCourseId, setScaleModalCourseId] = useState<number | null>(null);

  const rows = courses.map((c) => {
    const courseAssessments = assessments.filter((a) => a.course_id === c.course_id);
    const scale = gradeScales[c.course_id];
    const projection = projectCourseGrade(courseAssessments, scale || []);
    return { course: c, projection, hasScale: !!scale };
  });

  const termGpa = projectTermGpa(
    rows.map((r) => ({ creditHours: r.course.credit_hours, projection: r.projection }))
  );

  return (
    <div className="rounded-2xl border border-hairline bg-panel p-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-paper">Courses</h2>
          {termGpa != null && (
            <p className="mt-0.5 text-xs text-muted">
              Estimated term GPA: <span className="font-medium text-paper">{termGpa.toFixed(2)}</span>
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <AddAssessmentCourseSearch termCode={termCode} />
        </div>
      </div>

      {courses.length === 0 ? (
        <p className="mt-4 text-sm text-muted">
          No courses tracked yet. Courses you&apos;ve finalized (via Mark as Final on a Plan) for
          this term will show up here automatically, or add one manually above.
        </p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map(({ course, projection, hasScale }) => (
            <div key={course.course_id} className="flex flex-col rounded-xl border border-hairline bg-elevated p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-paper">
                    {course.subject} {course.course_number}
                  </p>
                  <p className="truncate text-xs text-muted">{course.title}</p>
                </div>
                {course.source === "manual" && (
                  <button
                    onClick={() => removeCourse(course.course_id)}
                    className="shrink-0 text-muted hover:text-danger"
                    aria-label={`Remove ${course.subject} ${course.course_number}`}
                  >
                    ×
                  </button>
                )}
              </div>

              <div className="mt-2.5">
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-panel">
                  <div
                    className="h-full rounded-full bg-accent"
                    style={{ width: `${Math.min(100, projection.gradedWeightPercent)}%` }}
                  />
                </div>
                <div className="mt-1 flex items-center justify-between">
                  <p className="text-[11px] text-muted">
                    {projection.gradedWeightPercent.toFixed(0)}% of graded weight recorded
                  </p>
                </div>
              </div>

              <div className="mt-2 flex flex-1 items-end justify-between">
                <div className="text-xs">
                  {projection.predictedFinalPercent != null ? (
                    <p className="text-paper">
                      Current standing:{" "}
                      <span className="font-medium">{projection.predictedFinalPercent.toFixed(1)}%</span>
                      {projection.predictedLetter && (
                        <span className="text-muted">
                          {" "}
                          ({projection.predictedLetter})
                        </span>
                      )}
                    </p>
                  ) : (
                    <p className="text-muted">No grades recorded yet</p>
                  )}
                  {!hasScale && (
                    <p className="mt-1 text-[11px] font-medium text-warning">
                      Grading scale not added
                    </p>
                  )}
                </div>
                
                <button
                  onClick={() => setScaleModalCourseId(course.course_id)}
                  className="shrink-0 rounded-lg border border-hairline bg-panel px-2 py-1 text-[11px] font-medium text-muted transition-colors hover:border-accent hover:text-paper"
                >
                  Set Scale
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <GradeScaleModal 
        courseId={scaleModalCourseId} 
        isOpen={scaleModalCourseId !== null} 
        onClose={() => setScaleModalCourseId(null)} 
      />
    </div>
  );
}