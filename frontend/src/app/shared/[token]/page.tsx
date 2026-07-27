"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getSharedPlan, createPlan, savePlanItems, getTerms, getCourseDetail } from "@/lib/api";
import type { PlanRead, Term, CourseDetailRead } from "@/types/api";

export default function SharedPlanPage() {
  const params = useParams();
  const router = useRouter();
  const token = params.token as string;

  const [plan, setPlan] = useState<PlanRead | null>(null);
  const [termLabels, setTermLabels] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [isCloning, setIsCloning] = useState(false);
  const [hydratedCourses, setHydratedCourses] = useState<Record<number, CourseDetailRead>>({});

  useEffect(() => {
    async function loadSharedPlan() {
      try {
        const [fetchedPlan, termList] = await Promise.all([
          getSharedPlan(token),
          getTerms(),
        ]);
        setPlan(fetchedPlan);
        setTermLabels(
          Object.fromEntries(termList.map((t: Term) => [t.term_code, t.description]))
        );

        // --- NEW HYDRATION STEP ---
        // Fetch the actual course names for every ID in the plan
        const courseData = await Promise.all(
          fetchedPlan.items.map((item) => getCourseDetail(item.course_id))
        );
        const courseMap: Record<number, CourseDetailRead> = {};
        for (const course of courseData) {
          courseMap[course.course_id] = course;
        }
        setHydratedCourses(courseMap);
        // --------------------------

      } catch (err) {
        setError("This share link is invalid or has expired.");
      }
    }
    loadSharedPlan();
  }, [token]);

  async function handleCloneToPlanner() {
    if (!plan) return;
    setIsCloning(true);
    try {
      // 1. Create a brand-new plan assigned to the current user's cookie
      const newPlan = await createPlan({
        name: `${plan.name} (Shared Copy)`,
        top_term_code: plan.top_term_code,
        bottom_term_code: plan.bottom_term_code,
      });

      // 2. Clone all the items over to the new plan
      await savePlanItems(newPlan.id, { items: plan.items });

      // 3. Kick the user over to their Planner tab with the new plan loaded
      router.push(`/planner?planId=${newPlan.id}`);
    } catch (err) {
      alert("Failed to save this plan to your account. Please try again.");
      setIsCloning(false);
    }
  }

  function termLabel(code: string | null): string | null {
    if (!code) return null;
    return termLabels[code] ?? code;
  }

  if (error) {
    return (
      <main className="mx-auto flex max-w-2xl flex-col items-center justify-center px-6 py-32 text-center">
        <div className="mb-4 rounded-full bg-danger/10 p-4 text-danger">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>
        </div>
        <h1 className="text-xl font-semibold text-paper">Plan Not Found</h1>
        <p className="mt-2 text-sm text-muted">{error}</p>
        <button onClick={() => router.push("/")} className="mt-6 rounded-xl border border-hairline px-4 py-2 text-sm text-paper transition-colors hover:bg-elevated">Return Home</button>
      </main>
    );
  }

  if (!plan) {
    return (
      <main className="mx-auto flex max-w-2xl items-center justify-center px-6 py-32">
        <p className="text-sm text-muted">Loading shared schedule...</p>
      </main>
    );
  }

  const termsUsed = [termLabel(plan.top_term_code), termLabel(plan.bottom_term_code)].filter(Boolean);

  return (
    <main className="mx-auto max-w-3xl px-6 py-16">
      <div className="rounded-2xl border border-hairline bg-panel p-8 shadow-sm">
        <div className="mb-6 flex flex-col items-start justify-between gap-4 border-b border-hairline pb-6 sm:flex-row sm:items-center">
          <div>
            <h2 className="mb-1 text-[10px] font-bold uppercase tracking-wider text-accent">Shared Schedule</h2>
            <h1 className="text-2xl font-bold text-paper">{plan.name}</h1>
            <p className="mt-1 text-sm text-muted">{termsUsed.join(" · ")}</p>
          </div>
          <button
            onClick={handleCloneToPlanner}
            disabled={isCloning}
            className="flex shrink-0 items-center gap-2 rounded-xl bg-accent px-5 py-2.5 text-sm font-medium text-canvas transition-colors hover:opacity-90 disabled:opacity-50"
          >
            {isCloning ? "Saving..." : "Save to my Planner"}
            {!isCloning && (
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>
            )}
          </button>
        </div>

        <div>
          <h3 className="mb-4 text-sm font-semibold text-paper">Courses in this plan</h3>
          {plan.items.length === 0 ? (
            <p className="text-sm text-muted">This plan is currently empty.</p>
          ) : (
            <div className="divide-y divide-hairline rounded-xl border border-hairline bg-elevated/30">
              {plan.items.map((item) => {
                const course = hydratedCourses[item.course_id];
                
                return (
                  <div key={item.id} className="flex items-center justify-between px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="rounded-md bg-elevated px-2 py-1 text-xs font-bold text-paper">
                        {course ? `${course.subject} ${course.course_number}` : `ID: ${item.course_id}`}
                      </span>
                      <span className="text-sm text-paper font-medium">
                        {course ? course.title : "Loading..."}
                      </span>
                      <span className="text-xs text-muted ml-2">
                        ({item.chosen_sections.length} section{item.chosen_sections.length > 1 ? 's' : ''})
                      </span>
                    </div>
                    <span className="text-xs text-muted">{termLabel(item.term_code)}</span>
                  </div>
                );
              })}
            </div>
          )}
          <p className="mt-4 text-center text-[11px] text-muted">
            Save this to your planner to view full course details, times, and calendar layouts.
          </p>
        </div>
      </div>
    </main>
  );
}