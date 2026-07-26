"use client";

import { useEffect, useState } from "react";

import { ApiError, getCourseDetail } from "@/lib/api";
import type { CourseDetailRead } from "@/types/api";

interface CourseDetailsModalProps {
  courseId: number;
  onClose: () => void;
}

export function CourseDetailsModal({ courseId, onClose }: CourseDetailsModalProps) {
  const [course, setCourse] = useState<CourseDetailRead | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setIsLoading(true);
    setError(null);
    getCourseDetail(courseId)
      .then((data) => {
        if (!cancelled) setCourse(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Couldn't load course details.");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [courseId]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={onClose}
    >
      <div
        className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-hairline bg-panel p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            {course && (
              <>
                <h2 className="text-lg font-medium text-paper">
                  {course.subject} {course.course_number}
                </h2>
                <p className="text-sm text-muted">{course.title}</p>
              </>
            )}
          </div>
          <button
            onClick={onClose}
            className="shrink-0 rounded-full px-2 py-1 text-sm text-muted transition-colors hover:text-paper"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 space-y-4">
          {isLoading && <p className="text-sm text-muted">Loading…</p>}
          {error && <p className="text-sm text-danger">{error}</p>}

          {course && !isLoading && (
            <>
              <div className="flex items-center gap-2 text-xs text-muted">
                <span className="rounded bg-elevated px-2 py-0.5">{course.credit_hours} CH</span>
              </div>

              {course.description ? (
                <p className="text-sm leading-relaxed text-paper">{course.description}</p>
              ) : (
                <p className="text-sm text-muted">No description available.</p>
              )}

              <div className="space-y-2">
                <div className="rounded-lg border border-hairline bg-elevated px-3 py-2">
                  <h3 className="text-xs font-medium uppercase tracking-wider text-muted">
                    Prerequisites
                  </h3>
                  <p className="mt-1 text-sm text-paper">
                    {course.prerequisites_text || "None"}
                  </p>
                </div>
                <div className="rounded-lg border border-hairline bg-elevated px-3 py-2">
                  <h3 className="text-xs font-medium uppercase tracking-wider text-muted">
                    Corequisites
                  </h3>
                  <p className="mt-1 text-sm text-paper">
                    {course.corequisites_text || "None"}
                  </p>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
