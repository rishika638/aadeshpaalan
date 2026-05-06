import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { format, parseISO } from "date-fns";
import type { Directive, RiskLevel } from "../types/api";
import { RiskBadge } from "./RiskBadge";

type Row = {
  case_id: string;
  case_number: string;
  court_name: string;
  directive: Directive;
};

function sortKey(level: RiskLevel) {
  return { overdue: 0, critical: 1, due_soon: 2, watch: 3, compliant: 4 }[level];
}

export function ContemptRadar({
  rows,
  onExportCsv,
  showAllTypes,
  onToggleTypes,
}: {
  rows: Row[];
  onExportCsv: () => void;
  showAllTypes?: boolean;
  onToggleTypes?: () => void;
}) {
  const nav = useNavigate();
  const [risk, setRisk] = useState<RiskLevel | "all">("all");
  const [department, setDepartment] = useState<string>("all");

  const departments = useMemo(() => {
    const set = new Set<string>();
    for (const r of rows) {
      if (r.directive.owner_department) set.add(r.directive.owner_department);
    }
    return ["all", ...Array.from(set).sort()];
  }, [rows]);

  const filtered = useMemo(() => {
    return rows
      .filter((r) => (risk === "all" ? true : (r.directive.risk_level || "watch") === risk))
      .filter((r) => (department === "all" ? true : r.directive.owner_department === department))
      .sort((a, b) => sortKey((a.directive.risk_level || "watch") as RiskLevel) - sortKey((b.directive.risk_level || "watch") as RiskLevel));
  }, [rows, risk, department]);

  return (
    <div className="border border-slate-800 rounded-xl bg-slate-950/30 max-h-[600px] overflow-y-auto">
      <div className="sticky top-0 z-30 bg-[#0d1424] border-b border-slate-800 p-4 flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold">Contempt Risk Radar</div>
          <div className="text-xs text-slate-400">Sorted by highest risk first</div>
        </div>
        <div className="flex items-center gap-2">
          <select
            className="bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-sm"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
          >
            {departments.map((d) => (
              <option key={d} value={d}>
                {d === "all" ? "All departments" : d}
              </option>
            ))}
          </select>
          <select
            className="bg-slate-900 border border-slate-800 rounded-md px-2 py-1 text-sm"
            value={risk}
            onChange={(e) => setRisk(e.target.value as RiskLevel | "all")}
          >
            <option value="all">All risk</option>
            <option value="overdue">Overdue</option>
            <option value="critical">Critical</option>
            <option value="due_soon">Due soon</option>
            <option value="watch">Watch</option>
            <option value="compliant">Compliant</option>
          </select>
          {onToggleTypes && (
            <button
              className={`px-3 py-1.5 rounded-md text-xs border ${
                showAllTypes ? "bg-slate-700 border-slate-600 text-slate-200" : "bg-slate-900 border-slate-700 text-slate-400"
              }`}
              onClick={onToggleTypes}
            >
              {showAllTypes ? "All types" : "Govt only"}
            </button>
          )}
          <button
            onClick={onExportCsv}
            className="px-3 py-1.5 rounded-md bg-saffron text-slate-950 text-sm font-semibold hover:brightness-95"
          >
            Export CSV
          </button>
        </div>
      </div>

      <table className="min-w-full text-sm">
        <thead className="sticky top-[57px] z-20 bg-[#0d1424] text-slate-300">
          <tr>
            <th className="text-left px-4 py-2 font-semibold border-b border-slate-800">Case No.</th>
            <th className="text-left px-4 py-2 font-semibold border-b border-slate-800">Directive</th>
            <th className="text-left px-4 py-2 font-semibold border-b border-slate-800">Owner</th>
            <th className="text-left px-4 py-2 font-semibold border-b border-slate-800">Deadline</th>
            <th className="text-left px-4 py-2 font-semibold border-b border-slate-800">Days Left</th>
            <th className="text-left px-4 py-2 font-semibold border-b border-slate-800">Risk</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => {
            const riskLevel = (r.directive.risk_level || "watch") as RiskLevel;
            const deadline = r.directive.deadline ? parseISO(r.directive.deadline) : null;
            const daysLeft =
              deadline ? Math.ceil((deadline.getTime() - Date.now()) / (1000 * 60 * 60 * 24)) : null;
            return (
              <tr
                key={r.directive.id}
                className="border-t border-slate-900 hover:bg-slate-900/20 cursor-pointer"
                onClick={() => nav(`/cases/${r.case_id}`)}
              >
                <td className="px-4 py-3 font-mono text-slate-200">{r.case_number}</td>
                <td className="px-4 py-3 text-slate-200 max-w-[520px]">
                  <div className="line-clamp-2">{r.directive.directive_text}</div>
                </td>
                <td className="px-4 py-3 text-slate-300">{r.directive.owner_designation}</td>
                <td className="px-4 py-3 text-slate-300">
                  {deadline ? format(deadline, "dd MMM yyyy") : "—"}
                </td>
                <td className="px-4 py-3 font-mono text-slate-300">{daysLeft ?? "—"}</td>
                <td className="px-4 py-3">
                  <RiskBadge level={riskLevel} />
                </td>
              </tr>
            );
          })}
          {filtered.length === 0 ? (
            <tr>
              <td className="px-4 py-6 text-slate-400" colSpan={6}>
                No directives match the current filters.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}

