"use client";

import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";

import { CourseSearchDropdown } from "@/components/CourseSearchDropdown";
import { SavePlanModal } from "@/components/SavePlanModal";
import { SlotCoursesPanel } from "@/components/SlotCoursesPanel";
import { TermCalendar } from "@/components/TermCalendar";
import {
  ApiError,
  createPlan,
  getCourseSections,
  getPlan,
  getTerms,
  savePlanItems,
  searchCourses,
  updatePlan,
} from "@/lib/api";
import { usePlannerBuilderStore } from "@/store/plannerBuilderStore";
import type { Course, PlanItemCreate, Term } from "@/types/api";

function termLabel(terms: Term[], code: string | null): string {
  if (!code) return "";
  return terms.find((t) => t.term_code === code)?.description ?? code;
}

export function PlannerPage() {
  const searchParams = useSearchParams();

  const [terms, setTerms] = useState<Term[]>([]);
  const [termsError, setTermsError] = useState<string | null>(null);
  const [isLoadingPlan, setIsLoadingPlan] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [offeredByTerm, setOfferedByTerm] = useState<
    Map<number, { top: boolean; bottom: boolean }>
  >(new Map());
  const [modalOpen, setModalOpen] = useState(false);
  const [modalMode, setModalMode] = useState<"new" | "fork">("new");

  const topTermCode = usePlannerBuilderStore((s) => s.topTermCode);
  const bottomTermCode = usePlannerBuilderStore((s) => s.bottomTermCode);
  const searchQuery = usePlannerBuilderStore((s) => s.searchQuery);
  const setSearchQuery = usePlannerBuilderStore((s) => s.setSearchQuery);
  const isSearching = usePlannerBuilderStore((s) => s.isSearching);
  const setIsSearching = usePlannerBuilderStore((s) => s.setIsSearching);
  const searchResults = usePlannerBuilderStore((s) => s.searchResults);
  const setSearchResults = usePlannerBuilderStore((s) => s.setSearchResults);
  const knownCourses = usePlannerBuilderStore((s) => s.knownCourses);
  const selections = usePlannerBuilderStore((s) => s.selections);
  const setCourseSections = usePlannerBuilderStore((s) => s.setCourseSections);
  const loadPlan = usePlannerBuilderStore((s) => s.loadPlan);
  const planName = usePlannerBuilderStore((s) => s.planName);
  const setPlanName = usePlannerBuilderStore((s) => s.setPlanName);
  const currentPlanId = usePlannerBuilderStore((s) => s.currentPlanId);
  const isSaving = usePlannerBuilderStore((s) => s.isSaving);
  const setIsSaving = usePlannerBuilderStore((s) => s.setIsSaving);
  const error = usePlannerBuilderStore((s) => s.error);
  const setError = usePlannerBuilderStore((s) => s.setError);

  useEffect(() => {
    getTerms()
      .then(setTerms)
      .catch((err) => setTermsError(err instanceof ApiError ? err.message : "Couldn't load terms."));
  }, []);

  // Load-from-Plans-page: reads ?planId= off the URL, fetches the Plan,
  // then fetches each referenced course's live CourseSections (once per
  // unique course_id+term_code pair) -- that call gives both the Course
  // fields needed for coursesById AND populates courseSectionsCache, so
  // the calendars render immediately without a second round trip.
  useEffect(() => {
    const planIdParam = searchParams.get("planId");
    if (!planIdParam) return;
    const planId = Number(planIdParam);
    if (!Number.isFinite(planId)) return;

    let cancelled = false;
    setIsLoadingPlan(true);
    setError(null);

    async function load() {
      try {
        const plan = await getPlan(planId);
        if (cancelled) return;

        const uniquePairs = new Map<string, { courseId: number; termCode: string }>();
        for (const item of plan.items) {
          uniquePairs.set(`${item.course_id}:${item.term_code}`, {
            courseId: item.course_id,
            termCode: item.term_code,
          });
        }

        const coursesById: Record<number, Course> = {};
        await Promise.all(
          Array.from(uniquePairs.values()).map(async ({ courseId, termCode }) => {
            const data = await getCourseSections(courseId, termCode);
            if (cancelled) return;
            setCourseSections(courseId, termCode, data);
            coursesById[courseId] = {
              course_id: data.course_id,
              subject: data.subject,
              course_number: data.course_number,
              title: data.title,
              credit_hours: data.credit_hours,
            };
          }),
        );

        if (cancelled) return;
        loadPlan(plan, coursesById);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof ApiError ? err.message : "Couldn't load that plan.");
        }
      } finally {
        if (!cancelled) setIsLoadingPlan(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  // Combined search: one query per active term slot, merged and deduped
  // -- one search box, no re-searching per term.
  useEffect(() => {
    if (!topTermCode && !bottomTermCode) {
      setSearchResults([]);
      setOfferedByTerm(new Map());
      return;
    }

    let cancelled = false;
    setIsSearching(true);

    const topPromise = topTermCode ? searchCourses(topTermCode, searchQuery) : Promise.resolve([]);
    const bottomPromise = bottomTermCode
      ? searchCourses(bottomTermCode, searchQuery)
      : Promise.resolve([]);

    Promise.all([topPromise, bottomPromise])
      .then(([topResults, bottomResults]) => {
        if (cancelled) return;
        const merged = new Map<number, Course>();
        const offered = new Map<number, { top: boolean; bottom: boolean }>();

        for (const course of topResults) {
          merged.set(course.course_id, course);
          offered.set(course.course_id, {
            top: true,
            bottom: offered.get(course.course_id)?.bottom ?? false,
          });
        }
        for (const course of bottomResults) {
          merged.set(course.course_id, course);
          offered.set(course.course_id, {
            top: offered.get(course.course_id)?.top ?? false,
            bottom: true,
          });
        }

        setSearchResults(Array.from(merged.values()));
        setOfferedByTerm(offered);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Search failed.");
      })
      .finally(() => {
        if (!cancelled) setIsSearching(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topTermCode, bottomTermCode, searchQuery]);

  const multiTermCourses = useMemo(
    () =>
      Object.entries(selections)
        .filter(([, sel]) => sel.activeTop && sel.activeBottom)
        .map(([id]) => knownCourses[Number(id)])
        .filter((c): c is Course => Boolean(c)),
    [selections, knownCourses],
  );

  function buildItems(): PlanItemCreate[] {
    const items: PlanItemCreate[] = [];
    for (const [idStr, sel] of Object.entries(selections)) {
      const courseId = Number(idStr);
      if (sel.activeTop && topTermCode) {
        items.push({
          term_code: topTermCode,
          course_id: courseId,
          chosen_sections: Object.entries(sel.topSectionChoices).map(([slotKey, crn]) => ({
            term_code: topTermCode,
            crn,
            link_slot: slotKey,
          })),
        });
      }
      if (sel.activeBottom && bottomTermCode) {
        items.push({
          term_code: bottomTermCode,
          course_id: courseId,
          chosen_sections: Object.entries(sel.bottomSectionChoices).map(([slotKey, crn]) => ({
            term_code: bottomTermCode,
            crn,
            link_slot: slotKey,
          })),
        });
      }
    }
    return items;
  }

  async function persistPlan(name: string, forkAsNew: boolean) {
    setIsSaving(true);
    setError(null);
    try {
      const items = buildItems();
      let planId = forkAsNew ? null : currentPlanId;

      if (planId === null) {
        const created = await createPlan({
          name,
          top_term_code: topTermCode,
          bottom_term_code: bottomTermCode,
        });
        planId = created.id;
        usePlannerBuilderStore.setState({ currentPlanId: planId });
        setPlanName(name);
      } else {
        await updatePlan(planId, {
          name,
          top_term_code: topTermCode,
          bottom_term_code: bottomTermCode,
        });
        setPlanName(name);
      }

      await savePlanItems(planId, { items });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't save plan.");
    } finally {
      setIsSaving(false);
    }
  }

  function handlePrimarySaveClick() {
    if (currentPlanId === null) {
      setModalMode("new");
      setModalOpen(true);
    } else {
      persistPlan(planName, false);
    }
  }

  function handleSaveAsNewClick() {
    setModalMode("fork");
    setModalOpen(true);
  }

  function handleModalConfirm(name: string) {
    setModalOpen(false);
    persistPlan(name, modalMode === "fork");
  }

  return (
    <div className="mx-auto w-full max-w-[1600px] space-y-5 px-6 py-8">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-[260px] flex-1">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setDropdownOpen(true)}
            placeholder="Search courses (e.g. MECH 2202 or Thermodynamics)"
            disabled={!topTermCode && !bottomTermCode}
            className="w-full rounded-xl border border-hairline bg-elevated px-3 py-2 text-sm text-paper placeholder:text-muted disabled:opacity-50"
          />
          <CourseSearchDropdown
            results={searchResults}
            offeredByTerm={offeredByTerm}
            topTermLabel={termLabel(terms, topTermCode)}
            bottomTermLabel={termLabel(terms, bottomTermCode)}
            visible={dropdownOpen && searchQuery.length > 0}
            onClose={() => setDropdownOpen(false)}
          />
        </div>

        {currentPlanId === null ? (
          <button
            onClick={handlePrimarySaveClick}
            disabled={isSaving || (!topTermCode && !bottomTermCode)}
            className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-canvas disabled:opacity-40"
          >
            {isSaving ? "Saving…" : "Save Plan"}
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={handlePrimarySaveClick}
              disabled={isSaving}
              className="rounded-xl bg-accent px-4 py-2 text-sm font-medium text-canvas disabled:opacity-40"
            >
              {isSaving ? "Saving…" : "Save Changes"}
            </button>
            <button
              onClick={handleSaveAsNewClick}
              disabled={isSaving}
              className="rounded-xl border border-hairline px-4 py-2 text-sm text-paper transition-colors hover:bg-elevated disabled:opacity-40"
            >
              Save as New…
            </button>
          </div>
        )}
      </div>

      {isLoadingPlan && <p className="text-xs text-muted">Loading plan…</p>}
      {!topTermCode && !bottomTermCode && (
        <p className="text-xs text-muted">Select a term in at least one calendar to search.</p>
      )}
      {termsError && <p className="text-xs text-danger">{termsError}</p>}
      {error && <p className="text-xs text-danger">{error}</p>}
      {isSearching && <p className="text-xs text-muted">Searching…</p>}

      {multiTermCourses.length > 0 && (
        <div className="rounded-xl border border-warning/40 bg-warning/10 px-3.5 py-2.5 text-xs text-warning">
          {multiTermCourses.map((c) => (
            <div key={c.course_id}>
              {c.subject} {c.course_number} has been selected in multiple terms.
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[25%_1fr]">
        <SlotCoursesPanel slot="top" termCode={topTermCode} />
        <TermCalendar slot="top" terms={terms} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[25%_1fr]">
        <SlotCoursesPanel slot="bottom" termCode={bottomTermCode} />
        <TermCalendar slot="bottom" terms={terms} />
      </div>

      <SavePlanModal
        isOpen={modalOpen}
        initialName={modalMode === "fork" ? `${planName} (copy)` : ""}
        isSaving={isSaving}
        onCancel={() => setModalOpen(false)}
        onConfirm={handleModalConfirm}
      />
    </div>
  );
}
