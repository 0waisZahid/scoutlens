export function PercentileBars({ values, labels }: { values: Record<string, number | null>; labels: Record<string, string> }) {
  const keys = Object.keys(labels);
  if (keys.every((k) => values[k] === null)) return <p className="muted">Not enough minutes (450 needed) in the latest season to compare with similar players.</p>;
  return (
    <ul className="pctbars">
      {keys.map((k) => {
        const v = values[k];
        return (
          <li key={k}>
            <span className="pctbar-name">{labels[k]}</span>
            <span className="pctbar-track" role="img" aria-label={v === null ? "no data" : `${v}th percentile`}>
              {[25, 50, 75].map((m) => <u key={m} style={{ left: `${m}%` }} />)}
              {v !== null && <i style={{ width: `${v}%` }} />}
            </span>
            <span className="pctbar-num mono">{v === null ? "–" : v}</span>
          </li>
        );
      })}
    </ul>
  );
}
