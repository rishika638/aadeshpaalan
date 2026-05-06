import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import type { Directive } from "../types/api";
import { DirectiveCard } from "../components/DirectiveCard";
import { PDFViewer } from "../components/PDFViewer";

type ReviewResponse = {
  case: {
    id: string;
    case_number: string;
    court_name: string;
    judgment_date?: string | null;
    status: string;
  };
  directives: Directive[];
};

export function ReviewExtraction() {
  const { caseId } = useParams();
  const nav = useNavigate();
  const [draft, setDraft] = useState<Record<string, Directive>>({});
  const [showAll, setShowAll] = useState(false);
  const [showPdf, setShowPdf] = useState(true);

  const q = useQuery({
    queryKey: ["case-review", caseId],
    queryFn: () => apiFetch<ReviewResponse>(`/api/cases/${caseId}/review`),
    enabled: !!caseId
  });

  const directives = q.data?.directives ?? [];
  const merged = useMemo(() => {
    return directives.map((d) => draft[d.id] ?? d);
  }, [directives, draft]);

  const visible = useMemo(() => {
    if (showAll) return merged;
    return merged.filter((d) => {
      const t = d.directive_type;
      return !t ||
             t === "government_action" ||
             t === "administrative" ||
             t === "financial" ||
             t === "ongoing_injunction";
    });
  }, [merged, showAll]);

  const unresolved = visible.filter((d) => d.requires_human_review).length;
  const canPublish = merged.length > 0;

  function markAllReviewed() {
    const updates: Record<string, Directive> = {};
    directives.forEach((d) => {
      updates[d.id] = { ...(draft[d.id] ?? d), requires_human_review: false };
    });
    setDraft((prev) => ({ ...prev, ...updates }));
  }

  const caseInfo = q.data?.case;

  return (
    <div className="h-[calc(100vh-3rem)] flex flex-col gap-0">
      {/* ── Top bar ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-[#0B1222] shrink-0">
        <div>
          <div className="text-base font-semibold">
            Review Extraction
            {caseInfo && (
              <span className="ml-2 text-xs font-mono text-slate-400">
                {caseInfo.case_number} · {caseInfo.court_name}
              </span>
            )}
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Approve only after all flagged directives are resolved.
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            className={`px-3 py-1.5 rounded-md text-xs border transition-colors ${
              showPdf
                ? "bg-slate-700 border-slate-600 text-slate-200"
                : "bg-slate-900 border-slate-700 text-slate-400"
            }`}
            onClick={() => setShowPdf((v) => !v)}
          >
            {showPdf ? "Hide PDF" : "Show PDF"}
          </button>
          <button
            className={`px-3 py-1.5 rounded-md text-xs border transition-colors ${
              showAll
                ? "bg-slate-700 border-slate-600 text-slate-200"
                : "bg-slate-900 border-slate-700 text-slate-400"
            }`}
            onClick={() => setShowAll((v) => !v)}
          >
            {showAll ? "Govt actions only" : "Show all types"}
          </button>
          {unresolved > 0 && (
            <button
              className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-xs border border-slate-700"
              onClick={markAllReviewed}
            >
              Mark all reviewed
            </button>
          )}
          <button
            disabled={!canPublish}
            className="px-4 py-2 rounded-md bg-saffron text-slate-950 text-sm font-semibold disabled:opacity-40 hover:brightness-95"
            onClick={async () => {
              await apiFetch(`/api/cases/${caseId}/verify`, {
                method: "POST",
                body: JSON.stringify({ directives: merged })
              });
              nav(`/cases/${caseId}`, { replace: true });
            }}
          >
            Approve All & Publish
          </button>
        </div>
      </div>

      {/* ── Main content ─────────────────────────────────────────────────── */}
      <div className={`flex-1 min-h-0 grid gap-4 p-4 ${showPdf ? "lg:grid-cols-3" : "grid-cols-1"}`}>

        {/* PDF panel — col-span-1, hidden when toggled off */}
        {showPdf && (
          <div className="lg:col-span-1 border border-slate-800 rounded-xl bg-slate-950/30 overflow-hidden hidden lg:block">
            <PDFViewer caseId={caseId!} />
          </div>
        )}

        {/* Directives panel — col-span-2 when PDF visible, full width otherwise */}
        <div className={`${showPdf ? "lg:col-span-2" : "col-span-1"} flex flex-col min-h-0`}>
          {!q.data && q.isLoading && (
            <div className="text-sm text-slate-400 py-4 text-center">Loading extraction…</div>
          )}
          {q.isError && (
            <div className="text-sm text-risk-overdue py-4 text-center">
              Unable to load extraction. Check backend connectivity.
            </div>
          )}

          <div className="flex-1 overflow-auto">
            <div className="max-w-3xl mx-auto w-full space-y-3 pb-4">
              {visible.map((d) => (
                <DirectiveCard
                  key={d.id}
                  directive={d}
                  onChange={(next) => setDraft((prev) => ({ ...prev, [d.id]: next }))}
                  onJumpToParagraph={(para) => console.log("jump to", para)}
                />
              ))}
              {visible.length === 0 && q.data && (
                <div className="text-sm text-slate-400 text-center py-12">
                  No directives match the current filter.
                </div>
              )}
            </div>
          </div>

          <div className="max-w-3xl mx-auto w-full pt-2 text-xs text-slate-500 shrink-0">
            {visible.length} directive{visible.length !== 1 ? "s" : ""} shown
            {unresolved > 0 && (
              <span className="ml-2 text-risk-watch">· {unresolved} unresolved</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
