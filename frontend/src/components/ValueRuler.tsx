import { eur, pct, seasonLabel } from "../format";
import type { Valuation } from "../types";

const W = 760, X0 = 150, X1 = 735;

export interface RulerItem { name: string; v: Valuation; tone: "a" | "b" }

function niceTicks(lo: number, hi: number): number[] {
  const out: number[] = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++)
    for (const m of [1, 2, 5]) { const v = m * 10 ** e; if (v >= lo && v <= hi) out.push(v); }
  return out;
}

/**
 * Market value, model estimate with its 80% interval, and the next-season forecast on ONE shared
 * log euro axis. With several players the axis is shared too, so widths and positions compare fairly.
 */
export function ValueRuler({ items }: { items: RulerItem[] }) {
  const all = items.flatMap(({ v }) => [v.market_value_eur, v.low_eur, v.high_eur, v.forecast.low_eur, v.forecast.high_eur]);
  const lo = Math.min(...all) * 0.75, hi = Math.max(...all) * 1.3;
  const x = (val: number) => X0 + ((Math.log(val) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))) * (X1 - X0);
  const multi = items.length > 1;
  const blockH = 196, head = multi ? 26 : 0;
  const axisY = items.length * blockH + head * items.length + 6;
  const ticks = niceTicks(lo, hi);

  return (
    <svg className="ruler" viewBox={`0 0 ${W} ${axisY + 30}`} role="img"
      aria-label={items.map(({ name, v }) => `${name}: market ${eur(v.market_value_eur)}, model ${eur(v.model_value_eur)} with 80% interval ${eur(v.low_eur)} to ${eur(v.high_eur)}, forecast ${eur(v.forecast.forecast_eur)} for ${seasonLabel(v.forecast.for_season)}.`).join(" ")}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1="6" y2={axisY} className="ruler-grid" />
          <text x={x(t)} y={axisY + 20} textAnchor="middle" className="ruler-tick">{eur(t)}</text>
        </g>
      ))}
      <line x1={X0} x2={X1} y1={axisY} y2={axisY} className="ruler-axis" />

      {items.map(({ name, v, tone }, i) => {
        const y0 = i * (blockH + head) + head;
        const rows = { market: y0 + 38, model: y0 + 100, fc: y0 + 160 };
        const f = v.forecast;
        const band = (y: number, low: number, high: number, mid: number, forecast: boolean) => (
          <g>
            <rect x={x(low)} y={y - 8} width={Math.max(3, x(high) - x(low))} height="16" rx="3" className={`ruler-band tone-${tone}${forecast ? " is-forecast" : ""}`} />
            <line x1={x(mid)} x2={x(mid)} y1={y - 15} y2={y + 15} className={`ruler-point tone-${tone}`} />
            <text x={x(mid)} y={y - 21} textAnchor="middle" className="ruler-value mono">{eur(mid)}</text>
            <text x={x(low) - 7} y={y + 4} textAnchor="end" className="ruler-end mono">{eur(low)}</text>
            <text x={x(high) + 7} y={y + 4} textAnchor="start" className="ruler-end mono">{eur(high)}</text>
          </g>
        );
        return (
          <g key={name}>
            {multi && <text x="0" y={y0 - 8} className={`ruler-name tone-${tone}`}>{name}</text>}
            <text x="0" y={rows.market + 4} className="ruler-label">Market value</text>
            <text x="0" y={rows.model + 4} className="ruler-label">Model estimate</text>
            <text x="0" y={rows.fc - 3} className="ruler-label">Forecast</text>
            <text x="0" y={rows.fc + 12} className="ruler-sub">{seasonLabel(f.for_season)}</text>
            <line x1={x(v.market_value_eur)} x2={x(v.market_value_eur)} y1={rows.market + 14} y2={rows.fc + 22} className={`ruler-market-line tone-${tone}`} />
            <rect x={x(v.market_value_eur) - 3} y={rows.market - 15} width="6" height="30" rx="1.5" className={`ruler-market tone-${tone}`} />
            <text x={x(v.market_value_eur)} y={rows.market - 21} textAnchor="middle" className="ruler-value mono">{eur(v.market_value_eur)}</text>
            {band(rows.model, v.low_eur, v.high_eur, v.model_value_eur, false)}
            {band(rows.fc, f.low_eur, f.high_eur, f.forecast_eur, true)}
            {f.expected_change_pct !== null && (
              <text x={X1} y={rows.fc + 34} textAnchor="end" className="ruler-note mono">{pct(f.expected_change_pct)} vs market value today</text>
            )}
          </g>
        );
      })}
    </svg>
  );
}
