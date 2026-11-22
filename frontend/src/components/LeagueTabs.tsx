import { LEAGUES } from "../format";

/** League filter as underline tabs: the active one is bright with a lime rule. */
export function LeagueTabs({ value, onChange, label = "League" }: { value: string; onChange: (v: string) => void; label?: string }) {
  const items: [string, string][] = [["", "All leagues"], ...Object.entries(LEAGUES)];
  return (
    <div className="tabs" role="group" aria-label={label}>
      {items.map(([k, v]) => (
        <button key={k || "all"} className={`tab${value === k ? " is-on" : ""}`} aria-pressed={value === k} onClick={() => onChange(k)}>{v}</button>
      ))}
    </div>
  );
}
