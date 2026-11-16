import type {
  Connection, Meta, ModelInfo, Profile, Rankings, Similar, Summary, Teammates, Valuation,
} from "./types";

const BASE = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ??
  (import.meta.env.DEV ? "http://127.0.0.1:8000" : ""); // built site: the API serves it, so same origin

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

type Params = Record<string, string | number | null | undefined>;

async function get<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  for (const [k, v] of Object.entries(params)) {
    if (v !== null && v !== undefined && v !== "") url.searchParams.set(k, String(v));
  }
  let res: Response;
  try {
    res = await fetch(url, { signal });
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    throw new ApiError(0, `Can't reach the ScoutLens API at ${BASE || window.location.origin}. Start it with: uvicorn api.main:app --reload`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
    } catch { /* keep statusText */ }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

let metaCache: Promise<Meta> | null = null;

export const api = {
  meta: () => (metaCache ??= get<Meta>("/meta").catch((e) => { metaCache = null; throw e; })),
  search: (q: string, limit = 8, signal?: AbortSignal) => get<Summary[]>("/players/search", { q, limit }, signal),
  player: (id: number, signal?: AbortSignal) => get<Profile>(`/players/${id}`, {}, signal),
  valuation: (id: number, season?: number | null, signal?: AbortSignal) =>
    get<Valuation>(`/players/${id}/valuation`, { season }, signal),
  similar: (id: number, k = 6, scope: "active" | "all" = "active", signal?: AbortSignal) =>
    get<Similar>(`/players/${id}/similar`, { k, scope }, signal),
  teammates: (id: number, limit = 12, signal?: AbortSignal) => get<Teammates>(`/players/${id}/teammates`, { limit }, signal),
  connection: (a: number, b: number, signal?: AbortSignal) => get<Connection>("/connections", { a, b }, signal),
  rankings: (params: Params, signal?: AbortSignal) => get<Rankings>("/rankings", params, signal),
  modelInfo: (signal?: AbortSignal) => get<ModelInfo>("/model/info", {}, signal),
};
