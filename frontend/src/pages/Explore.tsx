import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { LeagueTabs } from "../components/LeagueTabs";
import { PlayerCard } from "../components/PlayerCard";
import { Portrait } from "../components/Portrait";
import { RangeGauge } from "../components/RangeGauge";
import { Empty, ErrorBox, Skeleton } from "../components/State";
import { StarButton } from "../components/StarButton";
import { clubLabel, eur, LEAGUES, num2, pct, seasonLabel } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { RankRow } from "../types";

const GROUPS: { label: string; sorts: [string, string][] }[] = [
  { label: "Model", sorts: [["undervalued", "Undervalued"], ["overvalued", "Overvalued"], ["risers", "Projected risers"], ["fallers", "Projected fallers"]] },
  { label: "Market", sorts: [["value", "Most valuable"], ["young", "Under 21"]] },
  { label: "Output", sorts: [["goals", "Goals"], ["assists", "Assists"], ["goals_p90", "Goals / 90"], ["assists_p90", "Assists / 90"], ["minutes", "Minutes"]] },
];
const LABEL = Object.fromEntries(GROUPS.flatMap((g) => g.sorts));
const BLURB: Record<string, string> = {
  value: "Highest market values in the selected season.", young: "Players under 21, ranked by market value.",
  undervalued: "The model's estimate is furthest above the market value.", overvalued: "The model's estimate is furthest below the market value.",
  risers: "Largest forecast gains next season.", fallers: "Largest forecast drops next season.",
  goals: "Most goals in the season.", assists: "Most assists in the season.", goals_p90: "Goals per 90 minutes, 900+ minutes.",
  assists_p90: "Assists per 90 minutes, 900+ minutes.", minutes: "Most minutes played.",
};

function focus(sort: string, r: RankRow): { head: string; text: string; cls?: string } {
  const c = (v: number | null) => (v === null ? "" : v >= 0 ? "pos" : "neg");
  const arrow = (v: number | null) => (v === null ? "" : v >= 0 ? "▲ " : "▼ ");
  switch (sort) {
    case "undervalued": case "overvalued": return { head: "Model vs market", text: arrow(r.gap_pct) + pct(r.gap_pct), cls: c(r.gap_pct) };
    case "goals": return { head: "Goals", text: String(r.goals) };
    case "assists": return { head: "Assists", text: String(r.assists) };
    case "goals_p90": return { head: "Goals / 90", text: num2(r.goals_per90) };
    case "assists_p90": return { head: "Assists / 90", text: num2(r.assists_per90) };
    case "minutes": return { head: "Minutes", text: r.minutes.toLocaleString("en-US") };
    default: return { head: "Forecast", text: arrow(r.forecast_change_pct) + pct(r.forecast_change_pct), cls: c(r.forecast_change_pct) };
  }
}

