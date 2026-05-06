import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { apiFetch } from "../api/client";
import type { CaseStatusResponse } from "../types/api";

type UploadResponse = { case_id: string; status: string; estimated_seconds: number };

const MAX_MB = 50;

function Step({ done, label }: { done: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div
        className={`h-2.5 w-2.5 rounded-full ${
          done ? "bg-risk-compliant" : "bg-slate-700"
        }`}
      />
      <div className={done ? "text-slate-200" : "text-slate-400"}>{label}</div>
    </div>
  );
}

export function Upload() {
  const nav = useNavigate();
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [caseId, setCaseId] = useState<string | null>(null);
  const [status, setStatus] = useState<CaseStatusResponse | null>(null);

  const valid = useMemo(() => {
    if (!file) return false;
    if (file.type !== "application/pdf") return false;
    if (file.size > MAX_MB * 1024 * 1024) return false;
    return true;
  }, [file]);

  useEffect(() => {
    let t: number | undefined;
    let attempts = 0;
    const MAX_ATTEMPTS = 80; // 2 minutes max
    if (caseId) {
      const tick = async () => {
        try {
          const res = await apiFetch<CaseStatusResponse>(`/api/cases/${caseId}/status`);
          setStatus(res);
          attempts++;
          if (res.status === "pending_review") {
            nav(`/cases/${caseId}/review`, { replace: true });
            return;
          }
          if (attempts >= MAX_ATTEMPTS) {
            setError("Processing timed out. Please try again.");
            return;
          }
          t = window.setTimeout(tick, 3000);
        } catch (e) {
          setError((e as Error).message);
        }
      };
      tick();
    }
    return () => { if (t) window.clearTimeout(t); };
  }, [caseId, nav]);

  async function doUpload() {
    if (!file) return;
    setError(null);
    if (!valid) {
      setError("Please select a valid PDF ≤ 50MB.");
      return;
    }
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await apiFetch<UploadResponse>("/api/upload", { method: "POST", body: form });
      setCaseId(res.case_id);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="text-xl font-semibold">Upload Judgment</div>
      <div className="text-xs text-slate-400 mt-1">PDF only. Max 50MB. Processing target: under 60 seconds.</div>

      <div className="mt-6 border border-slate-800 rounded-xl bg-slate-950/30 p-6">
        <button
          className="w-full border-2 border-dashed border-slate-700 rounded-xl p-10 text-center hover:border-slate-500"
          onClick={() => inputRef.current?.click()}
        >
          <div className="text-sm font-semibold">Drag & drop or click to select PDF</div>
          <div className="text-xs text-slate-400 mt-1">
            Stored on-premise under <span className="font-mono">/storage/judgments</span>
          </div>
          {file ? (
            <div className="mt-4 text-sm text-slate-200 font-mono">{file.name}</div>
          ) : null}
        </button>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />

        <div className="mt-4 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            Validation: {file ? (valid ? "OK" : "Invalid") : "No file selected"}
          </div>
          <button
            disabled={!file || uploading}
            onClick={doUpload}
            className="px-4 py-2 rounded-md bg-saffron text-slate-950 font-semibold disabled:opacity-40"
          >
            Upload
          </button>
        </div>

        {error ? <div className="mt-4 text-sm text-risk-overdue">{error}</div> : null}
      </div>

      {caseId ? (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          className="mt-6 border border-slate-800 rounded-xl bg-slate-950/30 p-6"
        >
          <div className="text-sm font-semibold">Processing</div>
          <div className="text-xs text-slate-400 mt-1">Case ID: <span className="font-mono">{caseId}</span></div>

          <div className="mt-4 space-y-2">
            <Step done={true} label="✓ PDF Received" />
            <Step done={(status?.progress_percent ?? 0) >= 25} label="⟳ OCR Extraction" />
            <Step done={(status?.progress_percent ?? 0) >= 55} label="⟳ AI Analysis" />
            <Step done={(status?.progress_percent ?? 0) >= 80} label="⟳ Timeline Computation" />
            <Step done={status?.status === "pending_review"} label="✓ Ready for Review" />
          </div>

          <div className="mt-4 text-xs text-slate-400">
            {status ? (
              <>
                {status.message} — {status.progress_percent}%
              </>
            ) : (
              "Waiting for status…"
            )}
          </div>
        </motion.div>
      ) : null}
    </div>
  );
}

