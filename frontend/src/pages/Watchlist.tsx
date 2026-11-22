import { Link } from "react-router-dom";
import { api } from "../api";
import { Portrait } from "../components/Portrait";
import { RangeGauge } from "../components/RangeGauge";
import { SignalBadge } from "../components/Signal";
import { Empty, ErrorBox, Loading } from "../components/State";
import { clubLabel, eur, LEAGUES, pct, seasonLabel, signalOf } from "../format";
import { useAsync, useTitle, useWatchlist } from "../hooks";
import { csvCell } from "../csv";
import type { Profile, Valuation } from "../types";

type Row = { profile: Profile; v: Valuation };

function download(rows: Row[]) {
  const head = ["name", "position", "age", "league", "club", "season", "market_value_eur", "model_value_eur", "range_low_eur", "range_high_eur", "model_vs_market_pct", "change_12m_pct", "forecast_eur", "forecast_change_pct"];
  const lines = rows.map(({ profile: p, v }) => [p.name, p.sub_position ?? p.position, p.age, LEAGUES[p.league] ?? p.league, clubLabel(p), v.season, v.market_value_eur, v.model_value_eur, v.low_eur, v.high_eur, v.gap_pct, p.trend.value_change_12m_pct, v.forecast.forecast_eur, v.forecast.expected_change_pct].map(csvCell).join(","));
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([[head.join(","), ...lines].join("\n")], { type: "text/csv" }));
  a.download = "scoutlens-watchlist.csv"; a.click(); URL.revokeObjectURL(a.href);
}

export default function Watchlist() {
  useTitle("Watchlist");
  const { list, remove } = useWatchlist();
  const key = list.map((s) => s.id).join(",");
  const data = useAsync(async (signal) => Promise.all(list.map(async (s) => {
    const [profile, v] = await Promise.all([api.player(s.id, signal), api.valuation(s.id, null, signal)]);
    return { profile, v } as Row;
  })), [key]);
  const rows = (data.data ?? []).filter((r) => list.some((s) => s.id === r.profile.player_id));
  const total = rows.reduce((a, r) => a + r.v.market_value_eur, 0);
  const under = rows.filter((r) => signalOf(r.v.market_value_eur, r.v.low_eur, r.v.high_eur) === "below").length;

  return (
    <>
      <header className="page-head">
        <p className="eyebrow">Scouting workspace</p>
        <h1>Watchlist</h1>
        <p className="lede">Players you've starred, with their valuation, trend and forecast side by side. Saved in this browser only.</p>
      </header>

      {list.length === 0 && <Empty title="Nothing saved yet">Star players on <Link to="/explore">Explore</Link> or on a player page to keep them here.</Empty>}
      {list.length > 0 && data.loading && !data.data && <Loading />}
      {data.error && <ErrorBox message={data.error} />}

      {rows.length > 0 && (
        <>
          <dl className="summary-strip">
            <div><dt>Players</dt><dd className="mono">{rows.length}</dd></div>
            <div><dt>Combined market value</dt><dd className="mono">{eur(total)}</dd></div>
            <div><dt>Below model interval</dt><dd className="mono pos">{under}</dd></div>
            <div className="summary-action"><button className="btn btn-secondary" onClick={() => download(rows)}>Download CSV</button></div>
          </dl>
          <div className="table-wrap panel">
            <table className="table board">
              <thead>
                <tr><th scope="col">Player</th><th scope="col" className="num c-age">Age</th><th scope="col" className="num">Market</th><th scope="col" className="c-gauge">Model interval</th>
                  <th scope="col" className="num">Model</th><th scope="col" className="num">12 months</th><th scope="col" className="num">Forecast</th><th scope="col"><span className="sr-only">Remove</span></th></tr>
              </thead>
              <tbody>
                {rows.map(({ profile: p, v }) => (
                  <tr key={p.player_id}>
                    <td><div className="pcell"><Portrait id={p.player_id} name={p.name} size="xs" /><div><Link to={`/player/${p.player_id}`} className="player-link">{p.name}</Link><div className="sub">{clubLabel(p)}, {p.sub_position ?? p.position}, {seasonLabel(v.season)}</div></div></div></td>
                    <td className="num c-age mono">{p.age === null ? "–" : Math.floor(p.age)}</td>
                    <td className="num mono strong">{eur(v.market_value_eur)}</td>
                    <td className="c-gauge"><RangeGauge market={v.market_value_eur} model={v.model_value_eur} low={v.low_eur} high={v.high_eur} /><SignalBadge signal={signalOf(v.market_value_eur, v.low_eur, v.high_eur)} compact /></td>
                    <td className="num mono is-model">{eur(v.model_value_eur)}</td>
                    <td className={`num mono ${(p.trend.value_change_12m_pct ?? 0) >= 0 ? "pos" : "neg"}`}>{p.trend.value_change_12m_pct === null ? "–" : `${p.trend.value_change_12m_pct >= 0 ? "▲" : "▼"} ${pct(p.trend.value_change_12m_pct)}`}</td>
                    <td className={`num mono ${(v.forecast.expected_change_pct ?? 0) >= 0 ? "pos" : "neg"}`}>{eur(v.forecast.forecast_eur)}<div className="sub mono">{pct(v.forecast.expected_change_pct)}</div></td>
                    <td><button className="link-btn" onClick={() => remove(p.player_id)} aria-label={`Remove ${p.name}`}>Remove</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
