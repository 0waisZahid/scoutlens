import { useEffect, useState, useSyncExternalStore } from "react";

export interface AsyncState<T> {
  data: T | undefined;
  error: string | undefined;
  loading: boolean;
}

/** Runs `fn` whenever `deps` change; cancels the previous request. */
export function useAsync<T>(fn: (signal: AbortSignal) => Promise<T>, deps: unknown[]): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ data: undefined, error: undefined, loading: true });
  useEffect(() => {
    const ctl = new AbortController();
    setState((s) => ({ data: s.data, error: undefined, loading: true }));
    fn(ctl.signal).then(
      (data) => !ctl.signal.aborted && setState({ data, error: undefined, loading: false }),
      (e: Error) => {
        if (ctl.signal.aborted || e.name === "AbortError") return;
        setState({ data: undefined, error: e.message, loading: false });
      },
    );
    return () => ctl.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

export function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

export function useTitle(title: string) {
  useEffect(() => {
    document.title = title ? `${title} · ScoutLens` : "ScoutLens";
  }, [title]);
}

// ---- watchlist: saved in the browser, shared across components ------------------------
export interface Saved {
  id: number;
  name: string;
}
const KEY = "scoutlens.watchlist";
const listeners = new Set<() => void>();
let snapshot: Saved[] = read();

function read(): Saved[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x?.id === "number") : [];
  } catch {
    return [];
  }
}
function write(next: Saved[]) {
  snapshot = next;
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch { /* private mode: keep in memory only */ }
  listeners.forEach((l) => l());
}
const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};

export function useWatchlist() {
  const list = useSyncExternalStore(subscribe, () => snapshot);
  return {
    list,
    has: (id: number) => list.some((s) => s.id === id),
    toggle: (p: Saved) => write(list.some((s) => s.id === p.id) ? list.filter((s) => s.id !== p.id) : [...list, p]),
    remove: (id: number) => write(list.filter((s) => s.id !== id)),
  };
}

// ---- theme ------------------------------------------------------------------------------
export function useTheme(): ["light" | "dark", () => void] {
  const get = () =>
    (document.documentElement.dataset.theme as "light" | "dark" | undefined) ??
    (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const [theme, setTheme] = useState<"light" | "dark">(get);
  const toggle = () => {
    const next = theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("scoutlens.theme", next); } catch { /* ignore */ }
    setTheme(next);
  };
  return [theme, toggle];
}
