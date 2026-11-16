import { eur, pct, seasonLabel } from "../format";
import type { Valuation } from "../types";

const W = 760;
const X0 = 150;
const X1 = 730;

function niceTicks(lo: number, hi: number): number[] {
  const out: number[] = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) {
    for (const m of [1, 2, 5]) {
      const v = m * 10 ** e;
      if (v >= lo && v <= hi) out.push(v);
    }
  }
  return out;
}

/**
 * The signature chart. One shared euro axis (log scale, so €2M and €200M are both readable) with
 * the market value, the model's estimate with its 80% range, and the next-season forecast with
 * its range. Reading across shows how far apart the three views are.
 */
export function ValueRuler({ v }: { v: Valuation }) {
  const f = v.forecast;
  const all = [v.market_value_eur, v.low_eur, v.high_eur, f.low_eur, f.high_eur];
  const lo = Math.min(...all) * 0.75;
  const hi = Math.max(...all) * 1.3;
  const x = (val: number) => X0 + ((Math.log(val) - Math.log(lo)) / (Math.log(hi) - Math.log(lo))) * (X1 - X0);
  const ticks = niceTicks(lo, hi);
  const rows = { market: 44, model: 108, forecast: 172 };
  const axisY = 216;
  const mx = x(v.market_value_eur);

  const band = (y: number, low: number, high: number, mid: number, cls: string, label: string) => (
    <g>
      <rect x={x(low)} y={y - 8} width={Math.max(3, x(high) - x(low))} height="16" rx="3" className={cls} />
      <line x1={x(mid)} x2={x(mid)} y1={y - 15} y2={y + 15} className="ruler-point" />
      <text x={x(mid)} y={y - 22} textAnchor="middle" className="ruler-value">{label}</text>
      <text x={x(low) - 7} y={y + 4} textAnchor="end" className="ruler-end">{eur(low)}</text>
      <text x={x(high) + 7} y={y + 4} textAnchor="start" className="ruler-end">{eur(high)}</text>
    </g>
  );

  return (
    <svg className="ruler" viewBox={`0 0 ${W} 240`} role="img"
      aria-label={`Market value ${eur(v.market_value_eur)}. Model estimate ${eur(v.model_value_eur)}, 80% range ${eur(v.low_eur)} to ${eur(v.high_eur)}. Forecast for ${seasonLabel(f.for_season)} ${eur(f.forecast_eur)}, range ${eur(f.low_eur)} to ${eur(f.high_eur)}.`}>
      {ticks.map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1="10" y2={axisY} className="ruler-grid" />
          <text x={x(t)} y={axisY + 18} textAnchor="middle" className="ruler-tick">{eur(t)}</text>
        </g>
      ))}
      <line x1={X0} x2={X1} y1={axisY} y2={axisY} className="ruler-axis" />

      <text x="0" y={rows.market + 4} className="ruler-label">Market value</text>
      <text x="0" y={rows.model + 4} className="ruler-label">Model estimate</text>
      <text x="0" y={rows.forecast + 4} className="ruler-label">Forecast {seasonLabel(f.for_season)}</text>

      <line x1={mx} x2={mx} y1={rows.market + 14} y2={axisY} className="ruler-market-line" />
      <rect x={mx - 3} y={rows.market - 16} width="6" height="32" rx="1.5" className="ruler-market" />
      <text x={mx} y={rows.market - 24} textAnchor="middle" className="ruler-value">{eur(v.market_value_eur)}</text>

      {band(rows.model, v.low_eur, v.high_eur, v.model_value_eur, "ruler-band", eur(v.model_value_eur))}
      {band(rows.forecast, f.low_eur, f.high_eur, f.forecast_eur, "ruler-band ruler-band-forecast", eur(f.forecast_eur))}

      {f.expected_change_pct !== null && (
        <text x={X1} y={rows.forecast + 36} textAnchor="end" className="ruler-note">
          {pct(f.expected_change_pct)} vs today's market value
        </text>
      )}
    </svg>
  );
}
