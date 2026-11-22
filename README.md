# ScoutLens

Football player analytics and market-intelligence platform: performance stats,
ML-based valuation, forecasting with uncertainty, and SHAP explainability.

**Status:** data pipeline, valuation model, ranges, forecasts, SHAP explanations, REST API and web
frontend are built and tested. Remaining work needs new data (see Roadmap).

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
| `models/` | Saved valuation model, 80% range models, and forecast models (with metadata) |
| `api/` | FastAPI app: search, profiles, valuation + range + explanation + forecast, rankings, similar players, teammate graph |
| `frontend/` | React + TypeScript (Vite) web app: board, player pages, compare, connections, watchlist, method |

## Setup

Tested on Python 3.12. The pinned runtime dependencies require Python 3.12 or newer.

```bash
python3 -m venv venv
source venv/bin/activate          # Windows PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest
```

**Mac:** if XGBoost fails with `libomp.dylib could not be loaded`, run `brew install libomp`.
**Windows PowerShell:** if activation is blocked, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.
For a runtime-only installation, use `pip install -r requirements.txt`.

Always run scripts from the repo root with `python -m`, e.g. `python -m ml.train_improved`.

### Windows PowerShell setup

From the repository root:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

If activation is blocked, permit local scripts once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### Run tests

Run the Python suite from the repository root:

```bash
python -m pytest
```

Run the frontend tests and production build:

```bash
cd frontend
npm install
npm test
npm run build
cd ..
```

## Running the models

```bash
python -m ml.train_real        # baseline: formula vs XGBoost on real data
python -m ml.train_improved    # adds inflation adjustment, extra features, club strength
python -m ml.leakage_check     # tests whether the club_strength gain is real
python -m ml.train_and_tune    # Phase 2: feature ablation, tuning, saves models/ (about 3 min)
python -m ml.uncertainty       # Phase 3: ranges (run after train_and_tune)
python -m ml.forecast          # Phase 3: next-season forecaster (run after train_and_tune)
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
from the season being predicted reaches any feature). `ml/train_and_tune.py` keeps or
drops each feature group using **validation seasons 2021-22 only**, tunes XGBoost with a
random search, scores the test seasons **once**, and saves the model. Full output:
`reports/phase2_results.txt`.

| Feature group | Test median error | Kept? |
|---|---|---|
| base (age, minutes, goals/assists per 90, position, league) | 51% | yes |
| + extra (appearances, cards, height, sub-position, foot) | 51% | yes |
| + club strength (previous season) | 35% | yes |
| + history (last season's output, 2-season rates, club tenure, transfer signals) | 33% | yes |
| + context (share of club output, peer z-scores) | 33% | no, no validation gain |
| + nationality (top 15 countries) | 33% | yes |

| Final valuation model (seasons 2023+) | R² (log) | Median error | Within 25% | Within 50% |
|---|---|---|---|---|
| **Tuned, saved model** | 0.83 | **31%** | 41% | 72% |
| Same features, untuned | 0.82 | 33% | 39% | 70% |

**Quote 31% as the valuation accuracy.**

**Market trend fix.** Values are detrended by a market-level trend. Extrapolating the
2012-2022 growth made the model over-predict 2023+ values by about 15%, because the median
player's value stopped rising. Holding the trend flat after the last training season won on
the validation seasons (and on test), cutting median error from 34% to 31%.

**Not done, because the data is not available:** contract years left and national team
caps (the Kaggle Transfermarkt data only has a current contract snapshot, so it cannot be
used for past seasons, and has no caps), and xG, passing and tackling stats (FBref).
Club tenure is used as a rough contract proxy. When you get any of these as a CSV with
`player_id`, `season` and numeric columns, run
`python -m ml.train_and_tune --extra your_file.csv` and it is tested as one more feature group.

## Phase 3: explanations, ranges, and next-season forecasts

```bash
python -m ml.explain "Name"        # why the model valued this player that way
python -m ml.explain --global      # which factors matter most overall
python -m ml.uncertainty           # train + calibrate + save the 80% range models
python -m ml.forecast              # train + evaluate + save the next-season forecaster
python -m ml.forecast "Name"       # next-season forecast for one player
```

**Explanations (`ml/explain.py`).** Uses XGBoost's built-in TreeSHAP, which gives the same
numbers as the `shap` library (checked) without version problems. Contributions are
grouped into plain concepts (Age, Club strength, Playing time, ...) and shown as a percent
effect on value plus a euro waterfall that sums exactly to the prediction.
Across 2023+ players the biggest drivers are age, club strength, and playing time.

**Ranges (`ml/uncertainty.py`).** Two XGBoost quantile models (10th and 90th percentile)
trained before 2021, then widened by conformal calibration on 2021-22 so about 80% of
players fall inside. Checked on the untouched 2023+ seasons:

| | Coverage (target 80%) | Typical range width (high / low) |
|---|---|---|
| Raw quantile models | 78% | 4.7x |
| **Calibrated (saved)** | **81%** | 5.1x |

The range is wide because the model's typical error is 31%. It is weakest for players the
model values under EUR 2M (64% coverage), La Liga (76%) and players with under 900 minutes
(77%); it is a little too wide for EUR 10-30M players (88%). Re-calibrate on the newest
seasons whenever new data is added.

**Forecasts (`ml/forecast.py`).** Predicts a player's value one season ahead from his
current value, stats, history and club. Trained only on pairs whose next season is before
2023, then scored once on 2023+:

| Next-season value | R² (log) | Median error | Within 25% | Within 50% |
|---|---|---|---|---|
| **Forecast model** | 0.88 | **24%** | 52% | 82% |
| No-skill baseline (value stays the same) | 0.82 | 33% | 44% | 73% |

It ranks who will rise and who will fall (rank correlation 0.52) and gets the direction
right for 74% of players whose value moves more than 15%. Its 80% range covered 83% of
players (median width 2.8x).

**Known limitation.** The from-scratch valuation compresses superstar values: for a player
worth EUR 200M it predicts about EUR 135M, and the real value falls outside its range. The
forecast starts from the player's current value, so it does not have this problem.

## Running the app

Two terminals, both from the repo root.

```bash
# 1. API (builds the models and feature tables in the background at start-up, about 5 s)
uvicorn api.main:app --reload            # docs at http://127.0.0.1:8000/docs

