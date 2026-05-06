import { getSession } from "../api/sessionStore";

const API_BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/+$/, "") ?? "http://localhost:8000";

export function PDFViewer({ caseId }: { caseId: string }) {
  const session = getSession();
  const src = session
    ? `${API_BASE}/api/cases/${caseId}/pdf?token=${session.token}`
    : null;

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 pt-3 pb-2 flex items-center justify-between shrink-0">
        <div className="text-sm font-semibold text-slate-200">Judgment PDF</div>
        {src && (
          <a
            href={src}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-saffron hover:underline"
          >
            Open in new tab ↗
          </a>
        )}
      </div>
      {src ? (
        <iframe
          src={src}
          className="flex-1 w-full border-0 min-h-0"
          title="Judgment PDF"
        />
      ) : (
        <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
          Not authenticated
        </div>
      )}
    </div>
  );
}
