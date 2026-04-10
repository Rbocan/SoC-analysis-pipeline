/** Safe localStorage wrapper — no-ops on the server or in environments where localStorage is unavailable. */

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
