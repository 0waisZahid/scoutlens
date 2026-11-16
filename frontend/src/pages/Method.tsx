import { api } from "../api";
import { ErrorBox, Loading } from "../components/State";
import { useAsync, useTitle } from "../hooks";

const ABLATION: [string, string][] = [
  ["Age, minutes, goals and assists per 90, position, league", "51%"],
  ["+ appearances, cards, height, role, foot", "51%"],
  ["+ strength of the club (previous season)", "35%"],
  ["+ last season's output, club tenure, transfers", "33%"],
  ["+ nationality", "33%"],
];

export default function Method() {
  useTitle("Method");
  const info = useAsync((s) => api.modelInfo(s), []);
  const i = info.data;
  const max = i ? Math.max(...i.global_importance.map((g) => g.avg_effect_pct)) : 1;

  return (
    <article className="prose">
      <h1>How ScoutLens works, and where it's weak</h1>
      <p className="lede">
        A player's market value is an opinion. ScoutLens learns what that opinion has looked like for
        thousands of players and shows how confident it is, rather than pretending to be exact.
      </p>

      <h2>What it does</h2>
      <p>
        <strong>The estimate</strong> comes from a gradient-boosted tree model (XGBoost) trained on player seasons
        before 2023. It looks at age, minutes, goals and assists per 90, position and role, league, the strength of
        the club the previous season, recent history and nationality. It was then tested on 2023 onward, seasons it
        never saw. The market trend is held flat after 2022, because extrapolating earlier growth over-predicted
        recent values.
      </p>
      <p>
        <strong>The range</strong> is an 80% interval from two quantile models, widened by conformal calibration so
        that about 80% of players really do fall inside it. It is wide on purpose: the typical top of the range is
        about five times the bottom.
      </p>
      <p>
        <strong>The forecast</strong> predicts next season's market value from the current value, stats, history
        and club, with its own range.
      </p>
      <p>
        <strong>The explanation</strong> splits each estimate into factors using TreeSHAP. Effects are
        multipliers on value, so “+100%” means that factor doubled the estimate. The euro column adds them one at a
        time, largest first, and ends exactly at the estimate.
      </p>

      <h2>How accurate it is</h2>
      {info.loading && <Loading />}
      {info.error && <ErrorBox message={info.error} />}
      {i && (
        <>
          <p className="muted small">Measured on seasons {i.trained_before_season}+, which the models never trained on. Figures are read live from the saved models.</p>
          <div className="table-wrap">
            <table className="plain">
              <thead><tr><th scope="col">Task</th><th scope="col" className="num">Typical error</th><th scope="col">Other measures</th></tr></thead>
              <tbody>
                <tr><th scope="row">Valuation</th><td className="num">{i.valuation["median_APE_%"].toFixed(0)}%</td>
                  <td>{i.valuation["within_25%"].toFixed(0)}% within 25% of the real value, {i.valuation["within_50%"].toFixed(0)}% within 50%</td></tr>
                <tr><th scope="row">80% range</th><td className="num">n/a</td>
                  <td>{i.range.test_coverage_pct.toFixed(0)}% of real values landed inside (target 80%), typical width {i.range.test_median_width_ratio.toFixed(1)}x</td></tr>
                <tr><th scope="row">Next-season forecast</th><td className="num">{i.forecast.test_median_APE.toFixed(0)}%</td>
                  <td>vs {i.forecast.baseline_unchanged_median_APE.toFixed(0)}% if you assume the value stays the same; its range covered {i.forecast.range_coverage_pct.toFixed(0)}%</td></tr>
              </tbody>
            </table>
          </div>
          <p className="small">
            “Typical error” is the median absolute percentage error. A 31% typical error means half of all
            estimates are within 31% of the market value and half are further away.
          </p>

          <h3>What each kind of information added</h3>
          <div className="table-wrap">
            <table className="plain">
              <thead><tr><th scope="col">Information used</th><th scope="col" className="num">Typical error</th></tr></thead>
              <tbody>{ABLATION.map(([k, v]) => <tr key={k}><th scope="row">{k}</th><td className="num">{v}</td></tr>)}</tbody>
            </table>
          </div>
          <p className="small">Knowing which club a player is at is the biggest single gain after the basics. The numbers above are from the project's training report.</p>

          <h2>What drives values overall</h2>
          <p className="muted small">Average size of each factor's effect on a player's estimate, across a sample of 2023+ player seasons.</p>
          <ul className="pctbars wide">
            {i.global_importance.map((g) => (
              <li key={g.concept}>
                <span className="pctbar-name">{g.concept}</span>
                <span className="pctbar-track"><i style={{ width: `${(g.avg_effect_pct / max) * 100}%` }} /></span>
                <span className="pctbar-num">{g.avg_effect_pct.toFixed(0)}%</span>
              </li>
            ))}
          </ul>

          <h2>Data</h2>
          <p>
            {i.data.players.toLocaleString("en-US")} players and {i.data.player_seasons.toLocaleString("en-US")} player
            seasons, {i.data.first_season} to {i.data.last_season}, across the Premier League, La Liga, Serie A, Bundesliga
            and Ligue 1. Market values are Transfermarkt's.
          </p>
        </>
      )}

      <h2>Where to be careful</h2>
      <ul className="cautions">
        <li><strong>Superstars.</strong> Above about €100M the model compresses values: for a €200M player it predicts around €135M, and the real value falls outside the range. The rankings that compare the model to the market leave these players out.</li>
        <li><strong>Low values.</strong> Below €2M the range covers about 64% of real values instead of 80%. Players under 900 minutes are also less reliable.</li>
        <li><strong>La Liga.</strong> Ranges are a little too narrow there (about 76% coverage).</li>
        <li><strong>Seasons before 2023</strong> were used to train the models, so valuations there look better than they would for a new player. The player page marks these.</li>
        <li><strong>What the model can't see.</strong> Contract length, injuries, national team caps, and detailed stats such as expected goals, passing and tackling aren't in the data. A big gap between model and market is often explained by one of these.</li>
        <li><strong>Undervalued isn't a buy signal.</strong> It means the numbers the model sees point higher than the market's opinion. Use it to decide who to watch.</li>
      </ul>
    </article>
  );
}
