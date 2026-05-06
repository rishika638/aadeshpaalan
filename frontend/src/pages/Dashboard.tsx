import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { apiFetch } from "../api/client";
import type { DashboardSummary, Directive } from "../types/api";
import { TimelineAlert } from "../components/TimelineAlert";
import { ContemptRadar } from "../components/ContemptRadar";

type RadarRow = {
  case_id: string;
  case_number: string;
  court_name: string;
  directive: Directive;
};

function StatCard({
  label,
  count,
  colorClass
}: {
  label: string;
  count: number;
  colorClass: string;
}) {
  return (
    <div className="border border-slate-800 rounded-xl bg-white text-slate-900 p-4">
      <div className="text-xs font-semibold text-slate-600">{label}</div>
      <div className={`mt-2 text-3xl font-bold ${colorClass}`}>{count}</div>
    </div>
  );
}

export function Dashboard() {
  const summary = useQuery({
    queryKey: ["dashboard-summary"],
    queryFn: () => apiFetch<DashboardSummary>("/api/dashboard/summary"),
    retry: false,
  });

  const directives = useQuery({
    queryKey: ["dashboard-directives"],
    queryFn: () => apiFetch<{ items: RadarRow[] }>("/api/dashboard/directives?limit=50&page=1"),
    retry: false,
  });

  const s = summary.data;
  const rows = directives.data?.items ?? [];
  const [showAllTypes, setShowAllTypes] = useState(false);

  const visibleRows = showAllTypes
    ? rows
    : rows.filter((r) => !r.directive.directive_type || r.directive.directive_type === "government_action" || r.directive.directive_type === "ongoing_injunction");

  const t0 = visibleRows.filter((r) => r.directive.risk_level === "overdue").length;
  const t3 = visibleRows.filter((r) => r.directive.risk_level === "critical").length;

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-xl font-semibold">Dashboard</div>
          <div className="text-xs text-slate-400">
            Read-only compliance tracking overlay for CCMS-linked cases
          </div>
        </div>
        <div className="text-xs text-slate-400">Data is auditable and append-only</div>
      </div>

      <TimelineAlert t3={t3} t0={t0} />

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
        <StatCard label="Overdue" count={s?.overdue_count ?? 0} colorClass="text-risk-overdue" />
        <StatCard label="Critical" count={s?.critical_count ?? 0} colorClass="text-risk-critical" />
        <StatCard label="Due Soon" count={s?.due_soon_count ?? 0} colorClass="text-risk-dueSoon" />
        <StatCard label="Watch" count={s?.watch_count ?? 0} colorClass="text-risk-watch" />
        <StatCard label="Compliant" count={s?.compliant_count ?? 0} colorClass="text-risk-compliant" />
      </div>

      <ContemptRadar
        rows={visibleRows}
        showAllTypes={showAllTypes}
        onToggleTypes={() => setShowAllTypes((v) => !v)}
        onExportCsv={() => {
          const header = ["case_number", "directive_text", "owner", "deadline", "risk"].join(",");
          const lines = rows.map((r) =>
            [
              r.case_number,
              JSON.stringify(r.directive.directive_text),
              JSON.stringify(r.directive.owner_designation),
              r.directive.deadline ?? "",
              r.directive.risk_level ?? ""
            ].join(",")
          );
          const csv = [header, ...lines].join("\n");
          const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
          const url = URL.createObjectURL(blob);
          const a = document.createElement("a");
          a.href = url;
          a.download = "aadeshpaalan-directives.csv";
          a.click();
          URL.revokeObjectURL(url);
        }}
      />

      {(summary.isLoading || directives.isLoading) && (
        <div className="text-sm text-slate-400">Loading dashboard data…</div>
      )}
      {(summary.isError || directives.isError) && (
        <div className="text-sm text-risk-overdue">
          Unable to load dashboard data. Check backend connectivity and authentication.
        </div>
      )}
    </div>
  );
}

