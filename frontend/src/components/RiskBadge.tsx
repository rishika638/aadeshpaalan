import type { RiskLevel } from "../types/api";

const MAP: Record<RiskLevel, { label: string; className: string }> = {
  overdue: { label: "OVERDUE", className: "bg-risk-overdue/15 text-risk-overdue border-risk-overdue/30" },
  critical: { label: "CRITICAL", className: "bg-risk-critical/15 text-risk-critical border-risk-critical/30" },
  due_soon: { label: "DUE SOON", className: "bg-risk-dueSoon/15 text-risk-dueSoon border-risk-dueSoon/30" },
  watch: { label: "WATCH", className: "bg-risk-watch/15 text-risk-watch border-risk-watch/30" },
  compliant: { label: "COMPLIANT", className: "bg-risk-compliant/15 text-risk-compliant border-risk-compliant/30" },
  archived_unverified: { label: "UNVERIFIED (OLD)", className: "bg-slate-800/50 text-slate-400 border-slate-700" },
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  const m = MAP[level] ?? MAP.watch;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-xs font-semibold ${m.className}`}>
      {m.label}
    </span>
  );
}
