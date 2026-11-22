import { useMemo, useRef, useState } from "react";
import { eur, seasonLabel, shortDate } from "../format";
import type { ModelPoint, ValuePoint } from "../types";

export interface Series {
  name: string;
  tone: "a" | "b";
  market: ValuePoint[];
  model?: ModelPoint[];                // model value per season (only drawn when provided)
  forecast?: { low: number; mid: number; high: number; season: number };
}

const W = 760, H = 300, M = { t: 18, r: 28, b: 32, l: 58 };
const TRAIN_END = (testFrom: number) => new Date(`${testFrom}-07-01`).getTime();

/**
 * Market value history (solid step line) with the model's per-season estimate and 80% interval
 * (whisker + ring) and the next-season forecast (dashed, labelled). Seasons the model trained on
 * are shaded: the model value there is in-sample and looks better than it would out of sample.
 */
export function ValueChart({ series, testFrom, showModel = true }: { series: Series[]; testFrom?: number; showModel?: boolean }) {
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<{ s: number; i: number } | null>(null);

  const geo = useMemo(() => {
    const ts: number[] = [], vs: number[] = [];
    for (const s of series) {
      for (const p of s.market) { ts.push(new Date(p.date).getTime()); vs.push(p.value_eur); }
      if (showModel) for (const m of s.model ?? []) if (m.date) { ts.push(new Date(m.date).getTime()); vs.push(m.high_eur, m.low_eur); }
      if (s.forecast) vs.push(s.forecast.high);
    }
    if (!ts.length) return null;
    const lastT = Math.max(...ts);
    return { t0: Math.min(...ts), t1: series.some((s) => s.forecast) ? lastT + 365 * 864e5 : lastT, vMax: Math.max(...vs) * 1.08, fcT: lastT + 365 * 864e5 };
  }, [series, showModel]);

  if (!geo) return <p className="muted">No market value history for this player.</p>;
  const { t0, t1, vMax, fcT } = geo;
  const x = (t: number) => M.l + ((t - t0) / Math.max(1, t1 - t0)) * (W - M.l - M.r);
  const y = (v: number) => H - M.b - (v / vMax) * (H - M.t - M.b);
  const step = [1e6, 2e6, 5e6, 10e6, 20e6, 25e6, 50e6, 100e6].find((s) => vMax / s <= 5) ?? 100e6;
  const yTicks: number[] = [];
  for (let v = 0; v <= vMax; v += step) yTicks.push(v);
  const years: number[] = [];
  for (let yr = new Date(t0).getFullYear() + 1; new Date(`${yr}-01-01`).getTime() <= t1; yr++) years.push(yr);
  const yStep = Math.max(1, Math.ceil(years.length / 7));

  const path = (pts: ValuePoint[]) => {
    let d = "";
    pts.forEach((p, i) => { const t = new Date(p.date).getTime(); d += i === 0 ? `M${x(t)},${y(p.value_eur)}` : `H${x(t)}V${y(p.value_eur)}`; });
    return d + `H${x(new Date(pts[pts.length - 1].date).getTime())}`;
  };

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const box = ref.current!.getBoundingClientRect();
    const t = t0 + ((((e.clientX - box.left) / box.width) * W - M.l) / (W - M.l - M.r)) * (t1 - t0);
    let best: { s: number; i: number; d: number } | null = null;
    series.forEach((s, si) => s.market.forEach((p, i) => {
      const d = Math.abs(new Date(p.date).getTime() - t);
      if (!best || d < best.d) best = { s: si, i, d };
    }));
    setHover(best);
  };

  const hp = hover ? series[hover.s].market[hover.i] : null;
  const hm = hover && hp && showModel
    ? (series[hover.s].model ?? []).reduce<ModelPoint | null>((b, m) => {
        if (!m.date) return b;
        const d = Math.abs(new Date(m.date).getTime() - new Date(hp.date).getTime());
        return !b || d < Math.abs(new Date(b.date!).getTime() - new Date(hp.date).getTime()) ? m : b;
      }, null)
    : null;
  const px = hp ? x(new Date(hp.date).getTime()) : 0;

  return (
    <div className="chart-wrap">
      <svg ref={ref} className="chart" viewBox={`0 0 ${W} ${H}`} role="img"
        aria-label={`Market value history. ${series.map((s) => `${s.name}: latest ${eur(s.market[s.market.length - 1]?.value_eur)}`).join(". ")}`}
        onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {testFrom && showModel && series.some((s) => s.model?.length) && x(TRAIN_END(testFrom)) > M.l && (
          <g>
            <rect x={M.l} y={M.t} width={Math.min(W - M.r, x(TRAIN_END(testFrom))) - M.l} height={H - M.t - M.b} className="chart-train" />
            <text x={M.l + 8} y={M.t + 14} className="chart-note">model trained on these seasons</text>
          </g>
        )}
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className="chart-grid" />
            <text x={M.l - 10} y={y(v) + 4} textAnchor="end" className="chart-tick mono">{v === 0 ? "0" : eur(v)}</text>
          </g>
        ))}
        {years.filter((_, i) => i % yStep === 0).map((yr) => (
          <text key={yr} x={x(new Date(`${yr}-01-01`).getTime())} y={H - 10} textAnchor="middle" className="chart-tick mono">{yr}</text>
        ))}

        {series.map((s) => s.market.length > 0 && (
          <g key={s.name} className={`tone-${s.tone}`}>
            {showModel && (s.model ?? []).filter((m) => m.date).map((m) => (
              <g key={m.season} className="chart-model">
                <line x1={x(new Date(m.date!).getTime())} x2={x(new Date(m.date!).getTime())} y1={y(m.high_eur)} y2={y(m.low_eur)} />
                <circle cx={x(new Date(m.date!).getTime())} cy={y(m.model_value_eur)} r="4" />
              </g>
            ))}
            <path d={path(s.market)} className="chart-line" />
            {s.market.length < 40 && s.market.map((p) => <circle key={p.date} cx={x(new Date(p.date).getTime())} cy={y(p.value_eur)} r="2.2" className="chart-dot" />)}
            {s.forecast && (() => {
              const last = s.market[s.market.length - 1];
              const lx = x(new Date(last.date).getTime()), fx = x(fcT), f = s.forecast;
              return (
                <g className="chart-forecast">
                  <line x1={lx} y1={y(last.value_eur)} x2={fx} y2={y(f.mid)} strokeDasharray="5 4" />
                  <line x1={fx} x2={fx} y1={y(f.high)} y2={y(f.low)} />
                  <line x1={fx - 5} x2={fx + 5} y1={y(f.high)} y2={y(f.high)} />
                  <line x1={fx - 5} x2={fx + 5} y1={y(f.low)} y2={y(f.low)} />
                  <circle cx={fx} cy={y(f.mid)} r="5" />
                  <text x={fx - 10} y={y(f.high) - 8} textAnchor="end" className="chart-note mono">forecast {seasonLabel(f.season)}: {eur(f.mid)}</text>
                </g>
              );
            })()}
          </g>
        ))}

        {hover && hp && (
          <g pointerEvents="none">
            <line x1={px} x2={px} y1={M.t} y2={H - M.b} className="chart-cursor" />
            <circle cx={px} cy={y(hp.value_eur)} r="5" className={`chart-hover tone-${series[hover.s].tone}`} />
            <g transform={`translate(${px > W * 0.62 ? px - 12 : px + 12},${Math.max(M.t + 16, y(hp.value_eur) - 18)})`}>
              <text textAnchor={px > W * 0.62 ? "end" : "start"} className="chart-tip mono">
                <tspan x="0">{series.length > 1 ? `${series[hover.s].name}: ` : ""}{eur(hp.value_eur)} market, {shortDate(hp.date)}</tspan>
                {hm && <tspan x="0" dy="16" className="chart-tip-2">model {eur(hm.model_value_eur)} ({eur(hm.low_eur)} to {eur(hm.high_eur)}){hm.in_sample ? ", in training data" : ""}</tspan>}
              </text>
            </g>
          </g>
        )}
      </svg>
      <p className="scroll-hint" aria-hidden="true">← scroll sideways for the full chart →</p>
      <ul className="legend">
        {series.map((s) => <li key={s.name}><i className={`key-line tone-${s.tone}`} />{series.length > 1 ? `${s.name} market value` : "Market value"}</li>)}
        {showModel && series.some((s) => s.model?.length) && <li><i className="key-model" />Model estimate and 80% interval</li>}
        {series.some((s) => s.forecast) && <li><i className="key-forecast" />Forecast</li>}
      </ul>
    </div>
  );
}
