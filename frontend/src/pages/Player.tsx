import { Link, useParams, useSearchParams } from "react-router-dom";
import { Avatar } from "../components/Avatar";
import { SignalBadge } from "../components/Signal";
import { api } from "../api";
import { PercentileBars } from "../components/PercentileBars";
import { Empty, ErrorBox, Loading } from "../components/State";
import { StarButton } from "../components/StarButton";
import { ValueChart } from "../components/ValueChart";
import { ValueRuler } from "../components/ValueRuler";
import { Waterfall } from "../components/Waterfall";
import { clubLabel, eur, int, LEAGUES, num1, num2, pct, seasonLabel, shortDate, signalOf } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { Card, Profile, Valuation } from "../types";

function MiniList({ players, extra }: { players: (Card & { match_pct?: number })[]; extra?: (p: Card & { match_pct?: number }) => string }) {
  return (
    <ul className="minilist">
      {players.map((p) => (
        <li key={p.player_id}>
          <Avatar name={p.name} pos={p.position_code} size="sm" />
          <Link to={`/player/${p.player_id}`} className="player-link">{p.name}</Link>
          <span className="sub">{p.sub_position ?? p.position}, {LEAGUES[p.league] ?? p.league}{p.age ? `, ${Math.floor(p.age)}` : ""}</span>
          <span className="minilist-val">{eur(p.market_value_eur)}</span>
          {extra && <span className="minilist-extra">{extra(p)}</span>}
        </li>
      ))}
    </ul>
  );
}

function gapReading(v: Valuation): { title: string; text: string; tone: "up" | "down" | "flat" } {
  if (v.market_within_range) {
    return { title: "Inside the range", text: "The market value sits within the model's 80% range, so the model sees no clear mispricing.", tone: "flat" };
  }
  return v.market_value_eur < v.low_eur
    ? { title: "Market is below the range", text: "The model expects a higher value than the market shows. Worth a closer look, not proof.", tone: "up" }
    : { title: "Market is above the range", text: "The market values him above what the model expects from his numbers. Often a sign of things the model can't see.", tone: "down" };
}

function Stat({ label, value, sub, tone }: { label: string; value: string; sub: string; tone?: string }) {
  return (
    <div className="kpi">
      <dt>{label}</dt>
      <dd className={tone}>{value}</dd>
      <p>{sub}</p>
    </div>
  );
}

const TABS = [["valuation", "Valuation"], ["why", "Why this value"], ["seasons", "Seasons"], ["network", "Similar and teammates"]] as const;

