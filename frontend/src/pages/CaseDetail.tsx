import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { useSession } from "../api/sessionStore";
import type { CaseDetailResponse, Directive } from "../types/api";
import { RiskBadge } from "../components/RiskBadge";
import { AuditTrail } from "../components/AuditTrail";

function DirectiveRow({ d, canAct }: { d: Directive; canAct: boolean }) {
  return (
    <div className="border border-slate-800 rounded-xl bg-slate-950/30 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="text-sm font-semibold text-slate-200">{d.directive_text}</div>
        {d.risk_level ? <RiskBadge level={d.risk_level} /> : null}
      </div>
      <div className="mt-2 text-xs text-slate-400">
        Owner: <span className="text-slate-200">{d.owner_designation}</span>{" "}
        <span className="mx-2 text-slate-700">|</span>
        Deadline: <span className="font-mono text-slate-200">{d.deadline ?? "—"}</span>{" "}
        <span className="mx-2 text-slate-700">|</span>
        Status: <span className="font-mono text-slate-200">{d.status}</span>
      </div>

      {canAct ? (
        <div className="mt-3 flex gap-2">
          <button className="px-3 py-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-sm">
            Mark In Progress
          </button>
          <button className="px-3 py-1.5 rounded-md bg-saffron text-slate-950 font-semibold text-sm hover:brightness-95">
            Mark Complete
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function CaseDetail() {
  const { caseId } = useParams();
  const session = useSession();
  const canAct = session?.role === "officer" || session?.role === "admin";

  const q = useQuery({
    queryKey: ["case-detail", caseId],
    queryFn: () => apiFetch<CaseDetailResponse>(`/api/cases/${caseId}`),
    enabled: !!caseId
  });

  const data = q.data;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xl font-semibold">Case Detail</div>
          <div className="text-xs text-slate-400 mt-1">
            Case: <span className="font-mono">{data?.case_number ?? caseId}</span>
          </div>
        </div>
        {data ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded border border-slate-700 bg-slate-900 text-xs font-semibold">
            {data.status}
          </span>
        ) : null}
      </div>

      {q.isLoading ? <div className="text-sm text-slate-400">Loading case…</div> : null}
      {q.isError ? <div className="text-sm text-risk-overdue">Unable to load case.</div> : null}

      {data ? (
        <>
          <div className="border border-slate-800 rounded-xl bg-white text-slate-900 p-4">
            <div className="text-sm font-semibold">Header</div>
            <div className="mt-2 grid grid-cols-2 gap-3 text-sm">
              <div>
                <div className="text-xs text-slate-600">Court</div>
                <div>{data.court_name}</div>
              </div>
              <div>
                <div className="text-xs text-slate-600">Judgment date</div>
                <div className="font-mono">{data.judgment_date ?? "—"}</div>
              </div>
            </div>
          </div>

          <div className="space-y-3">
            {data.directives.map((d) => (
              <DirectiveRow key={d.id} d={d} canAct={canAct} />
            ))}
          </div>

          <AuditTrail logs={data.audit_logs} />
        </>
      ) : null}
    </div>
  );
}

