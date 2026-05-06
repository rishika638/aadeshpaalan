import { useSyncExternalStore } from "react";
import type { AuthSession } from "./client";

const STORAGE_KEY = "aadeshpaalan.session";

type Listener = () => void;
const listeners = new Set<Listener>();
let cachedSession: AuthSession | null = parseSession();

function parseSession(): AuthSession | null {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try { return JSON.parse(raw) as AuthSession; } catch { return null; }
}

function emit() {
  cachedSession = parseSession();
  for (const l of listeners) l();
}

export function getSession(): AuthSession | null {
  return cachedSession;
}

export function setSession(session: AuthSession | null) {
  if (!session) localStorage.removeItem(STORAGE_KEY);
  else localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
  emit();
}

export function useSession() {
  return useSyncExternalStore(
    (cb) => { listeners.add(cb); return () => listeners.delete(cb); },
    () => cachedSession,
    () => null
  );
}
