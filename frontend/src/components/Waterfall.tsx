import { eur, pct } from "../format";
import type { Valuation } from "../types";

/** Why the model valued this player the way it did: each factor's effect on value. */
export function Waterfall({ v }: { v: Valuation }) {
  const max = Math.max(...v.factors.map((f) => Math.abs(f.log_effect)), 0.01);
  return (
    <div className="factors">
      <div className="factor factor-edge">
        <span className="factor-name">Average player that season</span>
        <span className="factor-track" />
        <span className="factor-pct" />
        <span className="factor-eur">{eur(v.baseline_value_eur)}</span>
      </div>
      {v.factors.map((f) => {
        const w = (Math.abs(f.log_effect) / max) * 50;
        const up = f.log_effect >= 0;
        return (
          <div className="factor" key={f.concept}
            title={`Multiplies value by ${(1 + f.effect_pct / 100).toFixed(2)}x, worth ${eur(Math.abs(f.effect_eur))} at this step`}>
            <span className="factor-name">{f.concept}</span>
            <span className="factor-track" aria-hidden="true">
              <i className={up ? "up" : "down"} style={{ width: `${w}%`, [up ? "left" : "right"]: "50%" }} />
            </span>
            <span className={`factor-pct ${up ? "up" : "down"}`}>{pct(f.effect_pct, 0)}</span>
            <span className="factor-eur">{up ? "+" : "−"}{eur(Math.abs(f.effect_eur))}</span>
          </div>
        );
      })}
      <div className="factor factor-edge factor-total">
        <span className="factor-name">Model estimate</span>
        <span className="factor-track" />
        <span className="factor-pct" />
        <span className="factor-eur">{eur(v.model_value_eur)}</span>
      </div>
    </div>
  );
}
