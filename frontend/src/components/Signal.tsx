import { pct, type Signal } from "../format";

const LABEL: Record<Signal, string> = { below: "Undervalued", inside: "Fair value", above: "Overvalued" };
const MARK: Record<Signal, string> = { below: "▲", inside: "■", above: "▼" };

/** Market value against the model's 80% interval. Always text + shape, never colour alone. */
export function SignalBadge({ signal, gap, compact }: { signal: Signal; gap?: number | null; compact?: boolean }) {
  return (
    <span className={`badge badge-${signal}`} title="Where the market value sits against the model's 80% prediction interval">
      <span className="badge-mark" aria-hidden="true">{MARK[signal]}</span>
      {LABEL[signal]}
      {!compact && gap !== null && gap !== undefined && <b className="mono">{pct(gap)}</b>}
    </span>
  );
}
