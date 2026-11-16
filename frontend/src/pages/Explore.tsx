import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { RangeGauge } from "../components/RangeGauge";
import { Avatar } from "../components/Avatar";
import { Empty, ErrorBox, Loading } from "../components/State";
import { StarButton } from "../components/StarButton";
import { clubLabel, eur, LEAGUES, num2, pct, seasonLabel } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { RankRow } from "../types";

const GROUPS: { label: string; sorts: { id: string; label: string }[] }[] = [
  { label: "Market", sorts: [{ id: "value", label: "Most valuable" }, { id: "young", label: "Under 21" }] },
  {
    label: "Model",
    sorts: [
      { id: "undervalued", label: "Undervalued" }, { id: "overvalued", label: "Overvalued" },
      { id: "risers", label: "Projected risers" }, { id: "fallers", label: "Projected fallers" },
    ],
  },
  {
    label: "Stats",
    sorts: [
      { id: "goals", label: "Goals" }, { id: "assists", label: "Assists" }, { id: "goals_p90", label: "Goals per 90" },
      { id: "assists_p90", label: "Assists per 90" }, { id: "minutes", label: "Minutes" },
    ],
  },
];

const BLURB: Record<string, string> = {
  value: "The highest market values in the selected season.",
  young: "Players under 21, ranked by market value.",
  undervalued: "Where the model's estimate is furthest above the market value.",
  overvalued: "Where the model's estimate is furthest below the market value.",
  risers: "Players the forecast expects to gain the most value next season.",
  fallers: "Players the forecast expects to lose the most value next season.",
  goals: "Most goals in the selected season.",
  assists: "Most assists in the selected season.",
  goals_p90: "Goals per 90 minutes, for players with enough minutes to be meaningful.",
  assists_p90: "Assists per 90 minutes, for players with enough minutes to be meaningful.",
  minutes: "Most minutes played in the selected season.",
};

function focus(sort: string, r: RankRow): { head: string; text: string; tone?: "up" | "down" } {
  const tone = (v: number | null) => (v === null ? undefined : v >= 0 ? "up" : "down") as "up" | "down" | undefined;
  switch (sort) {
    case "undervalued": case "overvalued": return { head: "Model vs market", text: pct(r.gap_pct), tone: tone(r.gap_pct) };
    case "risers": case "fallers": return { head: "Next season", text: pct(r.forecast_change_pct), tone: tone(r.forecast_change_pct) };
    case "goals": return { head: "Goals", text: String(r.goals) };
    case "assists": return { head: "Assists", text: String(r.assists) };
    case "goals_p90": return { head: "Goals / 90", text: num2(r.goals_per90) };
    case "assists_p90": return { head: "Assists / 90", text: num2(r.assists_per90) };
    case "minutes": return { head: "Minutes", text: r.minutes.toLocaleString("en-US") };
    default: return { head: "Next season", text: pct(r.forecast_change_pct), tone: tone(r.forecast_change_pct) };
  }
}

