"use client";

import { useState } from "react";

import { getPlan } from "@/lib/api";
import { downloadIcsFile, generatePlanIcs } from "@/lib/generatePlanIcs";

interface ExportIcsButtonProps {
  planId: number;
  planName: string;
}

// Takes just planId/planName (matching what PlanSummary actually has on
// the /plans list) rather than a full PlanRead -- chosen_sections/items
// aren't in PlanSummary, so this fetches the full plan itself via
// getPlan() right before generating, the same way the existing PDF
// export presumably already does.
export function ExportIcsButton({ planId, planName }: ExportIcsButtonProps) {
  const [isGenerating, setIsGenerating] = useState(false);

  async function handleClick() {
    setIsGenerating(true);
    try {
      const plan = await getPlan(planId);
      const ics = await generatePlanIcs(plan);
      downloadIcsFile(ics, planName.replace(/[^a-z0-9]+/gi, "-").toLowerCase());
    } catch (err: any) {
      alert(err.message || "Failed to generate calendar file");
    } finally {
      setIsGenerating(false);
    }
  }

  return (
    <button
      onClick={handleClick}
      disabled={isGenerating}
      title="Add to Calendar (.ics)"
      aria-label="Export plan to calendar"
      className="mr-1 flex h-8 w-8 items-center justify-center rounded-lg p-1.5 text-muted transition-colors hover:bg-elevated hover:text-accent disabled:opacity-50"
    >
      {isGenerating ? (
        <span className="text-xs">…</span>
      ) : (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
          <line x1="16" y1="2" x2="16" y2="6" />
          <line x1="8" y1="2" x2="8" y2="6" />
          <line x1="3" y1="10" x2="21" y2="10" />
          <line x1="12" y1="14" x2="12" y2="18" />
          <line x1="10" y1="16" x2="14" y2="16" />
        </svg>
      )}
    </button>
  );
}
