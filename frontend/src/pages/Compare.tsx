import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { Portrait } from "../components/Portrait";
import { Radar } from "../components/Radar";
import { SearchBox } from "../components/SearchBox";
import { SignalBadge } from "../components/Signal";
import { Empty, ErrorBox, Loading } from "../components/State";
import { ValueChart } from "../components/ValueChart";
import { ValueRuler } from "../components/ValueRuler";
import { clubLabel, eur, int, LEAGUES, num2, pct, seasonLabel, signalOf } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { Profile, Valuation } from "../types";

type Both = { profile: Profile; valuation: Valuation };
const TONES = ["a", "b"] as const;

function usePlayer(id: number | null) {
  return useAsync(async (signal) => {
    if (id === null) return null;
    const [profile, valuation] = await Promise.all([api.player(id, signal), api.valuation(id, null, signal)]);
    return { profile, valuation } as Both;
  }, [id]);
}

const NUM_ROWS: { label: string; get: (x: Both) => number | null; fmt: (n: number | null) => string }[] = [
  { label: "Market value", get: (x) => x.valuation.market_value_eur, fmt: (n) => eur(n) },
  { label: "Model estimate", get: (x) => x.valuation.model_value_eur, fmt: (n) => eur(n) },
  { label: "Forecast next season", get: (x) => x.valuation.forecast.forecast_eur, fmt: (n) => eur(n) },
  { label: "Minutes", get: (x) => x.profile.minutes, fmt: (n) => int(n) },
  { label: "Goals", get: (x) => x.profile.goals, fmt: (n) => int(n) },
  { label: "Assists", get: (x) => x.profile.assists, fmt: (n) => int(n) },
  { label: "Recent goals per 90", get: (x) => x.profile.trend.form_goals_p90, fmt: (n) => num2(n) },
  { label: "Recent assists per 90", get: (x) => x.profile.trend.form_assists_p90, fmt: (n) => num2(n) },
];
const TEXT_ROWS: { label: string; get: (x: Both) => string }[] = [
  { label: "Model 80% interval", get: ({ valuation: v }) => `${eur(v.low_eur)} to ${eur(v.high_eur)}` },
  { label: "Model vs market", get: ({ valuation: v }) => pct(v.gap_pct) },
  { label: "Forecast movement", get: ({ valuation: v }) => pct(v.forecast.expected_change_pct) },
  { label: "Forecast 80% interval", get: ({ valuation: v }) => `${eur(v.forecast.low_eur)} to ${eur(v.forecast.high_eur)}` },
  { label: "Last 12 months", get: ({ profile: p }) => pct(p.trend.value_change_12m_pct) },
  { label: "Peak value", get: ({ profile: p }) => eur(p.trend.peak_value_eur) },
];

