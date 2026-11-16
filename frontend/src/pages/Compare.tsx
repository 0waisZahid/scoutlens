import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Radar } from "../components/Radar";
import { SearchBox } from "../components/SearchBox";
import { Empty, ErrorBox, Loading } from "../components/State";
import { ValueChart } from "../components/ValueChart";
import { clubLabel, eur, int, LEAGUES, num2, pct, seasonLabel } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { Profile, Valuation } from "../types";

const COLORS = ["var(--cobalt)", "var(--second)"];

function usePlayer(id: number | null) {
  return useAsync(async (signal) => {
    if (id === null) return null;
    const [profile, valuation] = await Promise.all([api.player(id, signal), api.valuation(id, null, signal)]);
    return { profile, valuation };
  }, [id]);
}

type Both = { profile: Profile; valuation: Valuation };

const ROWS: { label: string; get: (x: Both) => string }[] = [
  { label: "Position", get: ({ profile: p }) => p.sub_position ?? p.position },
  { label: "Age", get: ({ profile: p }) => (p.age === null ? "–" : String(Math.floor(p.age))) },
  { label: "League", get: ({ profile: p }) => LEAGUES[p.league] ?? p.league },
  { label: "Club", get: ({ profile: p }) => clubLabel(p) },
  { label: "Market value", get: ({ valuation: v }) => eur(v.market_value_eur) },
  { label: "Model estimate", get: ({ valuation: v }) => eur(v.model_value_eur) },
  { label: "Model 80% range", get: ({ valuation: v }) => `${eur(v.low_eur)} to ${eur(v.high_eur)}` },
  { label: "Model vs market", get: ({ valuation: v }) => pct(v.gap_pct) },
  { label: "Forecast next season", get: ({ valuation: v }) => `${eur(v.forecast.forecast_eur)} (${pct(v.forecast.expected_change_pct)})` },
  { label: "Last 12 months", get: ({ profile: p }) => pct(p.trend.value_change_12m_pct) },
  { label: "Peak value", get: ({ profile: p }) => eur(p.trend.peak_value_eur) },
  { label: "Minutes", get: ({ profile: p }) => int(p.minutes) },
  { label: "Goals", get: ({ profile: p }) => String(p.goals) },
  { label: "Assists", get: ({ profile: p }) => String(p.assists) },
  { label: "Recent goals per 90", get: ({ profile: p }) => num2(p.trend.form_goals_p90) },
  { label: "Recent assists per 90", get: ({ profile: p }) => num2(p.trend.form_assists_p90) },
];

export default function Compare() {
  useTitle("Compare");
  const [sp, setSp] = useSearchParams();
  const ids = [sp.get("a"), sp.get("b")].map((x) => (x && Number.isInteger(Number(x)) ? Number(x) : null));
  const A = usePlayer(ids[0]);
  const B = usePlayer(ids[1]);
  const pick = (slot: "a" | "b") => (p: { player_id: number }) => {
    const n = new URLSearchParams(sp);
    n.set(slot, String(p.player_id));
    setSp(n);
  };
  const drop = (slot: "a" | "b") => { const n = new URLSearchParams(sp); n.delete(slot); setSp(n); };

  const states = [A, B];
  const loaded = states.map((s) => s.data ?? null);
  const both = loaded.filter((x): x is Both => x !== null);

  return (
    <>
      <h1>Compare players</h1>
      <p className="lede">Put two players side by side: values, forecast, output and how each ranks against his position.</p>

      <div className="pickers">
        {(["a", "b"] as const).map((slot, i) => (
          <div className="picker" key={slot}>
            <span className="swatch" style={{ background: COLORS[i] }} aria-hidden="true" />
            {loaded[i] ? (
              <div className="picked">
                <Link to={`/player/${loaded[i]!.profile.player_id}`} className="player-link">{loaded[i]!.profile.name}</Link>
                <button className="link-btn" onClick={() => drop(slot)}>Change</button>
              </div>
            ) : (
              <SearchBox label={`Player ${slot.toUpperCase()}`} placeholder={`Search player ${slot.toUpperCase()}`} onSelect={pick(slot)} />
            )}
            {states[i].loading && ids[i] !== null && !loaded[i] && <Loading />}
            {states[i].error && <ErrorBox message={states[i].error!} />}
          </div>
        ))}
      </div>

      {both.length === 0 && <Empty>Choose two players to compare.</Empty>}

      {both.length > 0 && (
        <>
          <div className="two compare-top">
            <section aria-labelledby="radar-h" className="block">
              <h2 id="radar-h">Profile</h2>
              <p className="muted small">Percentile vs same-position players in the latest season (450+ minutes).</p>
              <Radar
                labels={Object.values(both[0].profile.radar_labels)}
                polys={loaded.flatMap((x, i) => x ? [{
                  name: x.profile.name, color: COLORS[i],
                  values: Object.keys(x.profile.radar_labels).map((k) => x.profile.percentiles[k]),
                }] : [])}
              />
              <ul className="legend">
                {loaded.map((x, i) => x && <li key={x.profile.player_id}><i style={{ background: COLORS[i] }} />{x.profile.name}</li>)}
              </ul>
            </section>
            <section aria-labelledby="mv-h" className="block">
              <h2 id="mv-h">Market value over time</h2>
              <ValueChart series={loaded.flatMap((x, i) => x ? [{ name: x.profile.name, color: COLORS[i], points: x.profile.value_history }] : [])} />
            </section>
          </div>

          <section aria-labelledby="tbl-h" className="block">
            <h2 id="tbl-h">Side by side</h2>
            <div className="table-wrap">
              <table className="plain compare">
                <thead>
                  <tr>
                    <th scope="col"><span className="sr-only">Measure</span></th>
                    {loaded.map((x, i) => x && <th scope="col" key={x.profile.player_id} style={{ borderBottomColor: COLORS[i] }}>{x.profile.name}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {ROWS.map((r) => (
                    <tr key={r.label}>
                      <th scope="row">{r.label}</th>
                      {loaded.map((x, i) => x && <td key={i}>{r.get(x)}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="fine">Stats are for each player's latest season in the data ({loaded.filter(Boolean).map((x) => `${x!.profile.name}: ${seasonLabel(x!.profile.season)}`).join(", ")}).</p>
          </section>
        </>
      )}
    </>
  );
}
