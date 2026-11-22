import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { LeagueTabs } from "../components/LeagueTabs";
import { MovementBar } from "../components/MovementBar";
import { PitchArt } from "../components/PitchArt";
import { PlayerCard } from "../components/PlayerCard";
import { Portrait } from "../components/Portrait";
import { RangeGauge } from "../components/RangeGauge";
import { SearchBox } from "../components/SearchBox";
import { SignalBadge } from "../components/Signal";
import { ErrorBox, Skeleton } from "../components/State";
import { clubLabel, eur, int, LEAGUES, pct, seasonLabel, signalOf } from "../format";
import { useAsync, useTitle } from "../hooks";
import type { Overview, RankRow } from "../types";

function FeaturedRead({ rows }: { rows: RankRow[] | undefined }) {
  const r = rows ? (rows.find((x) => x.outside_range === "below") ?? rows[0]) : undefined;
  return (
    <aside className="featured" aria-label="Largest gap between model and market this season">
      <PitchArt />
      {!r ? (
        <div className="featured-in"><Skeleton h={14} w={140} /><Skeleton h={64} w={64} className="mt" /><Skeleton h={22} w="70%" className="mt" /><Skeleton h={90} className="mt" /></div>
      ) : (
        <div className="featured-in">
          <p className="eyebrow">Largest gap this season</p>
          <div className="featured-id">
            <Portrait id={r.player_id} name={r.name} pos={r.position_code} size="md" />
            <div>
              <Link to={`/player/${r.player_id}`} className="featured-name">{r.name}</Link>
              <p className="muted">{clubLabel(r)}, {r.sub_position ?? r.position}, {r.age === null ? "" : Math.floor(r.age)}</p>
            </div>
          </div>
          <div className="featured-gauge">
            <RangeGauge market={r.market_value_eur} model={r.model_value_eur} low={r.low_eur} high={r.high_eur} width={360} />
            <div className="annot"><span>dot: market</span><span>line: model</span><span>band: 80% interval</span></div>
          </div>
          <dl className="featured-nums">
            <div><dt>Market value</dt><dd className="mono">{eur(r.market_value_eur)}</dd></div>
            <div className="is-model"><dt>Model estimate</dt><dd className="mono">{eur(r.model_value_eur)}</dd></div>
            <div><dt>80% interval</dt><dd className="mono">{eur(r.low_eur)} to {eur(r.high_eur)}</dd></div>
          </dl>
          <div className="featured-foot">
            <SignalBadge signal={signalOf(r.market_value_eur, r.low_eur, r.high_eur)} gap={r.gap_pct} />
            <Link to={`/player/${r.player_id}`} className="link-arrow">Open dossier</Link>
          </div>
        </div>
      )}
    </aside>
  );
}

function MarketOverview({ o, players, error }: { o?: Overview; players?: number; error?: string }) {
  if (error) return null;
  const tot = o ? o.players_assessed : 1;
  const seg = (n: number) => `${(n / tot) * 100}%`;
  return (
    <section className="overview" aria-label="Market overview">
      <div className="overview-main">
        <h2 className="overline">Market read, {o ? seasonLabel(o.season) : "latest season"}</h2>
        {o ? (
          <>
            <div className="stackbar" role="img" aria-label={`${o.below_range} players valued below the model interval, ${o.inside_range} inside, ${o.above_range} above`}>
              <i className="s-below" style={{ width: seg(o.below_range) }} />
              <i className="s-inside" style={{ width: seg(o.inside_range) }} />
              <i className="s-above" style={{ width: seg(o.above_range) }} />
            </div>
            <ul className="stack-legend">
              <li><span className="badge-mark pos">▲</span><b className="mono">{int(o.below_range)}</b> below model interval</li>
              <li><span className="badge-mark">■</span><b className="mono">{int(o.inside_range)}</b> inside</li>
              <li><span className="badge-mark neg">▼</span><b className="mono">{int(o.above_range)}</b> above</li>
            </ul>
          </>
        ) : <Skeleton h={34} />}
        <p className="fine">{o ? `${int(o.players_assessed)} players valued €2M to €100M with 900+ minutes, where the model is most reliable.` : " "}</p>
      </div>
      <dl className="overview-stats">
        <div><dt>Players tracked</dt><dd className="mono">{players ? int(players) : "–"}</dd></div>
        <div><dt>Median model vs market</dt><dd className="mono">{o ? pct(o.median_gap_pct) : "–"}</dd></div>
        <div><dt>Market value covered</dt><dd className="mono">{o?.total_market_value_eur ? `€${(o.total_market_value_eur / 1e9).toFixed(1)}B` : "–"}</dd></div>
      </dl>
    </section>
  );
}

function Section({ title, sub, more, children }: { title: string; sub: string; more?: string; children: React.ReactNode }) {
  return (
    <section className="section" aria-label={title}>
      <header className="section-head">
        <div><h2>{title}</h2><p>{sub}</p></div>
        {more && <Link to={more} className="link-arrow">See all</Link>}
      </header>
      {children}
    </section>
  );
}

function MoverList({ rows, loading, error }: { rows?: RankRow[]; loading: boolean; error?: string }) {
  if (error) return <ErrorBox message={error} />;
  if (loading && !rows) return <div className="mlist">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} h={48} className="mrow" />)}</div>;
  const max = Math.max(...(rows ?? []).map((r) => Math.abs(r.forecast_change_pct ?? 0)), 1);
  return (
    <ol className="mlist">
      {rows?.map((r) => (
        <li key={r.player_id}>
          <Link to={`/player/${r.player_id}`} className="mrow">
            <Portrait id={r.player_id} name={r.name} size="xs" />
            <span className="mrow-id"><strong>{r.name}</strong><small>{clubLabel(r)}, {r.position_code}</small></span>
            <span className="mrow-vals mono"><small>{eur(r.market_value_eur)}</small><span aria-hidden="true">→</span><strong>{eur(r.forecast_eur)}</strong></span>
            <MovementBar pct={r.forecast_change_pct} max={max} />
            <span className={`mrow-pct mono ${(r.forecast_change_pct ?? 0) >= 0 ? "pos" : "neg"}`}>{(r.forecast_change_pct ?? 0) >= 0 ? "▲" : "▼"} {pct(r.forecast_change_pct, 0)}</span>
          </Link>
        </li>
      ))}
    </ol>
  );
}

