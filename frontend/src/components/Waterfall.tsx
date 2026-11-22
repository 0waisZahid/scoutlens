import { eur, pct } from "../format";
import type { Valuation } from "../types";

/** What each factor does to the model's estimate. Effects multiply; the euro column follows them in order. */
export function Waterfall({ v }: { v: Valuation }) {
  const max = Math.max(...v.factors.map((f) => Math.abs(f.log_effect)), 0.01);
  return (
    <div className="factors" role="table" aria-label="Factors behind the model estimate">
      <div className="factor factor-edge" role="row">
        <span className="factor-name" role="cell">Average player that season</span>
        <span className="factor-track" role="cell" />
        <span className="factor-pct" role="cell" />
        <span className="factor-eur mono" role="cell">{eur(v.baseline_value_eur)}</span>
      </div>
      {v.factors.map((f) => {
        const up = f.log_effect >= 0, w = (Math.abs(f.log_effect) / max) * 50;
        return (
          <div className="factor" role="row" key={f.concept} title={`Multiplies the estimate by ${(1 + f.effect_pct / 100).toFixed(2)}x`}>
            <span className="factor-name" role="cell">{f.concept}</span>
            <span className="factor-track" role="cell" aria-hidden="true"><i className={up ? "pos" : "neg"} style={{ width: `${w}%`, [up ? "left" : "right"]: "50%" }} /></span>
            <span className={`factor-pct mono ${up ? "pos" : "neg"}`} role="cell">{up ? "▲" : "▼"} {pct(f.effect_pct, 0)}</span>
            <span className="factor-eur mono" role="cell">{up ? "+" : "−"}{eur(Math.abs(f.effect_eur))}</span>
          </div>
        );
      })}
      <div className="factor factor-edge factor-total" role="row">
        <span className="factor-name" role="cell">Model estimate</span>
        <span className="factor-track" role="cell" />
        <span className="factor-pct" role="cell" />
        <span className="factor-eur mono" role="cell">{eur(v.model_value_eur)}</span>
      </div>
    </div>
  );
}

export const FACTOR_MEANING: Record<string, string> = {
  "Age": "Value usually peaks in the mid-twenties and falls with age.",
  "League": "Players in the stronger, richer leagues are valued higher.",
  "Position": "Attackers tend to be valued above defenders and goalkeepers.",
  "Playing time": "Minutes and appearances: regular starters are worth more.",
  "Goals & assists (this season)": "Goals and assists per 90 minutes this season.",
  "Recent form (last 2 seasons)": "Goals and assists per 90 over the previous two seasons.",
  "Club strength": "How strong the player's club was the season before. A proxy for the level he plays at.",
  "Club tenure & moves": "Time at the club and recent transfers.",
  "Discipline": "Yellow and red cards per 90 minutes.",
  "Physical": "Height and preferred foot.",
  "Nationality": "Some nationalities carry a market premium or discount.",
  "Share of club output": "How much of his team's minutes, goals and assists he accounts for.",
  "Own previous value": "His own market value the season before: valuations are sticky.",
  "All other factors": "Many small effects combined.",
};
