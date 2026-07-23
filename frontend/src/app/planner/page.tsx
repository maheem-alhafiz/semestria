import { Suspense } from "react";

import { PlannerPage } from "@/components/PlannerPage";

// PlannerPage uses useSearchParams() (to read ?planId=), which requires
// a Suspense boundary in the App Router -- otherwise Next.js de-opts the
// whole route to fully client-side rendering with a build warning.
export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-6xl px-6 py-10 text-sm text-muted">Loading planner…</div>
      }
    >
      <PlannerPage />
    </Suspense>
  );
}
