# ScoutLens

Football player analytics and market-intelligence platform: performance stats,
ML-based valuation, forecasting with uncertainty, and SHAP explainability.

**Status:** valuation models and core data structures are built and tested.
API, frontend, SHAP, and uncertainty ranges are still to do (see Roadmap).

## What's in the repo

| Folder | Contents |
|---|---|
| `core/` | Valuation formula, schema, player classes, and from-scratch data structures (min-heap + `top_k`, trie autocomplete, merge sort) |
| `etl/` | Data cleaning and loading (`clean.py`, `add_club.py`, `load.py`) and a fake-player simulator |
| `ml/` | Training scripts, evaluation metrics, and the leakage check |
| `tests/` | pytest suite |
| `benchmarks/` | Merge sort timing benchmark |
| `reports/` | Saved results from the training scripts |
| `data/processed/` | Cleaned Transfermarkt-based data (27k player-seasons, 2012-2025, 5 leagues) |
| `api/`, `frontend/` | Empty, not built yet |

## Setup

Needs **Python 3.11 or newer** (the pinned versions in `requirements.txt` require it).

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

## Roadmap

- [x] Real data pipeline and cleaning
- [x] Baseline and improved models, evaluated on future seasons
- [x] Heap, trie, merge sort with tests
- [x] Leakage check on club strength
- [ ] Richer stats (xG, passes, tackles), contract length, national team caps
- [ ] Final model saved to `models/`
- [ ] SHAP explanations
- [ ] Prediction ranges (uncertainty)
- [ ] API (FastAPI) using the trie for search and `top_k` for rankings
- [ ] Frontend
