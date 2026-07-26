"use client";

import { useMemo, useState } from "react";

import { createManualFulfillment } from "@/lib/api";
import type { AcademicRecordRead, RequirementGroupRead } from "@/types/api";

interface AssignCourseModalProps {
  group: RequirementGroupRead;
  records: AcademicRecordRead[];
  onClose: () => void;
  onAssigned: () => void; // re-fetch progress after a successful assign
}

export function AssignCourseModal({ group, records, onClose, onAssigned }: AssignCourseModalProps) {
  const [query, setQuery] = useState("");
  const [isSubmitting, setIsSubmitting] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Already-assigned-elsewhere-in-this-group records shouldn't be
  // offered again -- a course can't fulfill the same bucket twice.
  const alreadyAssignedIds = new Set(group.manual_fulfillments.map((mf) => mf.academic_record_id));

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return records
      .filter((r) => !alreadyAssignedIds.has(r.id))
      .filter((r) =>
        q
          ? `${r.subject} ${r.course_number} ${r.title_snapshot}`.toLowerCase().includes(q)
          : true,
      );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [records, query]);

  async function handleAssign(record: AcademicRecordRead) {
    setIsSubmitting(record.id);
    setError(null);
    try {
      await createManualFulfillment({
        requirement_group_id: group.id,
        academic_record_id: record.id,
      });
      onAssigned();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to assign course");
    } finally {
      setIsSubmitting(null);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={onClose}
    >
      <div
        className="max-h-[70vh] w-full max-w-md overflow-hidden rounded-2xl border border-hairline bg-panel p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-medium text-paper">Assign a course</h3>
            <p className="text-xs text-muted">to satisfy &ldquo;{group.label}&rdquo;</p>
          </div>
          <button
            onClick={onClose}
            className="rounded-full px-2 py-1 text-sm text-muted transition-colors hover:text-paper"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <input
          type="text"
          autoFocus
          placeholder="Search your courses…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="mb-3 w-full rounded-lg border border-hairline bg-elevated px-3 py-2 text-sm text-paper outline-none focus:border-accent"
        />

        {error && <p className="mb-2 text-xs text-danger">{error}</p>}

        <div className="max-h-72 space-y-1 overflow-y-auto custom-scrollbar">
          {filtered.length === 0 ? (
            <p className="py-4 text-center text-xs text-muted">
              {records.length === 0
                ? "You don't have any courses on your transcript yet."
                : "No matching courses."}
            </p>
          ) : (
            filtered.map((record) => (
              <button
                key={record.id}
                onClick={() => handleAssign(record)}
                disabled={isSubmitting !== null}
                className="flex w-full items-center justify-between rounded-lg px-3 py-2 text-left text-sm transition-colors hover:bg-elevated disabled:opacity-50"
              >
                <span>
                  <span className="font-medium text-paper">
                    {record.subject} {record.course_number}
                  </span>
                  <span className="ml-1.5 text-xs text-muted">{record.title_snapshot}</span>
                </span>
                <span className="text-xs text-muted">
                  {isSubmitting === record.id ? "Assigning…" : `${record.credit_hours_snapshot} CH`}
                </span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