function Body({ p, id, season, onSeason }: { p: Profile; id: number; season: number | null; onSeason: (s: number) => void }) {
  const [sp, setSp] = useSearchParams();
  const tab = (TABS.find(([k]) => k === sp.get("tab"))?.[0] ?? "valuation") as (typeof TABS)[number][0];
  const setTab = (k: string) => { const n = new URLSearchParams(sp); n.set("tab", k); setSp(n, { replace: true }); };

  const val = useAsync((s) => api.valuation(id, season, s), [id, season]);
  const similar = useAsync((s) => api.similar(id, 6, "active", s), [id]);
  const mates = useAsync((s) => api.teammates(id, 8, s), [id]);
  const v = val.data;
  const t = p.trend;
  const shownSeason = v?.season ?? season ?? p.season;
  const sig = v ? signalOf(v.market_value_eur, v.low_eur, v.high_eur) : null;

  return (
    <>
      <header className={`hero pos-${p.position_code}`}>
        <Avatar name={p.name} pos={p.position_code} size="xl" />
        <div className="hero-text">
          <h1>{p.name}</h1>
          <ul className="pills" aria-label="Player details">
            <li>{p.sub_position ?? p.position}</li>
            <li>{LEAGUES[p.league] ?? p.league}</li>
            <li>{Math.floor(p.age ?? 0)} years</li>
            {p.country && <li>{p.country}</li>}
            {p.height_cm && <li>{p.height_cm} cm</li>}
            {p.foot && p.foot !== "unknown" && <li>{p.foot} foot</li>}
          </ul>
          <p>{clubLabel(p)}, last seen {seasonLabel(p.season)}{!p.is_active && " (no data for the latest season)"}</p>
        </div>
        <div className="hero-actions">
          <StarButton id={p.player_id} name={p.name} withLabel />
          <Link className="btn btn-ghost" to={`/compare?a=${p.player_id}`}>Compare</Link>
        </div>
      </header>

      <div className="kpi-wrap">
        {val.error && <ErrorBox message={val.error} />}
        {val.loading && !v && <div className="kpis">{[0, 1, 2, 3].map((i) => <div className="kpi skeleton" key={i} />)}</div>}
        {v && (
          <dl className={`kpis${val.loading ? " is-stale" : ""}`}>
            <Stat label="Market value" value={eur(v.market_value_eur)} sub={v.value_date ? `as of ${shortDate(v.value_date)}` : "Transfermarkt"} />
            <Stat label="Model estimate" value={eur(v.model_value_eur)} sub={`80% range ${eur(v.low_eur)} to ${eur(v.high_eur)}`} />
            <div className="kpi kpi-signal">
              <dt>Value signal</dt>
              <dd>{sig && <SignalBadge signal={sig} gap={v.gap_pct} />}</dd>
              <p>{gapReading(v).title}</p>
            </div>
            <Stat label={`Forecast ${seasonLabel(v.forecast.for_season)}`} value={eur(v.forecast.forecast_eur)}
              sub={`${pct(v.forecast.expected_change_pct)}, range ${eur(v.forecast.low_eur)} to ${eur(v.forecast.high_eur)}`}
              tone={(v.forecast.expected_change_pct ?? 0) >= 0 ? "up" : "down"} />
          </dl>
        )}
      </div>

      <div className="tabbar" role="tablist" aria-label="Player sections">
        {TABS.map(([k, label]) => (
          <button key={k} role="tab" id={`tab-${k}`} aria-selected={tab === k} aria-controls={`panel-${k}`}
            className={tab === k ? "is-on" : ""} onClick={() => setTab(k)}>{label}</button>
        ))}
        <label className="inline-select">Season
          <select value={shownSeason} onChange={(e) => onSeason(Number(e.target.value))}>
            {[...p.seasons].reverse().map((s) => <option key={s.season} value={s.season}>{seasonLabel(s.season)}</option>)}
          </select>
        </label>
      </div>

      {tab === "valuation" && (
        <div role="tabpanel" id="panel-valuation" aria-labelledby="tab-valuation" className="panel">
          <section className="card" aria-labelledby="ruler-h">
            <h2 id="ruler-h">Market vs model</h2>
            {v ? (
              <>
                <div className="ruler-wrap"><ValueRuler v={v} /></div>
                <p className="reading">{gapReading(v).text}</p>
                {v.forecast.actual_value_eur !== null && (
                  <p className="backtest">
                    <strong>Backtest.</strong> The real market value in {seasonLabel(v.forecast.for_season)} was{" "}
                    <strong>{eur(v.forecast.actual_value_eur)}</strong>
                    {v.forecast.actual_value_eur >= v.forecast.low_eur && v.forecast.actual_value_eur <= v.forecast.high_eur
                      ? ", inside the forecast range." : ", outside the forecast range."}
                    {v.in_sample && " This season was in the training data, so treat it as an illustration, not a test."}
                  </p>
                )}
                {v.warnings.length > 0 && (
                  <ul className="warnings" aria-label="Cautions for this valuation">
                    {v.warnings.map((w) => <li key={w}>{w}</li>)}
                  </ul>
                )}
              </>
            ) : <Loading label="Valuing player" />}
          </section>

          <section className="card" aria-labelledby="hist-h">
            <h2 id="hist-h">Market value over time</h2>
            <ValueChart series={[{
              name: p.name, color: "var(--brand)", points: p.value_history,
              forecast: v && shownSeason === p.season ? { low: v.forecast.low_eur, mid: v.forecast.forecast_eur, high: v.forecast.high_eur, season: v.forecast.for_season } : undefined,
            }]} />
            <ul className="facts">
              <li><span>Last 12 months</span><strong className={t.value_change_12m_pct === null ? "" : t.value_change_12m_pct >= 0 ? "up" : "down"}>{pct(t.value_change_12m_pct)}</strong></li>
              <li><span>Trend, last 3 years</span><strong>{t.annual_growth_pct === null ? "–" : `${pct(t.annual_growth_pct)} a year`}</strong></li>
              <li><span>Peak</span><strong>{eur(t.peak_value_eur)}{t.peak_date ? `, ${shortDate(t.peak_date)}` : ""}</strong></li>
              <li><span>Recent form</span><strong>{num2(t.form_goals_p90)} goals, {num2(t.form_assists_p90)} assists per 90</strong></li>
            </ul>
          </section>
        </div>
      )}

      {tab === "why" && (
        <div role="tabpanel" id="panel-why" aria-labelledby="tab-why" className="panel two">
          <section className="card" aria-labelledby="why-h">
            <h2 id="why-h">Why this estimate</h2>
            <p className="muted small">Each factor's effect on the model's estimate for {seasonLabel(shownSeason)}, largest first.</p>
            {v ? <Waterfall v={v} /> : <Loading />}
          </section>
          <section className="card" aria-labelledby="pct-h">
            <h2 id="pct-h">How he compares</h2>
            <p className="muted small">Percentile among {p.position.toLowerCase()} players in {seasonLabel(p.season)} with 450+ minutes. Higher is better.</p>
            <PercentileBars values={p.percentiles} labels={p.radar_labels} />
          </section>
        </div>
      )}

      {tab === "seasons" && (
        <div role="tabpanel" id="panel-seasons" aria-labelledby="tab-seasons" className="panel">
          <section className="card card-flush" aria-labelledby="seasons-h">
            <h2 id="seasons-h" className="card-title">Season by season</h2>
            <div className="table-wrap">
              <table className="plain">
                <thead>
                  <tr>
                    <th scope="col">Season</th><th scope="col" className="num">Age</th><th scope="col">League</th><th scope="col">Club</th>
                    <th scope="col" className="num">Apps</th><th scope="col" className="num">Min</th>
                    <th scope="col" className="num">G</th><th scope="col" className="num">A</th>
                    <th scope="col" className="num">G/90</th><th scope="col" className="num">A/90</th>
                    <th scope="col" className="num">Cards</th><th scope="col" className="num">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {[...p.seasons].reverse().map((s) => (
                    <tr key={s.season} className={s.season === shownSeason ? "is-current" : ""}>
                      <th scope="row">{seasonLabel(s.season)}</th>
                      <td className="num">{num1(s.age)}</td><td>{LEAGUES[s.league] ?? s.league}</td><td>{clubLabel(s)}</td>
                      <td className="num">{s.appearances}</td><td className="num">{int(s.minutes)}</td>
                      <td className="num">{s.goals}</td><td className="num">{s.assists}</td>
                      <td className="num">{num2(s.goals_per90)}</td><td className="num">{num2(s.assists_per90)}</td>
                      <td className="num">{s.yellow_cards}/{s.red_cards}</td><td className="num strong">{eur(s.market_value_eur)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      )}

      {tab === "network" && (
        <div role="tabpanel" id="panel-network" aria-labelledby="tab-network" className="panel two">
          <section className="card" aria-labelledby="sim-h">
            <h2 id="sim-h">Similar players</h2>
            <p className="muted small">Closest current players in the same role by age, output, minutes, cards and height.</p>
            {similar.loading && <Loading />}
            {similar.error && <ErrorBox message={similar.error} />}
            {similar.data && (similar.data.players.length > 0
              ? <MiniList players={similar.data.players} extra={(x) => `${x.match_pct}% match`} />
              : <Empty>No comparison available. Similar players need 450+ minutes in {seasonLabel(p.season)}.</Empty>)}
          </section>
          <section className="card" aria-labelledby="mates-h">
            <h2 id="mates-h">Teammates</h2>
            {mates.loading && <Loading />}
            {mates.data && (
              <>
                <p className="muted small">{mates.data.total.toLocaleString("en-US")} players shared a club season with {p.name}. The most valuable:</p>
                <MiniList players={mates.data.players} />
                <p className="fine"><Link to={`/connect?a=${p.player_id}`}>Find how he connects to any other player</Link></p>
              </>
            )}
          </section>
        </div>
      )}
    </>
  );
}

export default function Player() {
  const params = useParams();
  const id = Number(params.id);
  const [sp, setSp] = useSearchParams();
  const season = sp.get("season") ? Number(sp.get("season")) : null;
  const prof = useAsync((s) => api.player(id, s), [id]);
  useTitle(prof.data?.name ?? "Player");

  if (!Number.isInteger(id)) return <ErrorBox message="That isn't a valid player link." />;
  if (prof.error) return <ErrorBox message={prof.error} />;
  if (!prof.data) return <Loading label="Loading player" />;
  return (
    <Body p={prof.data} id={id} season={season}
      onSeason={(s) => { const n = new URLSearchParams(sp); n.set("season", String(s)); setSp(n, { replace: true }); }} />
  );
}
