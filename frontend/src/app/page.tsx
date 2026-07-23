import { CourseSearch } from "@/components/CourseSearch";
import { ErrorBanner } from "@/components/ErrorBanner";
import { ScheduleResults } from "@/components/ScheduleResults";
import { SelectedCourses } from "@/components/SelectedCourses";
import { TermSelector } from "@/components/TermSelector";

export default function HomePage() {
  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold text-brand">UM Course Planner</h1>
        <p className="text-sm text-slate-500">
          Search courses, build a schedule, and check it for conflicts.
        </p>
      </header>

      <ErrorBanner />

      <div className="space-y-8">
        <TermSelector />
        <CourseSearch />
        <SelectedCourses />
        <ScheduleResults />
      </div>
    </main>
  );
}
