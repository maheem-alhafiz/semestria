/**
 * Derives calendar events from planner selections, and detects time
 * conflicts between them. Mirrors app.services.scheduler's
 * meetings_conflict logic (share a weekday AND overlapping clock range)
 * so the Planner tab's warnings match what the backend would actually
 * enforce -- just computed client-side for instant feedback as picks
 * change, no round trip needed.
 */

import { isDistanceGroup } from "@/lib/distanceSections";
import type { CourseSections, MeetingTime } from "@/types/api";

export interface PlannerEvent {
  courseId: number;
  crn: string;
  subject: string;
  courseNumber: string;
  meetingType: string;
  startTime: string | null;
  endTime: string | null;
  monday: boolean;
  tuesday: boolean;
  wednesday: boolean;
  thursday: boolean;
  friday: boolean;
  saturday: boolean;
  sunday: boolean;
}

const DAY_KEYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

function sharesADay(a: PlannerEvent, b: PlannerEvent): boolean {
  return DAY_KEYS.some((day) => a[day] && b[day]);
}

function timesOverlap(a: PlannerEvent, b: PlannerEvent): boolean {
  // Async/TBA meetings (no clock time) can never time-conflict --
  // matches scheduler.py's _times_overlap exactly.
  if (!a.startTime || !a.endTime || !b.startTime || !b.endTime) return false;
  // "HH:MM:SS" strings compare correctly with plain string comparison
  // since they're fixed-width, zero-padded, and 24-hour.
  return a.startTime < b.endTime && b.startTime < a.endTime;
}

export interface ScheduleConflict {
  a: PlannerEvent;
  b: PlannerEvent;
}

/** Pairwise conflicts across DIFFERENT courses only -- two meetings of
 * the SAME course (e.g. its own lecture and lab) are never flagged here,
 * matching how self-conflicts are handled as a separate, earlier check
 * in the backend rather than surfaced as a schedule "conflict" to fix. */
export function findConflicts(events: PlannerEvent[]): ScheduleConflict[] {
  const conflicts: ScheduleConflict[] = [];
  for (let i = 0; i < events.length; i++) {
    const a = events[i];
    if (!a) continue;
    for (let j = i + 1; j < events.length; j++) {
      const b = events[j];
      if (!b) continue;
      if (a.courseId === b.courseId) continue;
      if (sharesADay(a, b) && timesOverlap(a, b)) {
        conflicts.push({ a, b });
      }
    }
  }
  return conflicts;
}

interface SelectionLike {
  activeTop: boolean;
  activeBottom: boolean;
  topSectionChoices: Record<string, string>;
  bottomSectionChoices: Record<string, string>;
  // Per-slot "this course is being taken via its distance/online
  // section" flag -- when true, only distance groups contribute events;
  // when false/absent (the default), distance groups are excluded
  // entirely so an online D0X section never silently becomes part of an
  // in-person schedule. See app.lib.distanceSections for group detection.
  topDistanceMode?: boolean;
  bottomDistanceMode?: boolean;
}

/**
 * Builds the event list for one calendar slot from current selections +
 * the cached grouped-sections data. A course whose sections haven't
 * finished loading yet (not in the cache) is silently skipped -- it'll
 * appear once its fetch resolves, same pattern as CourseGroupPicker's
 * loading state.
 */
export function buildSlotEvents(
  slot: "top" | "bottom",
  termCode: string | null,
  selections: Record<number, SelectionLike>,
  courseSectionsCache: Record<string, CourseSections>,
): PlannerEvent[] {
  if (!termCode) return [];
  const events: PlannerEvent[] = [];

  for (const [courseIdStr, sel] of Object.entries(selections)) {
    const courseId = Number(courseIdStr);
    const active = slot === "top" ? sel.activeTop : sel.activeBottom;
    if (!active) continue;

    const data = courseSectionsCache[`${courseId}:${termCode}`];
    if (!data) continue;

    const distanceMode = (slot === "top" ? sel.topDistanceMode : sel.bottomDistanceMode) ?? false;
    const choices = slot === "top" ? sel.topSectionChoices : sel.bottomSectionChoices;

    for (const group of data.groups) {
      // Only include a group if its distance-ness matches the course's
      // current mode -- distance groups are invisible in normal mode,
      // regular groups are invisible once distance mode is switched on.
      if (isDistanceGroup(group) !== distanceMode) continue;

      for (const slotDef of group.slots) {
        const key = `${group.link_group_id ?? "solo"}:${slotDef.link_slot}`;
        const chosenCrn = choices[key] ?? slotDef.options[0]?.crn;
        const option = slotDef.options.find((o) => o.crn === chosenCrn);
        if (!option) continue;

        for (const mt of option.meeting_times as MeetingTime[]) {
          events.push({
            courseId,
            crn: option.crn,
            subject: data.subject,
            courseNumber: data.course_number,
            meetingType: mt.meeting_type,
            startTime: mt.start_time,
            endTime: mt.end_time,
            monday: mt.monday,
            tuesday: mt.tuesday,
            wednesday: mt.wednesday,
            thursday: mt.thursday,
            friday: mt.friday,
            saturday: mt.saturday,
            sunday: mt.sunday,
          });
        }
      }
    }
  }

  return events;
}
