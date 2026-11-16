import { useMemo, useRef, useState } from "react";
import { eur, seasonLabel, shortDate } from "../format";
import type { ValuePoint } from "../types";

export interface Series {
  name: string;
  color: string;
  points: ValuePoint[];
  forecast?: { low: number; mid: number; high: number; season: number };
}

const W = 760;
const H = 280;
const M = { t: 16, r: 24, b: 30, l: 56 };

/** Market value over time as a step line (a value stays until Transfermarkt changes it). */
export function ValueChart({ series }: { series: Series[] }) {
  const ref = useRef<SVGSVGElement>(null);
  const [hover, setHover] = useState<{ s: number; i: number } | null>(null);

  const geo = useMemo(() => {
    const all = series.flatMap((s) => s.points.map((p) => ({ t: new Date(p.date).getTime(), v: p.value_eur })));
    if (all.length === 0) return null;
    const lastT = Math.max(...all.map((p) => p.t));
    const fcT = lastT + 365 * 864e5;
    const hasFc = series.some((s) => s.forecast);
    const t0 = Math.min(...all.map((p) => p.t));
    const t1 = hasFc ? fcT : lastT;
    const vMax = Math.max(...all.map((p) => p.v), ...series.map((s) => s.forecast?.high ?? 0)) * 1.08;
    return { t0, t1, vMax, fcT };
  }, [series]);

  if (!geo) return <p className="muted">No market value history for this player.</p>;
  const { t0, t1, vMax, fcT } = geo;
  const x = (t: number) => M.l + ((t - t0) / Math.max(1, t1 - t0)) * (W - M.l - M.r);
  const y = (v: number) => H - M.b - (v / vMax) * (H - M.t - M.b);

  const yTicks = (() => {
    const step = [1e6, 2e6, 5e6, 10e6, 20e6, 25e6, 50e6, 100e6].find((s) => vMax / s <= 5) ?? 100e6;
    const out: number[] = [];
    for (let v = 0; v <= vMax; v += step) out.push(v);
    return out;
  })();
  const years: number[] = [];
  for (let yr = new Date(t0).getFullYear() + 1; new Date(`${yr}-01-01`).getTime() <= t1; yr++) years.push(yr);
  const yearStep = Math.max(1, Math.ceil(years.length / 7));

  const path = (pts: ValuePoint[]) => {
    let d = "";
    pts.forEach((p, i) => {
      const t = new Date(p.date).getTime();
      d += i === 0 ? `M${x(t)},${y(p.value_eur)}` : `H${x(t)}V${y(p.value_eur)}`;
    });
    const last = pts[pts.length - 1];
    return d + `H${x(new Date(last.date).getTime())}`;
  };

  const onMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const box = ref.current!.getBoundingClientRect();
    const t = t0 + (((e.clientX - box.left) / box.width) * W - M.l) / (W - M.l - M.r) * (t1 - t0);
    let best: { s: number; i: number; d: number } | null = null;
    series.forEach((s, si) => s.points.forEach((p, i) => {
      const d = Math.abs(new Date(p.date).getTime() - t);
      if (!best || d < best.d) best = { s: si, i, d };
    }));
    setHover(best);
  };

  const hp = hover ? series[hover.s].points[hover.i] : null;
  const summary = series.map((s) => {
    const last = s.points[s.points.length - 1];
    return `${s.name}: ${eur(last?.value_eur)} on ${last ? shortDate(last.date) : "n/a"}`;
  }).join(". ");

  return (
    <div className="chart-wrap">
      <svg ref={ref} className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Market value history. ${summary}`}
        onPointerMove={onMove} onPointerLeave={() => setHover(null)}>
        {yTicks.map((v) => (
          <g key={v}>
            <line x1={M.l} x2={W - M.r} y1={y(v)} y2={y(v)} className="chart-grid" />
            <text x={M.l - 8} y={y(v) + 4} textAnchor="end" className="chart-tick">{v === 0 ? "0" : eur(v)}</text>
          </g>
        ))}
        {years.filter((_, i) => i % yearStep === 0).map((yr) => (
          <text key={yr} x={x(new Date(`${yr}-01-01`).getTime())} y={H - 8} textAnchor="middle" className="chart-tick">{yr}</text>
        ))}

        {series.map((s) => s.points.length > 0 && (
          <g key={s.name}>
            <path d={path(s.points)} fill="none" stroke={s.color} strokeWidth="2.25" strokeLinejoin="round" />
            {s.points.length < 40 && s.points.map((p) => (
              <circle key={p.date} cx={x(new Date(p.date).getTime())} cy={y(p.value_eur)} r="2.5" fill={s.color} />
            ))}
            {s.forecast && (() => {
              const last = s.points[s.points.length - 1];
              const lx = x(new Date(last.date).getTime());
              const fx = x(fcT);
              return (
                <g className="chart-forecast">
                  <line x1={lx} y1={y(last.value_eur)} x2={fx} y2={y(s.forecast.mid)} stroke={s.color} strokeWidth="2" strokeDasharray="4 4" />
                  <line x1={fx} x2={fx} y1={y(s.forecast.high)} y2={y(s.forecast.low)} stroke={s.color} strokeWidth="2" />
                  <line x1={fx - 5} x2={fx + 5} y1={y(s.forecast.high)} y2={y(s.forecast.high)} stroke={s.color} strokeWidth="2" />
                  <line x1={fx - 5} x2={fx + 5} y1={y(s.forecast.low)} y2={y(s.forecast.low)} stroke={s.color} strokeWidth="2" />
                  <circle cx={fx} cy={y(s.forecast.mid)} r="4.5" fill="var(--paper)" stroke={s.color} strokeWidth="2" />
                  <text x={fx} y={y(s.forecast.high) - 8} textAnchor="end" className="chart-tick">
                    forecast {seasonLabel(s.forecast.season)}: {eur(s.forecast.mid)}
                  </text>
                </g>
              );
            })()}
          </g>
        ))}

        {hover && hp && (() => {
          const px = x(new Date(hp.date).getTime());
          const flip = px > W * 0.7;
          return (
            <g pointerEvents="none">
              <line x1={px} x2={px} y1={M.t} y2={H - M.b} className="chart-cursor" />
              <circle cx={px} cy={y(hp.value_eur)} r="5" fill={series[hover.s].color} stroke="var(--paper)" strokeWidth="2" />
              <g transform={`translate(${flip ? px - 8 : px + 8},${Math.max(M.t + 14, y(hp.value_eur) - 10)})`}>
                <text textAnchor={flip ? "end" : "start"} className="chart-tip">
                  {series.length > 1 ? `${series[hover.s].name}: ` : ""}{eur(hp.value_eur)}, {shortDate(hp.date)}
                </text>
              </g>
            </g>
          );
        })()}
      </svg>
      {series.length > 1 && (
        <ul className="legend">
          {series.map((s) => <li key={s.name}><i style={{ background: s.color }} />{s.name}</li>)}
        </ul>
      )}
    </div>
  );
}
