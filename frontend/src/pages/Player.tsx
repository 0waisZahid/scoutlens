import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api";
import { PercentileBars } from "../components/PercentileBars";
import { PitchArt } from "../components/PitchArt";
import { Portrait } from "../components/Portrait";
import { SignalBadge } from "../components/Signal";
import { Empty, ErrorBox, Loading, Skeleton } from "../components/State";
import { StarButton } from "../components/StarButton";
import { ValueChart } from "../components/ValueChart";
import { ValueRuler } from "../components/ValueRuler";
import { FACTOR_MEANING, Waterfall } from "../components/Waterfall";
import { clubLabel, eur, int, LEAGUES, num1, num2, pct, seasonLabel, shortDate, signalOf } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { Card, Profile, Valuation } from "../types";

function MiniList({ players, extra }: { players: (Card & { match_pct?: number })[]; extra?: (p: Card & { match_pct?: number }) => string }) {
  return (
    <ul className="minilist">
      {players.map((p) => (
        <li key={p.player_id}>
          <Portrait id={p.player_id} name={p.name} size="xs" />
          <Link to={`/player/${p.player_id}`} className="player-link">{p.name}</Link>
          <span className="sub">{clubLabel(p)}, {p.position_code}{p.age ? `, ${Math.floor(p.age)}` : ""}</span>
          <span className="minilist-val mono">{eur(p.market_value_eur)}</span>
          {extra && <span className="minilist-extra mono">{extra(p)}</span>}
        </li>
      ))}
    </ul>
  );
}

function reading(v: Valuation): { title: string; text: string } {
  if (v.market_within_range) return { title: "Inside the interval", text: "The market value sits within the model's 80% interval, so the model sees no clear mispricing." };
  return v.market_value_eur < v.low_eur
    ? { title: "Market below the interval", text: "The model expects a higher value than the market shows. A prompt to look closer, not proof." }
    : { title: "Market above the interval", text: "The market values him above what the model expects from his numbers. Often a sign of things the model can't see." };
}

