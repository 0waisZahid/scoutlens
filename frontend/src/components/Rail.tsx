import { Link } from "react-router-dom";
import { api } from "../api";
import { useAsync } from "../hooks";
import { PlayerCard } from "./PlayerCard";

/** A horizontally scrolling row of player cards from one ranking. */
export function Rail({ title, sub, sort, league, more }: { title: string; sub: string; sort: string; league: string; more: string }) {
  const data = useAsync((s) => api.rankings({ sort, league, limit: 12 }, s), [sort, league]);
  return (
    <section className="rail" aria-label={title}>
      <div className="rail-head">
        <div><h2>{title}</h2><p>{sub}</p></div>
        <Link to={`${more}${league ? `&league=${league}` : ""}`} className="more">See all</Link>
      </div>
      {data.error && <p className="state state-error">{data.error}</p>}
      <div className="rail-track" tabIndex={0}>
        {!data.data && !data.error && Array.from({ length: 5 }, (_, i) => <div className="pcard skeleton" key={i} aria-hidden="true" />)}
        {data.data?.rows.map((r) => <PlayerCard key={r.player_id} r={r} season={data.data!.season} />)}
      </div>
    </section>
  );
}
