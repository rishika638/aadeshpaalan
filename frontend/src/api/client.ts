import type { UserRole } from "../types/api";
import { getSession } from "./sessionStore";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string | undefined;

function getBaseUrl(): string {
  if (!API_BASE_URL) return "http://localhost:8000";
  return API_BASE_URL.replace(/\/+$/, "");
}

export type AuthSession = {
  token: string;
  role: UserRole;
  name: string;
};

export { setSession } from "./sessionStore";

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const session = getSession();
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (!(init?.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (session?.token) {
    headers.set("Authorization", `Bearer ${session.token}`);
  }

  const res = await fetch(`${getBaseUrl()}${path}`, {
    ...init,
    headers
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return (await res.json()) as T;
}