export default function Explore() {
  useTitle("Explore");
  const [sp, setSp] = useSearchParams();
  const sort = sp.get("sort") ?? "undervalued", position = sp.get("position") ?? "", league = sp.get("league") ?? "";
  const season = sp.get("season") ?? "", maxAge = sp.get("max_age") ?? "", minM = sp.get("min_m") ?? "", maxM = sp.get("max_m") ?? "";
  const view = sp.get("view") === "cards" ? "cards" : "table";
  const set = (k: string, v: string) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); setSp(n, { replace: true }); };

  const meta = useAsync(() => api.meta(), []);
  const board = useAsync((s) => api.rankings({
    sort, position, league, season, max_age: maxAge, limit: 30,
    min_value: minM ? Number(minM) * 1e6 : undefined, max_value: maxM ? Number(maxM) * 1e6 : undefined,
  }, s), [sort, position, league, season, maxAge, minM, maxM]);
  const seasons = meta.data ? Array.from({ length: meta.data.max_season - meta.data.first_season + 1 }, (_, i) => meta.data!.max_season - i) : [];
  const d = board.data;

  const active: [string, string, string][] = [];
  if (position) active.push(["position", "Position", { FW: "Attack", MF: "Midfield", DF: "Defender", GK: "Goalkeeper" }[position] ?? position]);
  if (season) active.push(["season", "Season", seasonLabel(Number(season))]);
  if (maxAge) active.push(["max_age", "Age up to", maxAge]);
  if (minM) active.push(["min_m", "Value from", `€${minM}M`]);
  if (maxM) active.push(["max_m", "Value to", `€${maxM}M`]);

  return (
    <>
      <header className="page-head">
        <p className="eyebrow">Market intelligence</p>
        <h1>Explore players</h1>
        <p className="lede">Rank everyone by market value, by how far the model disagrees with the market, by forecast, or by output.</p>
      </header>

      <div className="workspace">
        <div className="modes" role="group" aria-label="Rank by">
          {GROUPS.map((g) => (
            <div className="mode-group" key={g.label}>
              <span className="overline">{g.label}</span>
              <div className="seg">
                {g.sorts.map(([id, label]) => <button key={id} className={sort === id ? "is-on" : ""} aria-pressed={sort === id} onClick={() => set("sort", id)}>{label}</button>)}
              </div>
            </div>
          ))}
        </div>

        <div className="filters">
          <LeagueTabs value={league} onChange={(v) => set("league", v)} />
          <div className="filter-fields">
            <label>Position
              <select value={position} onChange={(e) => set("position", e.target.value)}>
                <option value="">All</option><option value="FW">Attack</option><option value="MF">Midfield</option><option value="DF">Defender</option><option value="GK">Goalkeeper</option>
              </select>
            </label>
            <label>Season
              <select value={season} onChange={(e) => set("season", e.target.value)}>
                <option value="">{meta.data ? `${seasonLabel(meta.data.max_season)} (latest)` : "Latest"}</option>
                {seasons.slice(1).map((s) => <option key={s} value={s}>{seasonLabel(s)}</option>)}
              </select>
            </label>
            <label>Age up to<input type="number" min={16} max={45} inputMode="numeric" placeholder="Any" value={maxAge} onChange={(e) => set("max_age", e.target.value)} /></label>
            <label>Value from (€M)<input type="number" min={0} inputMode="decimal" placeholder="Auto" value={minM} onChange={(e) => set("min_m", e.target.value)} /></label>
            <label>Value to (€M)<input type="number" min={0} inputMode="decimal" placeholder="Auto" value={maxM} onChange={(e) => set("max_m", e.target.value)} /></label>
          </div>
        </div>

        <div className="results-bar">
          <p className="muted" aria-live="polite">
            <strong>{LABEL[sort]}.</strong> {BLURB[sort]}{" "}
            {d && <>
              {(d.min_value_eur || d.max_value_eur) ? <>Values {d.min_value_eur ? `from ${eur(d.min_value_eur)}` : ""}{d.max_value_eur ? ` up to ${eur(d.max_value_eur)}` : ""}</> : null}
              {d.min_minutes > 0 ? <>, {d.min_minutes}+ minutes</> : null}
              {["undervalued", "overvalued"].includes(sort) && !minM && !maxM ? ", the range where the model is most reliable" : ""}.{" "}
              <span className="mono">{d.total_matching.toLocaleString("en-US")}</span> match.
            </>}
          </p>
          <div className="seg seg-sm" role="group" aria-label="Layout">
            <button className={view === "table" ? "is-on" : ""} aria-pressed={view === "table"} onClick={() => set("view", "")}>Table</button>
            <button className={view === "cards" ? "is-on" : ""} aria-pressed={view === "cards"} onClick={() => set("view", "cards")}>Cards</button>
          </div>
        </div>
        {active.length > 0 && (
          <div className="active-filters">
            {active.map(([k, l, v]) => <button key={k} className="filter-chip" onClick={() => set(k, "")} aria-label={`Remove filter ${l} ${v}`}>{l}: {v} <span aria-hidden="true">×</span></button>)}
            <button className="link-btn" onClick={() => setSp(new URLSearchParams({ sort }), { replace: true })}>Clear all</button>
          </div>
        )}
      </div>

      {board.error && <ErrorBox message={board.error} />}
      {board.loading && !d && <div className="table-wrap panel">{Array.from({ length: 8 }, (_, i) => <Skeleton key={i} h={44} className="srow" />)}</div>}
      {d && d.rows.length === 0 && <Empty title="No players match these filters">Loosen the age, value or league filter, or clear them all.</Empty>}

      {d && d.rows.length > 0 && view === "table" && (
        <div className={`table-wrap panel${board.loading ? " is-stale" : ""}`}>
          <table className="table board">
            <caption className="sr-only">{d.label}, season {seasonLabel(d.season)}</caption>
            <thead>
              <tr>
                <th scope="col" className="c-rank">#</th><th scope="col">Player</th><th scope="col" className="num c-age">Age</th>
                <th scope="col" className="num">Market</th><th scope="col" className="c-gauge">Model interval<span className="th-hint">dot market · line model · band 80%</span></th>
                <th scope="col" className="num">Model</th><th scope="col" className="num">{focus(sort, d.rows[0]).head}</th>
                <th scope="col" className="num c-ga">G / A</th><th scope="col"><span className="sr-only">Watchlist</span></th>
              </tr>
            </thead>
            <tbody>
              {d.rows.map((r) => (
                <tr key={r.player_id}>
                  <td className="c-rank mono muted">{r.rank}</td>
                  <td>
                    <div className="pcell">
                      <Portrait id={r.player_id} name={r.name} size="xs" />
                      <div>
                        <Link to={`/player/${r.player_id}?season=${d.season}`} className="player-link">{r.name}</Link>
                        <div className="sub">{r.sub_position ?? r.position}, {clubLabel(r)}, {LEAGUES[r.league] ?? r.league}</div>
                      </div>
                    </div>
                  </td>
                  <td className="c-age num mono">{r.age === null ? "–" : Math.floor(r.age)}</td>
                  <td className="num mono strong">{eur(r.market_value_eur)}</td>
                  <td className="c-gauge"><RangeGauge market={r.market_value_eur} model={r.model_value_eur} low={r.low_eur} high={r.high_eur} /></td>
                  <td className="num mono is-model">{eur(r.model_value_eur)}</td>
                  <td className={`num mono strong ${focus(sort, r).cls ?? ""}`}>{focus(sort, r).text}</td>
                  <td className="num c-ga mono">{r.goals} / {r.assists}</td>
                  <td><StarButton id={r.player_id} name={r.name} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {d && d.rows.length > 0 && view === "cards" && (
        <div className={`cards-grid${board.loading ? " is-stale" : ""}`}>
          {d.rows.map((r) => <PlayerCard key={r.player_id} r={r} season={d.season} />)}
        </div>
      )}
      <p className="fine">Undervalued and overvalued are prompts to look closer, not verdicts: the model sees age, minutes, output and club, not injuries, contracts or fit.</p>
    </>
  );
}
