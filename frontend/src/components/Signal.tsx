import { pct, type Signal } from "../format";

const LABEL: Record<Signal, string> = { below: "Undervalued", inside: "Fair value", above: "Overvalued" };
const ARROW: Record<Signal, string> = { below: "▲", inside: "●", above: "▼" };

/** The Value Signal: where the market sits against the model's 80% range. */
export function SignalBadge({ signal, gap, compact }: { signal: Signal; gap?: number | null; compact?: boolean }) {
  return (
    <span className={`signal signal-${signal}`} title="Market value compared with the model's 80% range">
      <span aria-hidden="true">{ARROW[signal]}</span>
      {LABEL[signal]}
      {!compact && gap !== null && gap !== undefined && <b>{pct(gap)}</b>}
    </span>
  );
}
