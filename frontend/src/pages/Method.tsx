import { api } from "../api";
import { ErrorBox, Loading } from "../components/State";
import { int } from "../format";
import { useAsync, useTitle } from "../hooks";

const ABLATION: [string, number][] = [
  ["Age, minutes, per-90 output, position, league", 51],
  ["+ appearances, cards, height, role, foot", 51],
  ["+ strength of the club the season before", 35],
  ["+ last season's output, tenure, transfers", 33],
  ["+ nationality", 33],
];

function Bar({ label, value, max = 100, note, tone = "a", marker }: { label: string; value: number; max?: number; note?: string; tone?: "a" | "muted"; marker?: number }) {
  return (
    <div className="mbar">
      <span className="mbar-label">{label}</span>
      <span className="mbar-track" role="img" aria-label={`${label}: ${value.toFixed(0)}`}>
        <i className={`tone-${tone}`} style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
        {marker !== undefined && <u style={{ left: `${(marker / max) * 100}%` }} title={`Target ${marker}`} />}
      </span>
      <span className="mbar-val mono">{value.toFixed(0)}%</span>
      {note && <span className="mbar-note">{note}</span>}
    </div>
  );
}

export default function Method() {
  useTitle("Method");
  const info = useAsync((s) => api.modelInfo(s), []);
  const i = info.data;
  const maxImp = i ? Math.max(...i.global_importance.map((g) => g.avg_effect_pct)) : 1;

  return (
    <article className="prose-page">
      <header className="page-head">
        <p className="eyebrow">Methodology</p>
        <h1>How ScoutLens works, and where it's weak</h1>
        <p className="lede">A player's market value is an opinion. ScoutLens learns what that opinion has looked like for thousands of players, then shows how far it can be trusted instead of pretending to be exact.</p>
      </header>

      {info.loading && <Loading label="Reading the saved models" />}
      {info.error && <ErrorBox message={info.error} />}

      {i && (
        <section className="panel" aria-labelledby="meas-h">
          <div className="panel-head"><h2 id="meas-h">Measured results</h2><span className="tag tag-pos">Held-out seasons {i.trained_before_season}+</span></div>
          <p className="help">Measured on seasons the models never trained on. Read live from the saved model files.</p>
          <div className="measure-grid">
            <div className="measure">
              <h3>Valuation</h3>
              <p className="big mono">{i.valuation["median_APE_%"].toFixed(0)}%</p>
              <p className="help">typical error (median absolute percentage error): half of estimates are closer than this to the market value.</p>
              <Bar label="Within 25%" value={i.valuation["within_25%"]} />
              <Bar label="Within 50%" value={i.valuation["within_50%"]} />
            </div>
            <div className="measure">
              <h3>80% prediction interval</h3>
              <p className="big mono">{i.range.test_coverage_pct.toFixed(0)}%</p>
              <p className="help">of real market values landed inside the interval (the target is 80%). Typical interval width: top is about {i.range.test_median_width_ratio.toFixed(1)}x the bottom.</p>
              <Bar label="Coverage" value={i.range.test_coverage_pct} marker={80} />
              <p className="fine">The marker shows the 80% target. Coverage is an average over many players, not a probability for any one.</p>
            </div>
            <div className="measure">
              <h3>Next-season forecast</h3>
              <p className="big mono">{i.forecast.test_median_APE.toFixed(0)}%</p>
              <p className="help">typical error, against {i.forecast.baseline_unchanged_median_APE.toFixed(0)}% for simply assuming the value stays the same.</p>
              <Bar label="Model" value={i.forecast.test_median_APE} max={50} />
              <Bar label="Assume unchanged" value={i.forecast.baseline_unchanged_median_APE} max={50} tone="muted" />
              <p className="fine">Lower is better. The forecast interval covered {i.forecast.range_coverage_pct.toFixed(0)}% of real values.</p>
            </div>
          </div>
        </section>
      )}

      <div className="two-col">
        <section className="panel" aria-labelledby="how-h">
          <div className="panel-head"><h2 id="how-h">What it does</h2></div>
          <ol className="steps">
            <li><strong>Estimate.</strong> A gradient-boosted tree model (XGBoost) trained on player seasons before 2023 reads age, minutes, goals and assists per 90, position and role, league, the strength of the club the season before, recent history and nationality. The market trend is held flat after 2022, because extrapolating earlier growth over-predicted recent values.</li>
            <li><strong>Interval.</strong> Two quantile models give an 80% interval, widened by conformal calibration so that about 80% of players really fall inside. It is wide on purpose.</li>
            <li><strong>Forecast.</strong> A separate model predicts next season's market value from the current value, stats, history and club, with its own interval.</li>
            <li><strong>Explanation.</strong> TreeSHAP splits each estimate into factors. Effects are multipliers, and the euro column adds them one at a time, largest first, ending exactly at the estimate.</li>
          </ol>
        </section>
        <section className="panel" aria-labelledby="abl-h">
          <div className="panel-head"><h2 id="abl-h">What each kind of information added</h2></div>
          <p className="help">Typical valuation error as information was added (from the project's training report). Lower is better.</p>
          {ABLATION.map(([l, v]) => <Bar key={l} label={l} value={v} max={60} tone={v === 51 ? "muted" : "a"} />)}
          <p className="fine">Knowing the club a player is at gave the biggest gain after the basics.</p>
        </section>
      </div>

      {i && (
        <div className="two-col">
          <section className="panel" aria-labelledby="drv-h">
            <div className="panel-head"><h2 id="drv-h">What drives values overall</h2></div>
            <p className="help">Average size of each factor's effect on an estimate, across a sample of 2023+ player seasons.</p>
            <ul className="pctbars wide">
              {i.global_importance.map((g) => (
                <li key={g.concept}><span className="pctbar-name">{g.concept}</span><span className="pctbar-track"><i style={{ width: `${(g.avg_effect_pct / maxImp) * 100}%` }} /></span><span className="pctbar-num mono">{g.avg_effect_pct.toFixed(0)}%</span></li>
              ))}
            </ul>
          </section>
          <section className="panel" aria-labelledby="data-h">
            <div className="panel-head"><h2 id="data-h">Data coverage</h2></div>
            <dl className="data-grid">
              <div><dt>Players</dt><dd className="mono">{int(i.data.players)}</dd></div>
              <div><dt>Player seasons</dt><dd className="mono">{int(i.data.player_seasons)}</dd></div>
              <div><dt>Seasons</dt><dd className="mono">{i.data.first_season}–{i.data.last_season}</dd></div>
              <div><dt>Leagues</dt><dd>{Object.values(i.data.leagues).join(", ")}</dd></div>
            </dl>
            <p className="fine">Market values are Transfermarkt's, via the public Kaggle dataset. The models trained on seasons before {i.trained_before_season}.</p>
          </section>
        </div>
      )}

      <section className="panel limits" aria-labelledby="lim-h">
        <div className="panel-head"><h2 id="lim-h">Known limitations</h2><span className="tag tag-neg">Read before relying on a number</span></div>
        <ul className="cautions">
          <li><strong>Superstars.</strong> Above about €100M the model compresses values: for a €200M player it predicts around €135M, and the real value falls outside the interval. Rankings that compare model to market leave these players out.</li>
          <li><strong>Low values.</strong> Below €2M the interval covers about 64% of real values instead of 80%. Players under 900 minutes are also less reliable.</li>
          <li><strong>La Liga.</strong> Intervals are a little too narrow there (about 76% coverage).</li>
          <li><strong>Seasons before 2023</strong> were used for training, so estimates there look better than they would for a new player. The charts mark them.</li>
          <li><strong>What the model can't see.</strong> Contract length, injuries, national-team caps, and detailed stats such as expected goals, passing or tackling aren't in the data. A big gap between model and market is often explained by one of these.</li>
          <li><strong>Undervalued is not a buy signal.</strong> It means the numbers the model sees point higher than the market's opinion. Use it to decide who to watch.</li>
        </ul>
      </section>
    </article>
  );
}