# 2. Frontend (needs Node 18+)
cd frontend
npm install
npm run dev                              # http://localhost:5173
```

The frontend calls `http://127.0.0.1:8000` by default; set `VITE_API_URL` in `frontend/.env` to change it
(see `.env.example`). `npm run build` type-checks and produces `frontend/dist`.

**API endpoints**

| Endpoint | What it returns | Built on |
|---|---|---|
| `GET /players/search?q=` | Autocomplete, most valuable first | `core.trie`, `core.heap.top_k` |
| `GET /players/{id}` | Profile, season stats, value history, trend, position percentiles | `core.timeseries` |
| `GET /players/{id}/valuation?season=` | Model value, 80% range, factor breakdown, next-season forecast (with the actual value when it exists) | `ml.*` |
| `GET /players/{id}/similar` | Nearest players by profile | `core.similarity` |
| `GET /players/{id}/teammates`, `GET /connections?a=&b=` | Teammates and shortest teammate chain | `core.graph` (BFS) |
| `GET /rankings?sort=...` | Top players by value, model gap, forecast or stats, with filters | `core.heap.top_k` |
| `GET /model/info`, `GET /meta` | Accuracy, data coverage, global importance, filter options | model metadata |

`undervalued`, `overvalued`, `risers` and `fallers` only rank players valued EUR 2M-100M (EUR 1M+ for
forecasts), where the model is most reliable (see the limitations in Phase 3). Override with
`min_value` / `max_value`.

**Club names.** `data/processed/clubs.csv` maps the clubs in the processed player data to names, so
the UI can show club names instead of IDs. The mapping is sourced from the
[Transfermarkt datasets project](https://github.com/dcaribou/transfermarkt-datasets) (CC0 1.0).
Refresh the mapping if you replace the player data with data containing different club IDs.

## Roadmap

- [x] Real data pipeline and cleaning
- [x] Baseline and improved models, evaluated on future seasons
- [x] Heap, trie, merge sort with tests
- [x] Leakage check on club strength
- [x] Leakage-safe feature engineering, validated feature selection, tuned model saved to `models/`
- [x] SHAP explanations, 80% prediction ranges, next-season forecasts
- [ ] Contract length, national team caps, xG/passes/tackles (needs new data, see Phase 2)
- [x] API (FastAPI) using the trie for search and `top_k` for rankings
- [x] Frontend (React + TypeScript)
- [x] Club names
- [ ] A database instead of in-memory data