export default function Explore() {
  useTitle("Explore");
  const [sp, setSp] = useSearchParams();
  const sort = sp.get("sort") ?? "undervalued";
  const position = sp.get("position") ?? "";
  const league = sp.get("league") ?? "";
  const season = sp.get("season") ?? "";
  const maxAge = sp.get("max_age") ?? "";

  const set = (k: string, v: string) => {
    const next = new URLSearchParams(sp);
    if (v) next.set(k, v); else next.delete(k);
    setSp(next, { replace: true });
  };

  const meta = useAsync(() => api.meta(), []);
  const board = useAsync(
    (signal) => api.rankings({ sort, position, league, season, max_age: maxAge, limit: 25 }, signal),
    [sort, position, league, season, maxAge],
  );
  const seasons = meta.data ? Array.from({ length: meta.data.max_season - meta.data.first_season + 1 }, (_, i) => meta.data!.max_season - i) : [];

  const data = board.data;
  const f = (r: RankRow) => focus(sort, r);

  return (
    <>
      <header className="page-head">
        <h1>Explore players</h1>
        <p className="lede">Rank everyone by market value, by how far the model disagrees with the market, by forecast, or by output.</p>
      </header>

      <section aria-labelledby="board-h">
        <h2 id="board-h" className="sr-only">Rankings</h2>
        <div className="tabs" role="group" aria-label="Ranking">
          {GROUPS.map((g) => (
            <div className="tabgroup" key={g.label}>
              <span className="tabgroup-label">{g.label}</span>
              {g.sorts.map((s) => (
                <button key={s.id} className={`chip${sort === s.id ? " is-on" : ""}`} aria-pressed={sort === s.id}
                  onClick={() => set("sort", s.id)}>{s.label}</button>
              ))}
            </div>
          ))}
        </div>

        <div className="filters">
          <label>Position
            <select value={position} onChange={(e) => set("position", e.target.value)}>
              <option value="">All</option>
              <option value="FW">Attack</option><option value="MF">Midfield</option>
              <option value="DF">Defender</option><option value="GK">Goalkeeper</option>
            </select>
          </label>
          <label>League
            <select value={league} onChange={(e) => set("league", e.target.value)}>
              <option value="">All five</option>
              {Object.entries(LEAGUES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </label>
          <label>Season
            <select value={season} onChange={(e) => set("season", e.target.value)}>
              <option value="">{meta.data ? `${seasonLabel(meta.data.max_season)} (latest)` : "Latest"}</option>
              {seasons.slice(1).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
            </select>
          </label>
          <label>Age up to
            <input type="number" min={16} max={45} inputMode="numeric" placeholder="Any" value={maxAge}
              onChange={(e) => set("max_age", e.target.value)} />
          </label>
        </div>

        <p className="board-note">
          {BLURB[sort]}
          {data && (data.min_value_eur || data.max_value_eur || data.min_minutes > 0) && (
            <> Showing{data.min_value_eur || data.max_value_eur
              ? <> players valued {data.min_value_eur ? `from ${eur(data.min_value_eur)}` : ""}{data.max_value_eur ? ` up to ${eur(data.max_value_eur)}` : ""}</>
              : <> players</>}
              {data.min_minutes > 0 && <> with {data.min_minutes}+ minutes</>}
              {["undervalued", "overvalued"].includes(sort) && ", the range where the model is most reliable"}
              . {data.total_matching.toLocaleString("en-US")} match.</>
          )}
        </p>

        {board.error && <ErrorBox message={board.error} />}
        {board.loading && !data && <Loading label="Loading players (the first request warms up the models)" />}
        {data && data.rows.length === 0 && <Empty>No players match these filters. Loosen the age or league filter.</Empty>}

        {data && data.rows.length > 0 && (
          <div className={`table-wrap card-flush${board.loading ? " is-stale" : ""}`}>
            <table className="board">
              <caption className="sr-only">{data.label}, season {seasonLabel(data.season)}</caption>
              <thead>
                <tr>
                  <th scope="col" className="c-rank">#</th>
                  <th scope="col">Player</th>
                  <th scope="col" className="c-age num">Age</th>
                  <th scope="col" className="num">Market</th>
                  <th scope="col" className="c-gauge">
                    Model range
                    <span className="th-hint">dot: market · line: model · band: 80% range</span>
                  </th>
                  <th scope="col" className="num">Model</th>
                  <th scope="col" className="num c-focus">{data.rows[0] ? f(data.rows[0]).head : ""}</th>
                  <th scope="col" className="num c-ga">G / A</th>
                  <th scope="col"><span className="sr-only">Watchlist</span></th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.player_id}>
                    <td className="c-rank muted">{r.rank}</td>
                    <td>
                      <div className="pcell">
                        <Avatar name={r.name} pos={r.position_code} size="sm" />
                        <div>
                          <Link to={`/player/${r.player_id}?season=${data.season}`} className="player-link">{r.name}</Link>
                          <div className="sub">{r.sub_position ?? r.position}, {LEAGUES[r.league] ?? r.league}, {clubLabel(r)}</div>
                        </div>
                      </div>
                    </td>
                    <td className="c-age num">{r.age === null ? "–" : Math.floor(r.age)}</td>
                    <td className="num strong">{eur(r.market_value_eur)}</td>
                    <td className="c-gauge"><RangeGauge market={r.market_value_eur} model={r.model_value_eur} low={r.low_eur} high={r.high_eur} /></td>
                    <td className="num">{eur(r.model_value_eur)}</td>
                    <td className={`num c-focus strong ${f(r).tone ?? ""}`}>{f(r).text}</td>
                    <td className="num c-ga">{r.goals} / {r.assists}</td>
                    <td><StarButton id={r.player_id} name={r.name} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="fine">
          “Undervalued” means the model expects a higher value than the market currently shows. It is a prompt
          to look closer, not a verdict: the model sees stats, age and club, not injuries, contracts or fit.
        </p>
      </section>
    </>
  );
}
