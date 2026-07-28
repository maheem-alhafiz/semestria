import { createEvents, type EventAttributes } from "ics";

import { getCourseDetail, getCourseSections } from "@/lib/api";
import type { CourseSections, PlanRead, SectionOption } from "@/types/api";

const MEETING_TYPE_LABELS: Record<string, string> = {
  CLAS: "Lecture",
  TUT: "Tutorial",
  LAB: "Lab",
  EXAM: "Exam",
  SEM: "Seminar",
  WEB: "Online",
};

interface ResolvedMeeting {
  subject: string;
  courseNumber: string;
  meetingType: string;
  crn: string;
  instructor: string | null;
  startTime: string; // "HH:MM:SS"
  endTime: string;
  startDate: string; // "YYYY-MM-DD"
  endDate: string;
  monday: boolean;
  tuesday: boolean;
  wednesday: boolean;
  thursday: boolean;
  friday: boolean;
  saturday: boolean;
  sunday: boolean;
}

function findSectionOption(sections: CourseSections, crn: string): SectionOption | undefined {
  for (const group of sections.groups) {
    for (const slot of group.slots) {
      const found = slot.options.find((o) => o.crn === crn);
      if (found) return found;
    }
  }
  return undefined;
}

// Walks every chosen section in the plan and resolves it against real
// Section/MeetingTime data via the endpoints that already exist --
// PlanItem.chosen_sections only stores CRNs, not the meeting times
// themselves. Courses and course-sections are cached per plan export so
// a plan with the same course across two terms (or multiple chosen
// sections for one course) doesn't refetch the same data repeatedly.
async function resolvePlanMeetings(plan: PlanRead): Promise<ResolvedMeeting[]> {
  const meetings: ResolvedMeeting[] = [];
  const courseCache = new Map<number, { subject: string; course_number: string }>();
  const sectionsCache = new Map<string, CourseSections>();

  for (const item of plan.items) {
    if (!courseCache.has(item.course_id)) {
      const course = await getCourseDetail(item.course_id);
      courseCache.set(item.course_id, { subject: course.subject, course_number: course.course_number });
    }
    const { subject, course_number } = courseCache.get(item.course_id)!;

    const sectionsKey = `${item.course_id}:${item.term_code}`;
    if (!sectionsCache.has(sectionsKey)) {
      sectionsCache.set(sectionsKey, await getCourseSections(item.course_id, item.term_code));
    }
    const sections = sectionsCache.get(sectionsKey)!;

    for (const chosen of item.chosen_sections) {
      const option = findSectionOption(sections, chosen.crn);
      if (!option) continue; // section no longer offered / stale choice -- skip rather than crash the whole export

      for (const mt of option.meeting_times) {
        // Async/TBA meetings have no clock time or date -- nothing
        // meaningful to put on a calendar, so they're skipped rather
        // than emitting a broken/zero-length event.
        if (!mt.start_time || !mt.end_time || !mt.start_date || !mt.end_date) continue;

        meetings.push({
          subject,
          courseNumber: course_number,
          meetingType: mt.meeting_type,
          crn: option.crn,
          instructor: option.instructor,
          startTime: mt.start_time,
          endTime: mt.end_time,
          startDate: mt.start_date,
          endDate: mt.end_date,
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

  return meetings;
}

const WEEKDAY_BYDAY: [keyof ResolvedMeeting, string][] = [
  ["monday", "MO"],
  ["tuesday", "TU"],
  ["wednesday", "WE"],
  ["thursday", "TH"],
  ["friday", "FR"],
  ["saturday", "SA"],
  ["sunday", "SU"],
];

function toIcsUntil(dateStr: string): string {
  return dateStr.replace(/-/g, "");
}

function durationMinutes(start: string, end: string): number {
  const [sh = 0, sm = 0] = start.split(":").map(Number);
  const [eh = 0, em = 0] = end.split(":").map(Number);
  let minutes = eh * 60 + em - (sh * 60 + sm);
  if (minutes <= 0) minutes += 24 * 60; // guard against an overnight/malformed pair rather than emitting a negative duration
  return minutes;
}

function getTrueStartDate(dateStr: string, m: ResolvedMeeting): [number, number, number] {
  const [y = 0, mo = 0, d = 0] = dateStr.split("-").map(Number);
  
  // Set to noon to avoid any weird midnight Daylight Saving Time shifts
  const current = new Date(y, mo - 1, d, 12, 0, 0);

  const daysMap: Record<number, keyof ResolvedMeeting> = {
    0: "sunday",
    1: "monday",
    2: "tuesday",
    3: "wednesday",
    4: "thursday",
    5: "friday",
    6: "saturday",
  };

  // Fast-forward day by day until we hit a weekday this class actually meets on.
  let attempts = 0;
  while (attempts < 7) {
    const dayKey = daysMap[current.getDay()] as keyof ResolvedMeeting;
    if (m[dayKey]) break; // Found a valid meeting day, stop looping
    
    current.setDate(current.getDate() + 1);
    attempts++;
  }

  return [current.getFullYear(), current.getMonth() + 1, current.getDate()];
}

function meetingToEvent(m: ResolvedMeeting): EventAttributes {
  // Calculate the true first day instead of blindly trusting Aurora's term start date
  const [sy, smo, sd] = getTrueStartDate(m.startDate, m);
  const [hh = 0, mi = 0] = m.startTime.split(":").map(Number);

  // Aurora's per-meeting start_date/end_date (see backend's MeetingTime
  // model) is the source of truth for whether this is a single
  // occurrence or a weekly-recurring one -- equal dates means a genuine
  // one-off (e.g. a standalone lab date), not a data gap.
  const isOneOff = m.startDate === m.endDate;
  const byday = WEEKDAY_BYDAY.filter(([key]) => m[key]).map(([, code]) => code).join(",");

  const event: EventAttributes = {
    title: `${m.subject} ${m.courseNumber} — ${MEETING_TYPE_LABELS[m.meetingType] ?? m.meetingType}`,
    description: `CRN ${m.crn}${m.instructor ? ` · ${m.instructor}` : ""}`,
    start: [sy, smo, sd, hh, mi],
    // "local"/"local" produces a floating time (no UTC "Z" suffix) --
    // Aurora's times are wall-clock local, so treating them as UTC would
    // silently shift every event by Winnipeg's UTC offset in whatever
    // timezone the importing calendar app is set to.
    startInputType: "local",
    startOutputType: "local",
    duration: { minutes: durationMinutes(m.startTime, m.endTime) },
    calName: "semestria.",
  };

  if (!isOneOff && byday) {
    event.recurrenceRule = `FREQ=WEEKLY;BYDAY=${byday};UNTIL=${toIcsUntil(m.endDate)}`;
  }

  return event;
}

export async function generatePlanIcs(plan: PlanRead): Promise<string> {
  const meetings = await resolvePlanMeetings(plan);
  if (meetings.length === 0) {
    throw new Error("This plan has no scheduled meeting times to export.");
  }

  return new Promise((resolve, reject) => {
    createEvents(meetings.map(meetingToEvent), (error, value) => {
      if (error) {
        reject(error);
        return;
      }
      resolve(value);
    });
  });
}

export function downloadIcsFile(icsContent: string, filename: string): void {
  const blob = new Blob([icsContent], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".ics") ? filename : `${filename}.ics`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}