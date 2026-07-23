"use client";

import { usePlannerStore } from "@/store/plannerStore";

export function ErrorBanner() {
  const error = usePlannerStore((s) => s.error);
  const setError = usePlannerStore((s) => s.setError);

  if (!error) return null;

  return (
    <div className="mb-6 flex items-start justify-between gap-4 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
      <span>{error}</span>
      <button
        onClick={() => setError(null)}
        className="shrink-0 font-medium text-red-600 hover:text-red-800"
      >
        Dismiss
      </button>
    </div>
  );
}