export default function Compare() {
  useTitle("Compare");
  const [sp, setSp] = useSearchParams();
  const ids = [sp.get("a"), sp.get("b")].map((x) => (x && Number.isInteger(Number(x)) ? Number(x) : null));
  const states = [usePlayer(ids[0]), usePlayer(ids[1])];
  const loaded = states.map((s) => s.data ?? null);
  const have = loaded.flatMap((x, i) => (x ? [{ x, tone: TONES[i], i }] : []));
  const pick = (slot: "a" | "b") => (p: { player_id: number }) => { const n = new URLSearchParams(sp); n.set(slot, String(p.player_id)); setSp(n); };
  const drop = (slot: "a" | "b") => { const n = new URLSearchParams(sp); n.delete(slot); setSp(n); };

  return (
    <>
      <header className="page-head">
        <p className="eyebrow">Head to head</p>
        <h1>Compare players</h1>
        <p className="lede">Two players on one shared scale: values, forecasts, history and how each ranks against his position.</p>
      </header>

      <div className="compare-slots">
        {(["a", "b"] as const).map((slot, i) => {
          const x = loaded[i];
          return (
            <div className={`slot tone-${TONES[i]}`} key={slot}>
              {x ? (
                <div className="slot-id">
                  <Portrait id={x.profile.player_id} name={x.profile.name} pos={x.profile.position_code} size="md" />
                  <div>
                    <Link to={`/player/${x.profile.player_id}`} className="slot-name">{x.profile.name}</Link>
                    <p className="muted">{clubLabel(x.profile)}, {x.profile.sub_position ?? x.profile.position}, {Math.floor(x.profile.age ?? 0)}</p>
                    <p className="muted">{LEAGUES[x.profile.league] ?? x.profile.league}{x.profile.country ? `, ${x.profile.country}` : ""}</p>
                    <div className="slot-actions"><SignalBadge signal={signalOf(x.valuation.market_value_eur, x.valuation.low_eur, x.valuation.high_eur)} compact /><button className="link-btn" onClick={() => drop(slot)}>Change</button></div>
                  </div>
                </div>
              ) : (
                <>
                  <SearchBox label={`Player ${slot.toUpperCase()}`} placeholder={`Search player ${slot.toUpperCase()}`} onSelect={pick(slot)} />
                  {states[i].loading && ids[i] !== null && <Loading />}
                  {states[i].error && <ErrorBox message={states[i].error!} />}
                </>
              )}
            </div>
          );
        })}
      </div>

      {have.length === 0 && <Empty title="Choose two players">Search above to start. The same scales are used for both players so nothing is flattered.</Empty>}

      {have.length > 0 && (
        <>
          <div className="two-col">
            <section className="panel" aria-labelledby="radar-h">
              <div className="panel-head"><h2 id="radar-h">Profile</h2></div>
              <p className="help">Percentile against same-position players in the latest season (450+ minutes). Every axis runs 0 to 100.</p>
              <Radar labels={Object.values(have[0].x.profile.radar_labels)}
                polys={have.map(({ x, tone }) => ({ name: x.profile.name, tone, values: Object.keys(x.profile.radar_labels).map((k) => x.profile.percentiles[k]) }))} />
              <ul className="legend">{have.map(({ x, tone }) => <li key={x.profile.player_id}><i className={`key-line tone-${tone}`} />{x.profile.name}</li>)}</ul>
            </section>
            <section className="panel" aria-labelledby="mv-h">
              <div className="panel-head"><h2 id="mv-h">Market value history</h2></div>
              <p className="help">Both players on the same value axis, so heights compare directly.</p>
              <ValueChart showModel={false} series={have.map(({ x, tone }) => ({ name: x.profile.name, tone, market: x.profile.value_history }))} />
            </section>
          </div>

          <section className="panel" aria-labelledby="rul-h">
            <div className="panel-head"><h2 id="rul-h">Market, model and forecast</h2></div>
            <p className="help">One shared euro axis (logarithmic) for both players. Bands are 80% prediction intervals; the forecast row is a prediction, not a known value.</p>
            <div className="ruler-wrap"><ValueRuler items={have.map(({ x, tone }) => ({ name: x.profile.name, v: x.valuation, tone }))} /></div>
            <p className="scroll-hint" aria-hidden="true">← scroll sideways for the full ruler →</p>
          </section>

          <section className="panel flush" aria-labelledby="tbl-h">
            <div className="panel-head pad"><h2 id="tbl-h">Side by side</h2></div>
            <div className="table-wrap">
              <table className="table compare-table">
                <thead><tr><th scope="col"><span className="sr-only">Measure</span></th>{have.map(({ x, tone }) => <th scope="col" key={x.profile.player_id} className={`tone-${tone} th-player`}>{x.profile.name}</th>)}</tr></thead>
                <tbody>
                  <tr><th scope="row">Position</th>{have.map(({ x }) => <td key={x.profile.player_id}>{x.profile.sub_position ?? x.profile.position}</td>)}</tr>
                  <tr><th scope="row">Age</th>{have.map(({ x }) => <td key={x.profile.player_id} className="mono">{Math.floor(x.profile.age ?? 0)}</td>)}</tr>
                  {NUM_ROWS.map((r) => {
                    const vals = have.map(({ x }) => r.get(x));
                    const max = Math.max(...vals.map((v) => v ?? 0), 1e-9);
                    return (
                      <tr key={r.label}><th scope="row">{r.label}</th>
                        {have.map(({ x, tone }, j) => (
                          <td key={x.profile.player_id}>
                            <span className="mono">{r.fmt(vals[j])}</span>
                            <span className="cmpbar" aria-hidden="true"><i className={`tone-${tone}`} style={{ width: `${((vals[j] ?? 0) / max) * 100}%` }} /></span>
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                  {TEXT_ROWS.map((r) => <tr key={r.label}><th scope="row">{r.label}</th>{have.map(({ x }) => <td key={x.profile.player_id} className="mono">{r.get(x)}</td>)}</tr>)}
                </tbody>
              </table>
            </div>
            <p className="fine pad">Bars in each row share one scale, starting at zero. Stats are each player's latest season ({have.map(({ x }) => `${x.profile.name}: ${seasonLabel(x.profile.season)}`).join(", ")}).</p>
          </section>
        </>
      )}
    </>
  );
}
