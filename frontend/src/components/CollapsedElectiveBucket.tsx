"use client";

import { useState } from "react";

import { deleteManualFulfillment } from "@/lib/api";
import type { AcademicRecordRead, RequirementGroupRead } from "@/types/api";

// A group is treated as a "massive elective bucket" -- collapse the
// option list instead of dumping every row -- once it crosses this many
// courses OR has any pattern-based membership (patterns imply an
// unbounded/very large option set by nature, e.g. "any 1000-level HIST
// course", so always collapse those regardless of explicit course count).
const COLLAPSE_THRESHOLD = 6;

export function shouldCollapseGroup(group: RequirementGroupRead): boolean {
  return group.courses.length > COLLAPSE_THRESHOLD || group.patterns.length > 0;
}

interface CollapsedElectiveBucketProps {
  group: RequirementGroupRead;
  records: AcademicRecordRead[];
  onAssignClick: () => void;
  onChanged: () => void; // re-fetch progress after assign/unassign
}

export function CollapsedElectiveBucket({
  group,
  records,
  onAssignClick,
  onChanged,
}: CollapsedElectiveBucketProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [removingId, setRemovingId] = useState<number | null>(null);

  const recordsById = new Map(records.map((r) => [r.id, r]));

  async function handleRemove(fulfillmentId: number) {
    setRemovingId(fulfillmentId);
    try {
      await deleteManualFulfillment(fulfillmentId);
      onChanged();
    } catch {
      alert("Failed to remove assignment");
    } finally {
      setRemovingId(null);
    }
  }

  return (
    <div className="space-y-2">
      {/* Manually-assigned courses -- these are the ONLY thing shown by
          default for a collapsed bucket, since they're the actionable
          part (the student can remove them). Auto-matched completions
          that came from the explicit course list still count toward
          is_satisfied/completed_count, they just aren't re-listed here
          individually -- the full option list is behind "Show all". */}
      {group.manual_fulfillments.length > 0 && (
        <div className="space-y-1.5">
          {group.manual_fulfillments.map((mf) => {
            const record = recordsById.get(mf.academic_record_id);
            return (
              <div
                key={mf.id}
                className="flex items-center justify-between rounded-lg border border-accent/40 bg-accent/10 px-3 py-2 text-sm"
              >
                <span className="font-medium text-paper">
                  <span className="mr-1.5 text-accent">✓</span>
                  {record ? `${record.subject} ${record.course_number}` : `Record #${mf.academic_record_id}`}
                  <span className="ml-1.5 text-xs font-normal text-muted">(manually assigned)</span>
                </span>
                <button
                  onClick={() => handleRemove(mf.id)}
                  disabled={removingId === mf.id}
                  className="text-xs text-muted transition-colors hover:text-danger disabled:opacity-50"
                >
                  {removingId === mf.id ? "Removing…" : "Remove"}
                </button>
              </div>
            );
          })}
        </div>
      )}

      <div className="flex items-center gap-2">
        <button
          onClick={onAssignClick}
          className="rounded-lg border border-hairline bg-elevated px-3 py-1.5 text-xs font-medium text-paper transition-colors hover:border-accent"
        >
          + Assign a course
        </button>
        <button
          onClick={() => setIsExpanded((v) => !v)}
          className="text-xs text-muted transition-colors hover:text-paper"
        >
          {isExpanded
            ? "Hide options"
            : group.courses.length > 0
              ? `Show all ${group.courses.length} options`
              : "Show pattern rules"}
        </button>
      </div>

      {isExpanded && (
        <div className="max-h-64 space-y-1.5 overflow-y-auto rounded-lg border border-hairline bg-panel p-2 custom-scrollbar">
          {group.courses.map((course) => {
            const isDone = group.completed_course_ids.includes(course.course_id);
            return (
              <div
                key={course.course_id}
                className="flex items-center justify-between rounded-md px-2 py-1 text-xs"
              >
                <span className={isDone ? "text-muted line-through" : "text-paper"}>
                  {isDone && <span className="mr-1 text-accent no-underline">✓</span>}
                  {course.subject} {course.course_number}
                </span>
                <span className="text-muted">{course.credit_hours} CH</span>
              </div>
            );
          })}
          {group.patterns.map((p, i) => (
            <div key={i} className="px-2 py-1 text-xs text-muted">
              {`Any ${p.subject ?? ""} course, level ${p.level_min}–${p.level_max}`.trim()}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
