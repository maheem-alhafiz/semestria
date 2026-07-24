"use client";

import { useMemo } from "react";

import { colorForCourse } from "@/components/PlannerCourseCard";
import { buildSlotEvents, findConflicts, type PlannerEvent } from "@/lib/plannerEvents";
import { usePlannerBuilderStore } from "@/store/plannerBuilderStore";
import type { Term } from "@/types/api";

const GRID_START_MINUTES = 8 * 60; // 8:00 AM
const GRID_END_MINUTES = 22 * 60; // 10:00 PM
// A bit more squished vertically than a 1:1 minute mapping, per feedback.
const PIXELS_PER_MINUTE = 0.8;
const GRID_HEIGHT = (GRID_END_MINUTES - GRID_START_MINUTES) * PIXELS_PER_MINUTE;

const DAYS: [key: keyof PlannerEvent, label: string][] = [
  ["monday", "Mon"],
  ["tuesday", "Tue"],
  ["wednesday", "Wed"],
  ["thursday", "Thu"],
  ["friday", "Fri"],
  ["saturday", "Sat"],
];

const MEETING_TYPE_LABELS: Record<string, string> = {
  CLAS: "Lecture",
  LECL: "Lecture",
  LAB: "Lab",
  TUT: "Tutorial",
};

function formatMeetingType(type: string): string {
  return MEETING_TYPE_LABELS[type] ?? type;
}

//time formatter helper
function formatEventTime(hhmmss: string): string {
  const parts = hhmmss.split(":");
  const h = Number(parts[0]);
  const m = Number(parts[1]);
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmmss;
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${m.toString().padStart(2, "0")}${period}`;
}

function toMinutes(hhmmss: string): number {
  const parts = hhmmss.split(":").map(Number);
  const h = parts[0] ?? 0;
  const m = parts[1] ?? 0;
  return h * 60 + m;
}

function formatHourLabel(totalMinutes: number): string {
  const h = Math.floor(totalMinutes / 60);
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12} ${period}`;
}

interface TermCalendarProps {
  slot: "top" | "bottom";
  terms: Term[];
}

