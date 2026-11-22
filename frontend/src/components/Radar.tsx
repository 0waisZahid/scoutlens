interface Poly { name: string; tone: "a" | "b"; values: (number | null)[] }

/** Percentile radar, 0-100 on every axis (the same scale for every player and axis). */
export function Radar({ labels, polys }: { labels: string[]; polys: Poly[] }) {
  const S = 340, C = S / 2, R = 108, n = labels.length;
  const pt = (i: number, r: number) => { const a = -Math.PI / 2 + (i * 2 * Math.PI) / n; return [C + Math.cos(a) * r, C + Math.sin(a) * r] as const; };
  const ring = (f: number) => labels.map((_, i) => pt(i, R * f).join(",")).join(" ");
  return (
    <svg className="radar" viewBox={`-50 0 ${S + 100} ${S}`} role="img"
      aria-label={`Percentile profile, 0 to 100. ${polys.map((p) => `${p.name}: ${p.values.map((v, i) => `${labels[i]} ${v ?? "n/a"}`).join(", ")}`).join(". ")}`}>
      {[0.25, 0.5, 0.75, 1].map((f) => <polygon key={f} points={ring(f)} className="radar-ring" />)}
      {labels.map((_, i) => <line key={i} x1={C} y1={C} x2={pt(i, R)[0]} y2={pt(i, R)[1]} className="radar-ring" />)}
      {polys.map((p) => (
        <polygon key={p.name} points={p.values.map((v, i) => pt(i, (R * (v ?? 0)) / 100).join(",")).join(" ")} className={`radar-poly tone-${p.tone}`} />
      ))}
      {labels.map((l, i) => { const [x, y] = pt(i, R + 22); return <text key={l} x={x} y={y + 4} textAnchor={x < C - 4 ? "end" : x > C + 4 ? "start" : "middle"} className="radar-label">{l}</text>; })}
    </svg>
  );
}
