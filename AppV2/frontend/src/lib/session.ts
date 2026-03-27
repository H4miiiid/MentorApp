import { browser } from "$app/environment";
import { apiFetch, clearToken, getToken, type MeResponse } from "$lib/api";

/** Use with `depends()` in `load` and `invalidate()` after login/logout so layout session re-runs. */
export const SESSION_DEPENDENCY = "app:session";

/**
 * Validates stored JWT against `/api/auth/me`. Clears token on failure.
 * Returns `null` when there is no token or the session is invalid/expired.
 */
export async function fetchSession(): Promise<MeResponse | null> {
  if (!browser) return null;
  if (!getToken()) return null;
  const res = await apiFetch("/api/auth/me");
  if (!res.ok) {
    clearToken();
    return null;
  }
  return res.json() as Promise<MeResponse>;
}
