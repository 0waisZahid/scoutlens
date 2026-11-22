import { Link } from "react-router-dom";
import { clubLabel, eur, LEAGUES, pct, signalOf } from "../format";
import type { RankRow } from "../types";
import { Portrait } from "./Portrait";
import { RangeGauge } from "./RangeGauge";
import { SignalBadge } from "./Signal";
import { StarButton } from "./StarButton";

/** Valuation-forward player card: the model's estimate is the emphasised number. */
export function PlayerCard({ r, season }: { r: RankRow; season?: number }) {
  const sig = signalOf(r.market_value_eur, r.low_eur, r.high_eur);
  return (
    <Link to={`/player/${r.player_id}${season ? `?season=${season}` : ""}`} className="pcard">
      <div className="pcard-media">
        <Portrait id={r.player_id} name={r.name} pos={r.position_code} size="fill" />
        <span className="pcard-signal"><SignalBadge signal={sig} compact /></span>
        <span className="pcard-star"><StarButton id={r.player_id} name={r.name} /></span>
      </div>
      <div className="pcard-body">
        <div className="pcard-name">{r.name}</div>
        <div className="pcard-meta">{clubLabel(r)}, {r.position_code}{r.age === null ? "" : `, ${Math.floor(r.age)}`}</div>
        <div className="pcard-meta">{LEAGUES[r.league] ?? r.league}</div>
        <dl className="pcard-values">
          <div><dt>Market</dt><dd className="mono">{eur(r.market_value_eur)}</dd></div>
          <div className="is-model"><dt>Model</dt><dd className="mono">{eur(r.model_value_eur)}</dd></div>
        </dl>
        <RangeGauge market={r.market_value_eur} model={r.model_value_eur} low={r.low_eur} high={r.high_eur} width={192} />
        <div className={`pcard-diff mono ${(r.gap_pct ?? 0) >= 0 ? "pos" : "neg"}`}>
          {pct(r.gap_pct)} <span>model vs market</span>
        </div>
      </div>
    </Link>
  );
}
