import { useMemo } from "react";
import type { Directive, DirectiveType } from "../types/api";

function confidenceColor(c: number | null | undefined) {
  if (c === null || c === undefined) return "bg-slate-800 text-slate-200";
  if (c >= 0.85) return "bg-risk-compliant/15 text-risk-compliant border-risk-compliant/30";
  if (c >= 0.75) return "bg-risk-watch/15 text-risk-watch border-risk-watch/30";
  return "bg-risk-dueSoon/15 text-risk-dueSoon border-risk-dueSoon/30";
}

const TYPE_LABELS: Record<DirectiveType, { label: string; cls: string }> = {
  government_action:  { label: "Govt Action",   cls: "bg-blue-900/30 text-blue-300 border-blue-700/40" },
  judicial_direction: { label: "Judicial",       cls: "bg-purple-900/30 text-purple-300 border-purple-700/40" },
  private_party:      { label: "Private Party",  cls: "bg-slate-800 text-slate-400 border-slate-700" },
  ongoing_injunction: { label: "Injunction",     cls: "bg-risk-watch/15 text-risk-watch border-risk-watch/30" },
};

export function DirectiveCard({
  directive,
  onChange,
  onJumpToParagraph
}: {
  directive: Directive;
  onChange: (next: Directive) => void;
  onJumpToParagraph: (para: string) => void;
}) {
  const needs = directive.requires_human_review;
  const conf = directive.confidence_score ?? null;
  const confLabel = useMemo(() => (conf === null ? "—" : conf.toFixed(2)), [conf]);
  const isUnassigned = !directive.owner_designation || directive.owner_designation === "Needs Manual Assignment";
  const dtype = directive.directive_type as DirectiveType | null | undefined;

  return (
    <div className={`border rounded-xl p-4 ${needs ? "border-risk-watch/40 bg-risk-watch/10" : "border-slate-800 bg-slate-950/30"}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="text-sm font-semibold text-slate-200">Directive</div>
          {dtype && TYPE_LABELS[dtype] && (
            <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-medium ${TYPE_LABELS[dtype].cls}`}>
              {TYPE_LABELS[dtype].label}
            </span>
          )}
        </div>
        <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-semibold ${confidenceColor(conf)}`}>
          Confidence: {confLabel} {needs ? "• Needs Review" : ""}
        </span>
      </div>

      <textarea
        className="mt-2 w-full min-h-[88px] bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm text-slate-100"
        value={directive.directive_text}
        onChange={(e) => onChange({ ...directive, directive_text: e.target.value })}
      />

      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <div className="text-xs text-slate-400 mb-1">Source paragraph</div>
          <button
            className="text-sm font-mono text-saffron hover:underline text-left"
            onClick={() => onJumpToParagraph(directive.source_paragraph || "")}
            disabled={!directive.source_paragraph}
          >
            {directive.source_paragraph || "—"}
          </button>
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">Owner designation</div>
          {isUnassigned ? (
            <div className="relative group">
              <input
                className="w-full bg-amber-950/30 border border-amber-600/50 rounded-md px-3 py-2 text-sm text-amber-400 placeholder-amber-600"
                value={directive.owner_designation || ""}
                placeholder="Needs Manual Assignment"
                onChange={(e) => onChange({ ...directive, owner_designation: e.target.value })}
              />
              <div className="absolute bottom-full left-0 mb-1 hidden group-hover:block z-50 w-64 bg-slate-800 border border-slate-700 rounded-md px-3 py-2 text-xs text-slate-300 shadow-lg">
                Respondent designation could not be automatically resolved. Please assign manually.
              </div>
            </div>
          ) : (
            <input
              className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
              value={directive.owner_designation}
              onChange={(e) => onChange({ ...directive, owner_designation: e.target.value })}
            />
          )}
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">Deadline</div>
          <input
            type="date"
            className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
            value={directive.deadline ?? ""}
            onChange={(e) => onChange({ ...directive, deadline: e.target.value })}
          />
        </div>
        <div>
          <div className="text-xs text-slate-400 mb-1">Deadline basis</div>
          <div className="text-xs text-slate-300 border border-slate-800 rounded-md px-3 py-2 bg-slate-900">
            {directive.deadline_basis || "—"}
          </div>
        </div>
      </div>
    </div>
  );
}