// No "Top Calendar"/"Bottom Calendar" label -- the term dropdown itself
// is enough context, matching the plainer Semestria styling.
export function TermCalendar({ slot, terms }: TermCalendarProps) {
  const termCode = usePlannerBuilderStore((s) => (slot === "top" ? s.topTermCode : s.bottomTermCode));
  const setTermCode = usePlannerBuilderStore((s) => (slot === "top" ? s.setTopTerm : s.setBottomTerm));
  const selections = usePlannerBuilderStore((s) => s.selections);
  const knownCourses = usePlannerBuilderStore((s) => s.knownCourses);
  const courseSectionsCache = usePlannerBuilderStore((s) => s.courseSectionsCache);

  const events = useMemo(
    () => buildSlotEvents(slot, termCode, selections, courseSectionsCache),
    [slot, termCode, selections, courseSectionsCache],
  );
  const conflicts = useMemo(() => findConflicts(events), [events]);

  const totalCredits = useMemo(() => {
    let sum = 0;
    for (const [idStr, sel] of Object.entries(selections)) {
      const active = slot === "top" ? sel.activeTop : sel.activeBottom;
      if (!active) continue;
      const course = knownCourses[Number(idStr)];
      if (course) sum += course.credit_hours;
    }
    return sum;
  }, [selections, knownCourses, slot]);

  const timedEvents = events.filter((e) => e.startTime && e.endTime);
  const untimedEvents = events.filter((e) => !e.startTime || !e.endTime);

  const hourMarks: number[] = [];
  for (let m = GRID_START_MINUTES; m <= GRID_END_MINUTES; m += 60) hourMarks.push(m);

  return (
    <div className="rounded-2xl border border-hairline bg-panel p-4">
      <div className="mb-3 flex items-center gap-2">
        <select
          value={termCode ?? ""}
          onChange={(e) => setTermCode(e.target.value || null)}
          className="rounded-lg border border-hairline bg-elevated px-2.5 py-1.5 text-sm text-paper focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="">Select a term…</option>
          {terms.map((t) => (
            <option key={t.term_code} value={t.term_code}>
              {t.description}
            </option>
          ))}
        </select>
        {termCode && (
          <span className="rounded-full border border-hairline bg-elevated px-2.5 py-1 text-xs font-medium text-muted">
            {totalCredits} CH
          </span>
        )}
      </div>

      {!termCode ? (
        <p className="py-8 text-center text-sm text-muted">
          Select a term to start building this calendar.
        </p>
      ) : (
        <>
          <div className="flex">
            <div className="relative w-12 shrink-0" style={{ height: GRID_HEIGHT }}>
              {hourMarks.map((m) => (
                <div
                  key={m}
                  className="absolute right-1 text-[10px] text-muted"
                  style={{ top: (m - GRID_START_MINUTES) * PIXELS_PER_MINUTE - 6 }}
                >
                  {formatHourLabel(m)}
                </div>
              ))}
            </div>

            <div
              className="relative flex-1 grid grid-cols-6 gap-px overflow-hidden rounded-xl bg-hairline"
              style={{ height: GRID_HEIGHT }}
            >
              {hourMarks.map((m) => (
                <div
                  key={m}
                  className="pointer-events-none absolute left-0 right-0 border-t border-hairline/80"
                  style={{ top: (m - GRID_START_MINUTES) * PIXELS_PER_MINUTE }}
                />
              ))}

              {DAYS.map(([dayKey, dayLabel]) => (
                <div key={dayKey} className="relative bg-panel">
                  <div className="sticky top-0 z-10 bg-panel pb-1 text-center text-[10px] font-medium text-muted">
                    {dayLabel}
                  </div>
                  {timedEvents
                    .filter((e) => e[dayKey])
                    .map((e, i) => {
                      const start = toMinutes(e.startTime!);
                      const end = toMinutes(e.endTime!);
                      const top = Math.max(0, (start - GRID_START_MINUTES) * PIXELS_PER_MINUTE);
                      const height = Math.max(14, (end - start) * PIXELS_PER_MINUTE);
                      return (
                        <div
                          key={`${e.crn}-${dayKey}-${i}`}
                          className="absolute left-0.5 right-0.5 overflow-hidden rounded-lg px-1.5 py-1 text-[10px] leading-tight text-canvas shadow-sm"
                          style={{
                            top,
                            height,
                            backgroundColor: colorForCourse(e.courseId),
                          }}
                          title={`${e.subject} ${e.courseNumber} — ${e.meetingType} ${e.startTime}-${e.endTime}`}
                        >
                          <div className="font-semibold truncate">
                            {e.subject} {e.courseNumber} {formatMeetingType(e.meetingType)}
                          </div>
                          <div className="text-[10px] opacity-90 truncate">
                            {formatEventTime(e.startTime!)}-{formatEventTime(e.endTime!)}
                          </div>
                        </div>
                      );
                    })}
                </div>
              ))}
            </div>
          </div>

          {untimedEvents.length > 0 && (
            <div className="mt-3 space-y-1 border-t border-hairline pt-2">
              <p className="text-[11px] font-medium text-muted">Async / TBA (no scheduled time):</p>
              {untimedEvents.map((e, i) => (
                <div key={`${e.crn}-untimed-${i}`} className="flex items-center gap-2 text-xs text-paper/80">
                  <span
                    className="h-2 w-2 shrink-0 rounded-sm"
                    style={{ backgroundColor: colorForCourse(e.courseId) }}
                  />
                  {e.subject} {e.courseNumber} — {e.meetingType}
                </div>
              ))}
            </div>
          )}

          {conflicts.length > 0 && (
            <div className="mt-3 space-y-1 rounded-xl border border-danger/40 bg-danger/10 px-3 py-2.5 text-xs text-danger">
              <p className="font-medium">
                ⚠ {conflicts.length} conflict{conflicts.length > 1 ? "s" : ""} — overlap every week:
              </p>
              {conflicts.map((c, i) => (
                <p key={i} className="pl-4 text-danger/90">
                  {c.a.subject} {c.a.courseNumber} ({c.a.meetingType}, {c.a.startTime}–{c.a.endTime}) ↔{" "}
                  {c.b.subject} {c.b.courseNumber} ({c.b.meetingType}, {c.b.startTime}–{c.b.endTime})
                </p>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
