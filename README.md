# ScoutLens

Football player analytics and market-intelligence platform: performance stats,
ML-based valuation, forecasting with uncertainty, and SHAP explainability.

**Status:** valuation model (tuned and saved) and core data structures are built and tested.
SHAP, uncertainty ranges, API, and frontend are still to do (see Roadmap).

## What's in the repo

| Folder | Contents |
|---|---|
| `core/` | Valuation formula, schema, player classes, and from-scratch data structures (min-heap + `top_k`, trie autocomplete, merge sort) |
| `etl/` | Data cleaning and loading (`clean.py`, `add_club.py`, `load.py`) and a fake-player simulator |
| `ml/` | Feature engineering, training and tuning scripts, evaluation metrics, and the leakage check |
| `tests/` | pytest suite |
| `benchmarks/` | Merge sort timing benchmark |
| `reports/` | Saved results from the training scripts |
| `data/processed/` | Cleaned Transfermarkt-based data (27k player-seasons, 2012-2025, 5 leagues) |
| `models/` | Saved tuned model (`scoutlens_xgb_v2.json`) and its metadata |
| `api/`, `frontend/` | Empty, not built yet |

## Setup

Tested on Python 3.12. It should also work on 3.9+, since `requirements.txt` uses `>=` bounds.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest
```

**Mac:** if XGBoost fails with `libomp.dylib could not be loaded`, run `brew install libomp`.
**Windows PowerShell:** if activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

Always run scripts from the repo root with `python -m`, e.g. `python -m ml.train_improved`.

## Running the models

```bash
python -m ml.train_real        # baseline: formula vs XGBoost on real data
python -m ml.train_improved    # adds inflation adjustment, extra features, club strength
python -m ml.leakage_check     # tests whether the club_strength gain is real
python -m ml.train_and_tune    # Phase 2: feature ablation, tuning, saves models/ (about 3 min)
```

All real-data scripts train on seasons before 2023 and test on 2023 onward, so
the model is always judged on the future.

## Results (held-out seasons 2023+)

| Model | R² (log) | Median error | Within 25% | Within 50% |
|---|---|---|---|---|
| Formula baseline | 0.51 | 57% | 22% | 44% |
| XGBoost, no club info | 0.55 | 54% | 23% | 46% |
| + club strength (same-season teammates) | 0.83 | 32% | 40% | 70% |
| + club strength (previous season only) | 0.78 | 37% | 36% | 63% |
| + club strength (frozen at 2022) | 0.77 | 38% | 35% | 63% |

**Honest number to quote: about 37% median error.** The same-season club
strength feature uses other players' market values from the period being
predicted, which inflates the score by roughly 5 points. The previous-season
version uses only information available beforehand, and still cuts the error
from 54% to 37%, so the club effect is real. About 14% of test rows have no
previous-season club data.

## Phase 2: richer features, tuning, saved model

`ml/feature_engineering.py` adds leakage-safe features (a test proves no market value
from the season being predicted reaches any feature). `ml/train_and_tune.py` then keeps
or drops each feature group using **validation seasons 2021-22 only**, tunes XGBoost
with a random search (early stopping on validation), scores the test seasons **once**,
and saves the model. Full output: `reports/phase2_results.txt`.

| Feature group | Test median error | Kept? |
|---|---|---|
| base (age, minutes, goals/assists per 90, position, league) | 56% | yes |
| + extra (appearances, cards, height, sub-position, foot) | 54% | yes |
| + club strength (previous season) | 38% | yes |
| + history (last season's output, 2-season rates, club tenure, transfer signals) | 36% | yes |
| + context (share of club output, peer z-scores) | 36% | no, no validation gain |
| + nationality (top 15 countries) | 36% | no, no validation gain |

| Final model (seasons 2023+) | R² (log) | Median error | Within 25% | Within 50% |
|---|---|---|---|---|
| **Tuned, saved model** | 0.81 | **34%** | 38% | 67% |
| Same features, untuned | 0.79 | 36% | 37% | 64% |
| Forecast mode (also uses the player's own last known value) | 0.91 | 22% | 56% | 83% |

**Quote 34% as the valuation accuracy.** Forecast mode is a different task: it starts
from the player's last Transfermarkt value, so it is an anchor, not a from-scratch
estimate. It is kept for the forecasting phase and is not the saved model.

**Not done, because the data is not available:** contract years left and national team
caps (the Kaggle Transfermarkt data only has a current contract snapshot, so it cannot be
used for past seasons, and has no caps), and xG, passing and tackling stats (FBref).
Club tenure is used as a rough contract proxy. When you get any of these as a CSV with
`player_id`, `season` and numeric columns, run
`python -m ml.train_and_tune --extra your_file.csv` and it is tested as one more feature group.

## Roadmap

- [x] Real data pipeline and cleaning
- [x] Baseline and improved models, evaluated on future seasons
- [x] Heap, trie, merge sort with tests
- [x] Leakage check on club strength
- [x] Leakage-safe feature engineering, validated feature selection, tuned model saved to `models/`
- [ ] Contract length, national team caps, xG/passes/tackles (needs new data, see Phase 2)
- [ ] SHAP explanations
- [ ] Prediction ranges (uncertainty)
- [ ] API (FastAPI) using the trie for search and `top_k` for rankings
- [ ] Frontend
