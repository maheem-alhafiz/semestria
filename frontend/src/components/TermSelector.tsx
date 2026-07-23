"use client";

import { useEffect, useState } from "react";

import { ApiError, getTerms } from "@/lib/api";
import { usePlannerStore } from "@/store/plannerStore";
import type { Term } from "@/types/api";

export function TermSelector() {
  const [terms, setTerms] = useState<Term[]>([]);
  const [loading, setLoading] = useState(true);

  const termCode = usePlannerStore((s) => s.termCode);
  const setTermCode = usePlannerStore((s) => s.setTermCode);
  const setError = usePlannerStore((s) => s.setError);

  useEffect(() => {
    getTerms()
      .then(setTerms)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load terms."))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex items-center gap-3">
      <label htmlFor="term-select" className="text-sm font-medium text-slate-600">
        Term
      </label>
      <select
        id="term-select"
        className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm disabled:opacity-50"
        value={termCode ?? ""}
        onChange={(e) => setTermCode(e.target.value)}
        disabled={loading || terms.length === 0}
      >
        <option value="" disabled>
          {loading ? "Loading terms…" : terms.length === 0 ? "No terms available" : "Select a term"}
        </option>
        {terms.map((t) => (
          <option key={t.term_code} value={t.term_code}>
            {t.description}
          </option>
        ))}
      </select>
    </div>
  );
}
