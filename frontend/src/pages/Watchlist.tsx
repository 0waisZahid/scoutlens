import { Link } from "react-router-dom";
import { api } from "../api";
import { RangeGauge } from "../components/RangeGauge";
import { Empty, ErrorBox, Loading } from "../components/State";
import { clubLabel, eur, LEAGUES, pct, seasonLabel } from "../format";
import { useAsync, useTitle, useWatchlist } from "../hooks";
import type { Profile, Valuation } from "../types";

type Row = { profile: Profile; v: Valuation };

function csvCell(x: string | number | null): string {
  const s = x === null ? "" : String(x);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function download(rows: Row[]) {
  const head = ["name", "position", "age", "league", "club", "season", "market_value_eur", "model_value_eur",
    "range_low_eur", "range_high_eur", "model_vs_market_pct", "forecast_eur", "forecast_change_pct"];
  const lines = rows.map(({ profile: p, v }) => [
    p.name, p.sub_position ?? p.position, p.age, LEAGUES[p.league] ?? p.league, clubLabel(p), v.season,
    v.market_value_eur, v.model_value_eur, v.low_eur, v.high_eur, v.gap_pct, v.forecast.forecast_eur,
    v.forecast.expected_change_pct,
  ].map(csvCell).join(","));
  const blob = new Blob([[head.join(","), ...lines].join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "scoutlens-watchlist.csv";
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function Watchlist() {
  useTitle("Watchlist");
  const { list, remove } = useWatchlist();
  const key = list.map((s) => s.id).join(",");
  const data = useAsync(async (signal) => {
    const rows = await Promise.all(list.map(async (s) => {
      const [profile, v] = await Promise.all([api.player(s.id, signal), api.valuation(s.id, null, signal)]);
      return { profile, v } as Row;
    }));
    return rows;
  }, [key]);

  return (
    <>
      <h1>Watchlist</h1>
      <p className="lede">Players you've starred. Saved in this browser only.</p>

      {list.length === 0 && (
        <Empty>
          Nothing saved yet. Star players on the <Link to="/">board</Link> or on a player page to keep them here.
        </Empty>
      )}
      {list.length > 0 && data.loading && !data.data && <Loading />}
      {data.error && <ErrorBox message={data.error} />}

      {data.data && list.length > 0 && (
        <>
          <div className="toolbar">
            <span className="muted">{list.length} player{list.length === 1 ? "" : "s"}</span>
            <button className="btn" onClick={() => download(data.data!)}>Download CSV</button>
          </div>
          <div className="table-wrap">
            <table className="board">
              <thead>
                <tr>
                  <th scope="col">Player</th><th scope="col" className="num c-age">Age</th>
                  <th scope="col" className="num">Market</th><th scope="col" className="c-gauge">Model range</th>
                  <th scope="col" className="num">Model</th><th scope="col" className="num">Forecast</th>
                  <th scope="col"><span className="sr-only">Remove</span></th>
                </tr>
              </thead>
              <tbody>
                {data.data.filter((r) => list.some((s) => s.id === r.profile.player_id)).map(({ profile: p, v }) => (
                  <tr key={p.player_id}>
                    <td>
                      <Link to={`/player/${p.player_id}`} className="player-link">{p.name}</Link>
                      <div className="sub">{p.sub_position ?? p.position}, {LEAGUES[p.league] ?? p.league}, {seasonLabel(v.season)}</div>
                    </td>
                    <td className="num c-age">{p.age === null ? "–" : Math.floor(p.age)}</td>
                    <td className="num strong">{eur(v.market_value_eur)}</td>
                    <td className="c-gauge"><RangeGauge market={v.market_value_eur} model={v.model_value_eur} low={v.low_eur} high={v.high_eur} /></td>
                    <td className="num">{eur(v.model_value_eur)}</td>
                    <td className={`num ${(v.forecast.expected_change_pct ?? 0) >= 0 ? "up" : "down"}`}>
                      {eur(v.forecast.forecast_eur)} <span className="sub inline">{pct(v.forecast.expected_change_pct)}</span>
                    </td>
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
