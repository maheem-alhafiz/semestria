"use client";

import { useState } from "react";

interface SavePlanModalProps {
  isOpen: boolean;
  initialName?: string;
  isSaving: boolean;
  onCancel: () => void;
  onConfirm: (name: string) => void;
}

// Only shown when a name is actually needed: creating a brand-new plan,
// or forking the current one via "Save as New...". A plain "Save
// Changes" on an already-loaded plan never opens this -- it just saves
// silently under the existing name.
export function SavePlanModal({
  isOpen,
  initialName,
  isSaving,
  onCancel,
  onConfirm,
}: SavePlanModalProps) {
  const [name, setName] = useState(initialName ?? "");

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
      <div className="w-full max-w-sm rounded-2xl border border-hairline bg-panel p-5 shadow-2xl">
        <h2 className="text-sm font-semibold text-paper">Name this plan</h2>
        <input
          autoFocus
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Fall 2026 / Winter 2027"
          className="mt-3 w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent"
          onKeyDown={(e) => {
            if (e.key === "Enter" && name.trim()) onConfirm(name.trim());
          }}
        />
        <div className="mt-4 flex justify-end gap-2">
          <button
            onClick={onCancel}
            className="rounded-xl px-3 py-1.5 text-sm text-muted transition-colors hover:text-paper"
          >
            Cancel
          </button>
          <button
            onClick={() => name.trim() && onConfirm(name.trim())}
            disabled={isSaving || !name.trim()}
            className="rounded-xl bg-accent px-4 py-1.5 text-sm font-medium text-canvas disabled:opacity-40"
          >
            {isSaving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
