"use client";

import { usePlannerStore } from "@/store/plannerStore";
import type { MeetingTime, Section } from "@/types/api";

const DAY_ABBREVIATIONS: Array<[keyof MeetingTime, string]> = [
  ["monday", "Mon"],
  ["tuesday", "Tue"],
  ["wednesday", "Wed"],
  ["thursday", "Thu"],
  ["friday", "Fri"],
  ["saturday", "Sat"],
  ["sunday", "Sun"],
];

function formatClockTime(value: string | null): string {
  if (!value) return "TBA";
  const [hourStr, minuteStr] = value.split(":");
  const hour = Number(hourStr);
  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  return `${displayHour}:${minuteStr} ${period}`;
}

function formatMeeting(mt: MeetingTime): string {
  const days = DAY_ABBREVIATIONS.filter(([key]) => Boolean(mt[key]))
    .map(([, label]) => label)
    .join("");
  const time =
    mt.start_time && mt.end_time
      ? `${formatClockTime(mt.start_time)}–${formatClockTime(mt.end_time)}`
      : "Async / TBA";
  return `${mt.meeting_type} ${days ? `${days} ` : ""}${time}`;
}

function SectionCard({ section }: { section: Section }) {
  return (
    <div className="rounded-md border border-slate-200 p-2.5">
      <p className="text-sm font-medium">
        {section.course.subject} {section.course.course_number}{" "}
        <span className="font-normal text-slate-500">— {section.section_number}</span>
      </p>
      <p className="text-xs text-slate-400">
        CRN {section.crn}
        {section.instructor ? ` · ${section.instructor}` : ""}
      </p>
      <ul className="mt-1.5 space-y-0.5 text-xs text-slate-600">
        {section.meeting_times.length === 0 ? (
          <li>No scheduled meetings</li>
        ) : (
          section.meeting_times.map((mt, i) => <li key={i}>{formatMeeting(mt)}</li>)
        )}
      </ul>
    </div>
  );
}

export function ScheduleResults() {
  const schedules = usePlannerStore((s) => s.schedules);

  if (schedules.length === 0) return null;

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-semibold text-slate-700">
        {schedules.length} valid schedule{schedules.length === 1 ? "" : "s"} found
      </h2>

      <div className="space-y-4">
        {schedules.map((schedule, i) => (
          <div key={i} className="rounded-lg border border-slate-200 p-3">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Schedule {i + 1}
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {schedule.sections.map((section) => (
                <SectionCard key={section.crn} section={section} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
