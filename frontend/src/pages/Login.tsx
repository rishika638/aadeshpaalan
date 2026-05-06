import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { apiFetch, setSession } from "../api/client";

export function Login() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const [email, setEmail] = useState("reviewer@karnataka.gov.in");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  return (
    <div className="max-w-lg mx-auto">
      <div className="border border-slate-800 rounded-xl bg-slate-950/30 p-6">
        <div className="text-xl font-semibold">Sign in</div>
        <div className="text-xs text-slate-400 mt-1">
          Internal access only. Session timeout: 8 hours (enforced by backend JWT).
        </div>

        <div className="mt-6 space-y-3">
          <label className="block">
            <div className="text-xs text-slate-400 mb-1">Email</div>
            <input
              className="w-full bg-slate-900 border border-slate-800 rounded-md px-3 py-2 text-sm"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
        </div>

        <button
          disabled={loading}
          className="mt-6 w-full px-4 py-2 rounded-md bg-saffron text-slate-950 font-semibold hover:brightness-95 disabled:opacity-40"
          onClick={async () => {
            setError(null);
            setLoading(true);
            try {
              const res = await apiFetch<{ access_token: string; name: string; role: string }>("/api/auth/login", {
                method: "POST",
                body: JSON.stringify({ email })
              });
              setSession({ token: res.access_token, name: res.name, role: res.role as any });
              await qc.invalidateQueries();
              nav("/", { replace: true });
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setLoading(false);
            }
          }}
        >
          Continue
        </button>
        {error ? <div className="mt-4 text-sm text-risk-overdue">{error}</div> : null}
      </div>
    </div>
  );
}

