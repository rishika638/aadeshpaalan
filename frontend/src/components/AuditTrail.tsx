import type { AuditLog } from "../types/api";
import { format, parseISO } from "date-fns";

export function AuditTrail({ logs }: { logs: AuditLog[] }) {
  return (
    <div className="border border-slate-800 rounded-xl bg-slate-950/30">
      <div className="p-4">
        <div className="text-sm font-semibold">Audit trail (append-only)</div>
        <div className="text-xs text-slate-400 mt-1">Every state change is recorded for CAG/RTI compliance.</div>
      </div>
      <div className="overflow-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-900/40 text-slate-300">
            <tr>
              <th className="text-left px-4 py-2 font-semibold">Officer</th>
              <th className="text-left px-4 py-2 font-semibold">Action</th>
              <th className="text-left px-4 py-2 font-semibold">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((l) => (
              <tr key={l.id} className="border-t border-slate-900">
                <td className="px-4 py-3 text-slate-200">{l.officer_name}</td>
                <td className="px-4 py-3 font-mono text-slate-300">{l.action}</td>
                <td className="px-4 py-3 font-mono text-slate-300">
                  {format(parseISO(l.timestamp), "dd MMM yyyy HH:mm")}
                </td>
              </tr>
            ))}
            {logs.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-slate-400">
                  No audit records available.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </div>
  );
}

