import { eur } from "../format";

const SPAN = 1.6; // x-axis covers model value x e^-1.6 .. x e^+1.6 (about 0.2x to 5x)

/**
 * One valuation at a glance. The tall line is the model's estimate, the band is its 80%
 * prediction interval, the dot is the market value. Dot left of the band: the market values
 * the player below what the model expects. Right of it: above.
 */
export function RangeGauge({ market, model, low, high, width = 150 }: { market: number; model: number; low: number; high: number; width?: number }) {
  const h = 22;
  const x = (v: number) => (((Math.max(-1, Math.min(1, Math.log(v / model) / SPAN)) + 1) / 2) * (width - 8)) + 4;
  const side = market < low ? "below" : market > high ? "above" : "inside";
  const desc = side === "inside" ? "inside the model interval" : side === "below" ? "below the model interval" : "above the model interval";
  return (
    <svg className="gauge" width={width} height={h} viewBox={`0 0 ${width} ${h}`} role="img"
      aria-label={`Market ${eur(market)} is ${desc}. Model ${eur(model)}, 80% interval ${eur(low)} to ${eur(high)}.`}>
      <title>{`Market ${eur(market)} · Model ${eur(model)} (${eur(low)} to ${eur(high)})`}</title>
      <line x1="4" x2={width - 4} y1={h / 2} y2={h / 2} className="gauge-axis" />
      <rect x={x(low)} y={h / 2 - 5} width={Math.max(2, x(high) - x(low))} height="10" rx="2" className="gauge-band" />
      <line x1={x(model)} x2={x(model)} y1="2" y2={h - 2} className="gauge-model" />
      <circle cx={x(market)} cy={h / 2} r="4.5" className={`gauge-dot gauge-${side}`} />
    </svg>
  );
}