function Body({ p, id, season, onSeason }: { p: Profile; id: number; season: number | null; onSeason: (s: number) => void }) {
  const val = useAsync((s) => api.valuation(id, season, s), [id, season]);
  const hist = useAsync((s) => api.modelHistory(id, s), [id]);
  const similar = useAsync((s) => api.similar(id, 6, "active", s), [id]);
  const mates = useAsync((s) => api.teammates(id, 6, s), [id]);
  const meta = useAsync(() => api.meta(), []);
  const v = val.data, t = p.trend;
  const shownSeason = v?.season ?? season ?? p.season;
  const sig = v ? signalOf(v.market_value_eur, v.low_eur, v.high_eur) : null;
  const isLatest = shownSeason === p.season;

  return (
    <>
      <header className="dossier">
        <PitchArt />
        <div className="dossier-portrait"><Portrait id={p.player_id} name={p.name} pos={p.position_code} size="lg" /></div>
        <div className="dossier-id">
          <p className="eyebrow">{LEAGUES[p.league] ?? p.league}</p>
          <h1>{p.name}</h1>
          <p className="dossier-club">{clubLabel(p)}</p>
          <dl className="meta-grid">
            <div><dt>Position</dt><dd>{p.sub_position ?? p.position}</dd></div>
            <div><dt>Age</dt><dd className="mono">{Math.floor(p.age ?? 0)}</dd></div>
            {p.country && <div><dt>Nationality</dt><dd>{p.country}</dd></div>}
            {p.height_cm && <div><dt>Height</dt><dd className="mono">{p.height_cm} cm</dd></div>}
            {p.foot && p.foot !== "unknown" && <div><dt>Foot</dt><dd>{p.foot}</dd></div>}
            <div><dt>Latest data</dt><dd className="mono">{seasonLabel(p.season)}</dd></div>
          </dl>
          {!p.is_active && <p className="fine">No data for the latest season ({seasonLabel(meta.data?.max_season ?? p.season)}), so the most recent available season is shown.</p>}
        </div>
        <div className="dossier-actions">
          <StarButton id={p.player_id} name={p.name} withLabel />
          <Link className="btn btn-secondary" to={`/compare?a=${p.player_id}`}>Compare</Link>
        </div>
      </header>

      <div className="profile-grid">
        <div className="profile-main">
          <section className="panel valuation" aria-labelledby="val-h">
            <div className="panel-head">
              <h2 id="val-h">Valuation</h2>
              <label className="inline-select">Season
                <select value={shownSeason} onChange={(e) => onSeason(Number(e.target.value))}>
                  {[...p.seasons].reverse().map((s) => <option key={s.season} value={s.season}>{seasonLabel(s.season)}</option>)}
                </select>
              </label>
            </div>
            {val.error && <ErrorBox message={val.error} />}
            {val.loading && !v && <div className="val-skel"><Skeleton h={18} w={160} /><Skeleton h={72} w={280} className="mt" /><Skeleton h={120} className="mt" /></div>}
            {v && (
              <div className={val.loading ? "is-stale" : ""}>
                <div className="val-top">
                  <div className="val-hero">
                    <span className="label">Model valuation</span>
                    <strong className="val-number mono">{eur(v.model_value_eur)}</strong>
                    <span className="help">What the model estimates from his {seasonLabel(v.season)} age, minutes, output and club.</span>
                  </div>
                  <dl className="val-side">
                    <div><dt>Market value</dt><dd className="mono">{eur(v.market_value_eur)}</dd><span>Transfermarkt{v.value_date ? `, ${shortDate(v.value_date)}` : ""}</span></div>
                    <div><dt>80% prediction interval</dt><dd className="mono">{eur(v.low_eur)} to {eur(v.high_eur)}</dd><span>Calibrated so about 80% of real values fall inside intervals like this. Not a probability for this one player.</span></div>
                    <div><dt>Model vs market</dt><dd className={`mono ${(v.gap_pct ?? 0) >= 0 ? "pos" : "neg"}`}>{(v.gap_pct ?? 0) >= 0 ? "▲" : "▼"} {pct(v.gap_pct)}</dd><span>{sig && <SignalBadge signal={sig} compact />} {reading(v).title}</span></div>
                  </dl>
                </div>
                <div className="ruler-wrap"><ValueRuler items={[{ name: p.name, v, tone: "a" }]} /></div>
                <p className="scroll-hint" aria-hidden="true">← scroll sideways for the full ruler →</p>
                <p className="reading">{reading(v).text}</p>
                {v.warnings.length > 0 && <ul className="warnings" aria-label="Cautions for this valuation">{v.warnings.map((w) => <li key={w}>{w}</li>)}</ul>}
              </div>
            )}
          </section>

          <section className="panel" aria-labelledby="hist-h">
            <div className="panel-head"><h2 id="hist-h">Valuation history</h2></div>
            <p className="help">Market value over time, with the model's estimate and 80% interval for each season. Seasons before {meta.data?.test_from_season ?? 2023} were used to train the model, so its estimates there are flattering.</p>
            <ValueChart testFrom={meta.data?.test_from_season}
              series={[{ name: p.name, tone: "a", market: p.value_history, model: hist.data,
                forecast: v && isLatest ? { low: v.forecast.low_eur, mid: v.forecast.forecast_eur, high: v.forecast.high_eur, season: v.forecast.for_season } : undefined }]} />
            <ul className="facts">
              <li><span>Last 12 months</span><strong className={`mono ${(t.value_change_12m_pct ?? 0) >= 0 ? "pos" : "neg"}`}>{pct(t.value_change_12m_pct)}</strong></li>
              <li><span>Trend, last 3 years</span><strong className="mono">{t.annual_growth_pct === null ? "–" : `${pct(t.annual_growth_pct)} a year`}</strong></li>
              <li><span>Peak</span><strong className="mono">{eur(t.peak_value_eur)}{t.peak_date ? `, ${shortDate(t.peak_date)}` : ""}</strong></li>
              <li><span>Recent form</span><strong className="mono">{num2(t.form_goals_p90)} goals, {num2(t.form_assists_p90)} assists per 90</strong></li>
            </ul>
          </section>

          <section className="panel forecast" aria-labelledby="fc-h">
            <div className="panel-head"><h2 id="fc-h">Next-season forecast</h2><span className="tag">Forecast, not a known value</span></div>
            {!v ? <Loading /> : (
              <>
                <div className="fc-grid">
                  <div><span className="label">Predicted value, {seasonLabel(v.forecast.for_season)}</span><strong className="fc-number mono">{eur(v.forecast.forecast_eur)}</strong></div>
                  <div><span className="label">Expected movement</span>
                    <strong className={`fc-number mono ${(v.forecast.expected_change_pct ?? 0) >= 0 ? "pos" : "neg"}`}>{(v.forecast.expected_change_pct ?? 0) >= 0 ? "▲" : "▼"} {pct(v.forecast.expected_change_pct)}</strong>
                    <span className="help">against the market value in {seasonLabel(v.season)}</span></div>
                  <div><span className="label">80% prediction interval</span><strong className="fc-range mono">{eur(v.forecast.low_eur)} to {eur(v.forecast.high_eur)}</strong></div>
                </div>
                {v.forecast.actual_value_eur !== null && (
                  <p className="backtest"><strong>Backtest.</strong> The real market value in {seasonLabel(v.forecast.for_season)} was <strong className="mono">{eur(v.forecast.actual_value_eur)}</strong>
                    {v.forecast.actual_value_eur >= v.forecast.low_eur && v.forecast.actual_value_eur <= v.forecast.high_eur ? ", inside the forecast interval." : ", outside the forecast interval."}
                    {v.in_sample && " This season was in the training data, so treat it as an illustration, not a test."}</p>
                )}
              </>
            )}
          </section>

          <section className="panel" aria-labelledby="why-h">
            <div className="panel-head"><h2 id="why-h">Why this estimate</h2></div>
            <p className="help">Each factor's effect on the model's estimate for {seasonLabel(shownSeason)}, largest first. Effects multiply: +100% means that factor doubled the estimate. This describes the model, not causes in the real world.</p>
            {v ? (
              <>
                <Waterfall v={v} />
                <dl className="glossary">
                  {v.factors.filter((f) => FACTOR_MEANING[f.concept]).slice(0, 5).map((f) => (
                    <div key={f.concept}><dt>{f.concept}</dt><dd>{FACTOR_MEANING[f.concept]}</dd></div>
                  ))}
                </dl>
              </>
            ) : <Loading />}
          </section>

          <section className="panel flush" aria-labelledby="seasons-h">
            <div className="panel-head pad"><h2 id="seasons-h">Season by season</h2></div>
            <div className="table-wrap">
              <table className="table plain">
                <thead>
                  <tr><th scope="col">Season</th><th scope="col" className="num">Age</th><th scope="col">League</th><th scope="col">Club</th>
                    <th scope="col" className="num">Apps</th><th scope="col" className="num">Min</th><th scope="col" className="num">G</th><th scope="col" className="num">A</th>
                    <th scope="col" className="num">G/90</th><th scope="col" className="num">A/90</th><th scope="col" className="num">Cards</th><th scope="col" className="num">Value</th></tr>
                </thead>
                <tbody>
                  {[...p.seasons].reverse().map((s) => (
                    <tr key={s.season} className={s.season === shownSeason ? "is-current" : ""}>
                      <th scope="row" className="mono">{seasonLabel(s.season)}</th><td className="num mono">{num1(s.age)}</td><td>{LEAGUES[s.league] ?? s.league}</td><td>{clubLabel(s)}</td>
                      <td className="num mono">{s.appearances}</td><td className="num mono">{int(s.minutes)}</td><td className="num mono">{s.goals}</td><td className="num mono">{s.assists}</td>
                      <td className="num mono">{num2(s.goals_per90)}</td><td className="num mono">{num2(s.assists_per90)}</td>
                      <td className="num mono">{s.yellow_cards}/{s.red_cards}</td><td className="num mono strong">{eur(s.market_value_eur)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="profile-rail">
          <section className="panel" aria-labelledby="pct-h">
            <div className="panel-head"><h2 id="pct-h">Percentiles</h2></div>
            <p className="help">Against {p.position.toLowerCase()} players in {seasonLabel(p.season)} with 450+ minutes. Higher is better.</p>
            <PercentileBars values={p.percentiles} labels={p.radar_labels} />
          </section>
          <section className="panel" aria-labelledby="sim-h">
            <div className="panel-head"><h2 id="sim-h">Similar players</h2></div>
            <p className="help">Closest current players in the same role by age, output, minutes, cards and height.</p>
            {similar.loading && <Loading />}
            {similar.error && <ErrorBox message={similar.error} />}
            {similar.data && (similar.data.players.length > 0
              ? <MiniList players={similar.data.players} extra={(x) => `${x.match_pct}% match`} />
              : <Empty>No comparison available. It needs 450+ minutes in the latest season.</Empty>)}
          </section>
          <section className="panel" aria-labelledby="mates-h">
            <div className="panel-head"><h2 id="mates-h">Teammates</h2></div>
            {mates.loading && <Loading />}
            {mates.data && (<>
              <p className="help"><span className="mono">{mates.data.total.toLocaleString("en-US")}</span> players shared a club season with {p.name}. The most valuable:</p>
              <MiniList players={mates.data.players} />
              <Link to={`/connect?a=${p.player_id}`} className="link-arrow">Explore his connections</Link>
            </>)}
          </section>
        </aside>
      </div>
    </>
  );
}

export default function Player() {
  const id = Number(useParams().id);
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const season = sp.get("season") ? Number(sp.get("season")) : null;
  const prof = useAsync((s) => api.player(id, s), [id]);
  useTitle(prof.data?.name ?? "Player");
  if (!Number.isInteger(id)) return <ErrorBox message="That isn't a valid player link." onRetry={() => nav("/")} />;
  if (prof.error) return <ErrorBox message={prof.error} />;
  if (!prof.data) return <Loading label="Loading player" />;
  return <Body p={prof.data} id={id} season={season} onSeason={(s) => { const n = new URLSearchParams(sp); n.set("season", String(s)); setSp(n, { replace: true }); }} />;
}