function RankList({ rows, loading }: { rows?: RankRow[]; loading: boolean }) {
  if (loading && !rows) return <div className="mlist">{Array.from({ length: 6 }, (_, i) => <Skeleton key={i} h={44} className="mrow" />)}</div>;
  return (
    <ol className="rlist">
      {rows?.map((r) => (
        <li key={r.player_id}>
          <Link to={`/player/${r.player_id}`} className="mrow">
            <span className="rank mono">{r.rank}</span>
            <Portrait id={r.player_id} name={r.name} size="xs" />
            <span className="mrow-id"><strong>{r.name}</strong><small>{clubLabel(r)}, {LEAGUES[r.league] ?? r.league}</small></span>
            <span className="mono strong">{eur(r.market_value_eur)}</span>
          </Link>
        </li>
      ))}
    </ol>
  );
}

export default function Home() {
  useTitle("");
  const nav = useNavigate();
  const [league, setLeague] = useState("");
  const meta = useAsync(() => api.meta(), []);
  const featured = useAsync((s) => api.rankings({ sort: "undervalued", limit: 12 }, s), []);
  const under = useAsync((s) => api.rankings({ sort: "undervalued", league, limit: 12 }, s), [league]);
  const risers = useAsync((s) => api.rankings({ sort: "risers", league, limit: 7 }, s), [league]);
  const fallers = useAsync((s) => api.rankings({ sort: "fallers", league, limit: 7 }, s), [league]);
  const young = useAsync((s) => api.rankings({ sort: "young", league, limit: 6 }, s), [league]);
  const top = useAsync((s) => api.rankings({ sort: "value", league, limit: 6 }, s), [league]);
  const m = meta.data;

  return (
    <>
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Football intelligence</p>
          <h1>See the value <em>others miss.</em></h1>
          <p className="hero-lede">Football intelligence powered by machine learning. Discover player valuations, identify market inefficiencies and forecast future potential.</p>
          <SearchBox label="Search a player" hideLabel placeholder="Search a player, e.g. Haaland" className="search-hero" onSelect={(p) => nav(`/player/${p.player_id}`)} />
          <dl className="hero-stats">
            <div><dt>Player seasons</dt><dd className="mono">{m ? int(m.player_seasons) : "–"}</dd></div>
            <div><dt>Seasons covered</dt><dd className="mono">{m ? `${m.first_season}–${m.max_season}` : "–"}</dd></div>
            <div><dt>Typical valuation error</dt><dd className="mono">{m?.typical_error_pct ? `${m.typical_error_pct}%` : "–"}</dd></div>
          </dl>
        </div>
        <FeaturedRead rows={featured.data?.rows} />
      </section>

      <MarketOverview o={m?.overview} players={m?.players} error={meta.error} />

      <div className="filterbar">
        <span className="overline">Filter the sections below</span>
        <LeagueTabs value={league} onChange={setLeague} />
      </div>

      <Section title="Undervalued by the model" sub="Where the model's estimate is furthest above the market value" more={`/explore?sort=undervalued${league ? `&league=${league}` : ""}`}>
        {under.error && <ErrorBox message={under.error} />}
        <div className="cards-row" tabIndex={0} aria-label="Undervalued players, scroll sideways">
          {!under.data && !under.error && Array.from({ length: 6 }, (_, i) => <div key={i} className="pcard is-skeleton"><Skeleton h={150} /><Skeleton h={14} w="70%" className="mt" /><Skeleton h={14} w="50%" className="mt" /></div>)}
          {under.data?.rows.map((r) => <PlayerCard key={r.player_id} r={r} season={under.data!.season} />)}
        </div>
      </Section>

      <div className="split">
        <Section title="Projected risers" sub="Biggest expected gains next season" more={`/explore?sort=risers${league ? `&league=${league}` : ""}`}>
          <MoverList rows={risers.data?.rows} loading={risers.loading} error={risers.error} />
        </Section>
        <Section title="Projected fallers" sub="Biggest expected drops next season" more={`/explore?sort=fallers${league ? `&league=${league}` : ""}`}>
          <MoverList rows={fallers.data?.rows} loading={fallers.loading} error={fallers.error} />
        </Section>
      </div>
      <p className="fine forecast-note">Forecasts are model predictions for the next season with their own intervals, not known values. Open a player to see the range.</p>

      <div className="split">
        <Section title="Rising talents" sub="Under 21, by market value" more="/explore?sort=young"><RankList rows={young.data?.rows} loading={young.loading} /></Section>
        <Section title="Most valuable" sub="Highest market values this season" more="/explore?sort=value"><RankList rows={top.data?.rows} loading={top.loading} /></Section>
      </div>

      <section className="tools" aria-label="Tools">
        <Link to="/compare" className="tool"><strong>Compare two players</strong><span>Values, forecasts and profiles on one shared scale</span></Link>
        <Link to="/connect" className="tool"><strong>Find the connection</strong><span>The shortest chain of teammates between any two players</span></Link>
        <Link to="/method" className="tool"><strong>How it works</strong><span>Accuracy, intervals and where the model is weak</span></Link>
      </section>
    </>
  );
}
