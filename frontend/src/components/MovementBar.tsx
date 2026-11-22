/** Projected movement as a diverging bar around zero. `max` keeps bars comparable within one list. */
export function MovementBar({ pct, max }: { pct: number | null; max: number }) {
  if (pct === null) return <span className="move move-none" aria-hidden="true" />;
  const w = Math.min(50, (Math.abs(pct) / Math.max(max, 1)) * 50);
  return (
    <span className="move" aria-hidden="true">
      <i className={pct >= 0 ? "move-up" : "move-down"} style={{ width: `${w}%`, [pct >= 0 ? "left" : "right"]: "50%" }} />
    </span>
  );
}
