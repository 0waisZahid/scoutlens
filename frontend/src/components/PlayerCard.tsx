import { Link } from "react-router-dom";
import { eur, LEAGUES, signalOf } from "../format";
import type { RankRow } from "../types";
import { Avatar } from "./Avatar";
import { RangeGauge } from "./RangeGauge";
import { SignalBadge } from "./Signal";
import { StarButton } from "./StarButton";

export function PlayerCard({ r, season }: { r: RankRow; season?: number }) {
  const sig = signalOf(r.market_value_eur, r.low_eur, r.high_eur);
  return (
    <Link to={`/player/${r.player_id}${season ? `?season=${season}` : ""}`} className={`pcard pos-${r.position_code}`}>
      <div className="pcard-top">
        <Avatar name={r.name} pos={r.position_code} />
        <StarButton id={r.player_id} name={r.name} />
      </div>
      <div className="pcard-name">{r.name}</div>
      <div className="pcard-sub">{r.sub_position ?? r.position}, {r.age === null ? "" : Math.floor(r.age)}</div>
      <div className="pcard-sub">{LEAGUES[r.league] ?? r.league}</div>
      <div className="pcard-value">{eur(r.market_value_eur)}<span>market</span></div>
      <RangeGauge market={r.market_value_eur} model={r.model_value_eur} low={r.low_eur} high={r.high_eur} width={156} />
      <div className="pcard-foot"><SignalBadge signal={sig} compact /><span className="pcard-model">model {eur(r.model_value_eur)}</span></div>
    </Link>
  );
}
