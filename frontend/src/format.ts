export const LEAGUES: Record<string, string> = {
  GB1: "Premier League", ES1: "La Liga", IT1: "Serie A", L1: "Bundesliga", FR1: "Ligue 1",
};

const trim = (n: number, d: number) => parseFloat(n.toFixed(d)).toString();

/** 12_500_000 -> "€12.5M", 850_000 -> "€850k" */
export function eur(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const a = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (a >= 1e9) return `${sign}€${trim(a / 1e9, 2)}B`;
  if (a >= 1e8) return `${sign}€${trim(a / 1e6, 0)}M`;
  if (a >= 1e7) return `${sign}€${trim(a / 1e6, 1)}M`;
  if (a >= 1e6) return `${sign}€${trim(a / 1e6, 2)}M`;
  if (a >= 1e3) return `${sign}€${trim(a / 1e3, 0)}k`;
  return `${sign}€${Math.round(a)}`;
}

export function pct(v: number | null | undefined, digits = 0, signed = true): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "–";
  const s = v.toFixed(digits);
  return `${signed && v > 0 ? "+" : ""}${s}%`;
}

/** 2025 -> "2025/26" */
export function seasonLabel(s: number): string {
  return `${s}/${String((s + 1) % 100).padStart(2, "0")}`;
}

export const num1 = (v: number | null | undefined) => (v === null || v === undefined ? "–" : v.toFixed(1));
export const num2 = (v: number | null | undefined) => (v === null || v === undefined ? "–" : v.toFixed(2));
export const int = (v: number | null | undefined) => (v === null || v === undefined ? "–" : Math.round(v).toLocaleString("en-US"));

export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-GB", { month: "short", year: "numeric" });
}

export const clubLabel = (c: { club_name: string | null; club_id: number }) => c.club_name ?? `Club ${c.club_id}`;

export const POS_CODE: Record<string, string> = { Attack: "FW", Midfield: "MF", Defender: "DF", Goalkeeper: "GK" };
export const posCode = (label: string) => POS_CODE[label] ?? label;

export type Signal = "below" | "above" | "inside";
/** Where the market value sits against the model's 80% range. */
export const signalOf = (market: number, low: number, high: number): Signal =>
  market < low ? "below" : market > high ? "above" : "inside";
