/**
 * Safe localStorage wrapper — no-ops on the server or in environments where
 * localStorage is unavailable.
 *
 * Security note: storing the JWT in localStorage means it is readable by any
 * JavaScript running on the page (XSS risk). This is mitigated by the CSP
 * headers in next.config.mjs which restrict script sources. A future
 * improvement (Phase 3) is to move to httpOnly cookies set by the backend,
 * which removes JS access to the token entirely.
 */

function isAvailable(): boolean {
  try {
    return (
      typeof window !== "undefined" &&
      typeof window.localStorage !== "undefined" &&
      typeof window.localStorage.getItem === "function"
    );
  } catch {
    return false;
  }
}

export const storage = {
  get(key: string): string | null {
    if (!isAvailable()) return null;
    try { return window.localStorage.getItem(key); } catch { return null; }
  },
  set(key: string, value: string): void {
    if (!isAvailable()) return;
    try { window.localStorage.setItem(key, value); } catch { /* noop */ }
  },
  remove(key: string): void {
    if (!isAvailable()) return;
    try { window.localStorage.removeItem(key); } catch { /* noop */ }
  },
};
