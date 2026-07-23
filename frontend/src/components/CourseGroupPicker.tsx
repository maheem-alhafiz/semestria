"use client";

import { useEffect } from "react";

import { ApiError, getCourseSections } from "@/lib/api";
import { usePlannerStore } from "@/store/plannerStore";
import type { SectionOption } from "@/types/api";

const DAY_ABBREV: [key: keyof SectionOption["meeting_times"][number], label: string][] = [
  ["monday", "Mon"],
  ["tuesday", "Tue"],
  ["wednesday", "Wed"],
  ["thursday", "Thu"],
  ["friday", "Fri"],
  ["saturday", "Sat"],
  ["sunday", "Sun"],
];

// "HH:MM:SS" -> "10:30 AM". Falls back to the raw string if it doesn't
// parse (shouldn't happen given the API's typed contract, but a display
// glitch is better than a crash on unexpected data).
function formatClockTime(hhmmss: string): string {
  const [hStr, mStr] = hhmmss.split(":");
  const h = Number(hStr);
  const m = Number(mStr);
  if (Number.isNaN(h) || Number.isNaN(m)) return hhmmss;
  const period = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${m.toString().padStart(2, "0")} ${period}`;
}

function formatMeeting(mt: SectionOption["meeting_times"][number]): string {
  const days = DAY_ABBREV.filter(([key]) => mt[key]).map(([, label]) => label);
  const dayPart = days.length > 0 ? days.join("") : "TBA";
  const timePart =
    mt.start_time && mt.end_time
      ? `${formatClockTime(mt.start_time)}\u2013${formatClockTime(mt.end_time)}`
      : "no scheduled time";
  return `${mt.meeting_type} ${dayPart} ${timePart}`;
}

function optionLabel(option: SectionOption): string {
  const meetings = option.meeting_times.map(formatMeeting).join(" · ");
  const instructor = option.instructor ? ` · ${option.instructor}` : "";
  return `${option.section_number}${instructor}${meetings ? ` · ${meetings}` : ""}`;
}

// Matches the key format documented in plannerStore.ts's SlotKey type --
// keep these in sync, both sides need to agree on the same string.
function slotKey(linkGroupId: number | null, linkSlot: string): string {
  return `${linkGroupId ?? "solo"}:${linkSlot}`;
}

export function CourseGroupPicker({ courseId }: { courseId: number }) {
  const termCode = usePlannerStore((s) => s.termCode);
  const courseSections = usePlannerStore((s) => s.courseSections[courseId]);
  const setCourseSections = usePlannerStore((s) => s.setCourseSections);
  const choices = usePlannerStore((s) => s.sectionChoices[courseId]);
  const setSectionChoice = usePlannerStore((s) => s.setSectionChoice);
  const setError = usePlannerStore((s) => s.setError);

  useEffect(() => {
    if (!termCode || courseSections) return;
    let cancelled = false;
    getCourseSections(courseId, termCode)
      .then((data) => {
        if (!cancelled) setCourseSections(courseId, data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Couldn't load sections.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [courseId, termCode, courseSections, setCourseSections, setError]);

  // Seeds every slot's default (first) option into real store state as
  // soon as data loads, instead of leaving it purely a display fallback.
  // Without this, a slot whose default happens to be what the student
  // wants never gets an onChange event (the <select> already shows that
  // value, so choosing it again fires nothing) -- sectionChoices stays
  // empty, nothing gets locked, and Generate Schedules silently treats
  // every option as still valid instead of respecting the pick. Reads
  // current choices imperatively via getState() rather than the reactive
  // hook value so this doesn't need `choices` in the dependency array
  // (which would re-run every time a choice changes, not just on load).
  useEffect(() => {
    if (!courseSections) return;
    const currentChoices = usePlannerStore.getState().sectionChoices[courseId] ?? {};
    for (const group of courseSections.groups) {
      for (const slot of group.slots) {
        const key = slotKey(group.link_group_id, slot.link_slot);
        if (!currentChoices[key] && slot.options[0]) {
          setSectionChoice(courseId, key, slot.options[0].crn);
        }
      }
    }
  }, [courseSections, courseId, setSectionChoice]);

  if (!courseSections) {
    return <p className="pl-4 py-1 text-xs text-slate-400">Loading sections…</p>;
  }

  if (courseSections.groups.length === 0) {
    return <p className="pl-4 py-1 text-xs text-slate-400">No sections found for this term.</p>;
  }

  return (
    <div className="mt-1 space-y-2 border-l-2 border-slate-200 pl-4 py-2">
      {courseSections.groups.map((group, groupIndex) => (
        <div key={group.link_group_id ?? `standalone-${groupIndex}`} className="space-y-1.5">
          {group.slots.map((slot) => {
            const key = slotKey(group.link_group_id, slot.link_slot);
            const selected = choices?.[key] ?? slot.options[0]?.crn;
            const hasChoice = slot.options.length > 1;

            return (
              <label key={key} className="flex flex-col gap-0.5 text-xs">
                <span className="font-medium text-slate-600">
                  {slot.link_slot}
                  {hasChoice && (
                    <span className="ml-1 font-normal text-slate-400">
                      (pick 1 of {slot.options.length})
                    </span>
                  )}
                </span>
                {hasChoice ? (
                  <select
                    value={selected}
                    onChange={(e) => setSectionChoice(courseId, key, e.target.value)}
                    className="rounded-md border border-slate-300 px-2 py-1 text-xs"
                  >
                    {slot.options.map((option) => (
                      <option key={option.crn} value={option.crn}>
                        {optionLabel(option)}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="text-slate-500">
                    {slot.options[0] ? optionLabel(slot.options[0]) : "—"}
                  </span>
                )}
              </label>
            );
          })}
        </div>
      ))}
    </div>
  );
}
