"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

// Added finalizePlan to the imports here
import { ApiError, deletePlan, getTerms, listPlans, finalizePlan } from "@/lib/api";
import { usePlannerBuilderStore } from "@/store/plannerBuilderStore";
import type { PlanSummary, Term } from "@/types/api";

function formatUpdatedAt(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function PlansPage() {
  const router = useRouter();
  const resetPlanner = usePlannerBuilderStore((s) => s.resetPlanner);
  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [termLabels, setTermLabels] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal states
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [planToDelete, setPlanToDelete] = useState<PlanSummary | null>(null);
  
  // Finalize loading state
  const [finalizingId, setFinalizingId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const [planList, termList] = await Promise.all([listPlans(), getTerms()]);
        if (cancelled) return;
        setPlans(planList);
        setTermLabels(
          Object.fromEntries(termList.map((t: Term) => [t.term_code, t.description])),
        );
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof ApiError ? err.message : "Couldn't load your plans.");
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  async function confirmDelete() {
    if (!planToDelete) return;
    setDeletingId(planToDelete.id);
    try {
      await deletePlan(planToDelete.id);
      setPlans((prev) => prev.filter((p) => p.id !== planToDelete.id));
      setPlanToDelete(null); 
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't delete that plan.");
    } finally {
      setDeletingId(null);
    }
  }

  // New function to handle the Finalize API call
  async function handleFinalize(plan: PlanSummary) {
    setFinalizingId(plan.id);
    setError(null);
    try {
      await finalizePlan(plan.id);
      // Update the local state so the "Finalized" badge appears instantly
      setPlans((prev) =>
        prev.map((p) => (p.id === plan.id ? { ...p, is_final: true } : p))
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't finalize that plan.");
    } finally {
      setFinalizingId(null);
    }
  }

  function handleNewPlan() {
    resetPlanner();
    router.push("/planner");
  }

  function termLabel(code: string | null): string | null {
    if (!code) return null;
    return termLabels[code] ?? code;
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-paper">Plans</h1>
          <p className="text-sm text-muted">Every schedule you&apos;ve saved, in one place.</p>
        </div>
        <button
          onClick={handleNewPlan}
          className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-canvas transition-colors hover:opacity-90"
        >
          New plan
        </button>
      </header>

      {error && (
        <div className="mb-6 rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
          {error}
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-muted">Loading your plans…</p>
      ) : plans.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-hairline px-6 py-16 text-center">
          <p className="text-sm font-medium text-paper">No plans yet</p>
          <p className="mt-1 text-sm text-muted">
            Build a schedule in the Planner tab, then save it here.
          </p>
          <button
            onClick={handleNewPlan}
            className="mt-4 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-canvas transition-colors hover:opacity-90"
          >
            Go to Planner
          </button>
        </div>
      ) : (
        <ul className="divide-y divide-hairline rounded-2xl border border-hairline">
          {plans.map((plan) => (
            <li key={plan.id} className="flex items-center justify-between px-5 py-4">
              <div>
                <div className="flex items-center gap-2">
                  <p className="text-sm font-medium text-paper">{plan.name}</p>
                  {plan.is_final && (
                    <span className="rounded-full bg-success/15 px-2 py-0.5 text-[11px] font-medium text-success">
                      Finalized
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted">
                  {[termLabel(plan.top_term_code), termLabel(plan.bottom_term_code)]
                    .filter(Boolean)
                    .join(" · ")}
                  {" — updated "}
                  {formatUpdatedAt(plan.updated_at)}
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  href={`/planner?planId=${plan.id}`}
                  className="rounded-full border border-hairline px-3 py-1.5 text-sm text-paper transition-colors hover:bg-elevated"
                >
                  Load
                </Link>
                
                {/* New Finalize Button */}
                <button
                  onClick={() => handleFinalize(plan)}
                  disabled={finalizingId === plan.id}
                  className="rounded-full border border-accent px-3 py-1.5 text-sm text-accent transition-colors hover:bg-accent hover:text-canvas disabled:opacity-50"
                >
                  {finalizingId === plan.id ? "Syncing..." : plan.is_final ? "Update Tracker" : "Finalize"}
                </button>

                <button
                  onClick={() => setPlanToDelete(plan)}
                  className="rounded-full px-3 py-1.5 text-sm text-muted transition-colors hover:text-danger"
                >
                  Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Custom Delete Modal Overlay */}
      {planToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-canvas/80 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl border border-hairline bg-elevated p-6 shadow-xl">
            <h3 className="text-lg font-medium text-paper">Delete Plan</h3>
            <p className="mt-2 text-sm text-muted">
              Are you sure you want to delete <span className="font-medium text-paper">&quot;{planToDelete.name}&quot;</span>? This action cannot be undone.
            </p>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => setPlanToDelete(null)}
                disabled={deletingId !== null}
                className="rounded-xl px-4 py-2 text-sm font-medium text-paper transition-colors hover:bg-panel disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                onClick={confirmDelete}
                disabled={deletingId !== null}
                className="rounded-xl bg-danger px-4 py-2 text-sm font-medium text-canvas transition-colors hover:opacity-90 disabled:opacity-50"
              >
                {deletingId === planToDelete.id ? "Deleting…" : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}