import numpy as np

from core.formula import FormulaModel
from etl.simulate import simulate_players
from ml.evaluate import score


def test_formula_beats_naive_median():
    df = simulate_players(1500)
    tr, te = df.iloc[:1200], df.iloc[1200:]
    pred = FormulaModel().fit(tr).predict(te)
    naive = np.full(len(te), tr.market_value_eur.median())
    assert score(te.market_value_eur, pred)["R2_log"] > 0.5
    assert score(te.market_value_eur, pred)["median_APE_%"] < score(te.market_value_eur, naive)["median_APE_%"]
