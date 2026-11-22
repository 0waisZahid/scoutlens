# ScoutLens security audit

Audit date: 2026-11-22  
Scope: FastAPI/API and ML loading, React/Vite frontend, dependencies, Docker, deployment configuration, GitHub Actions, and secret-pattern scanning.

## Findings and fixes

| ID | Severity | File and line | What was wrong | How it was fixed | How it was verified |
|---|---|---|---|---|---|
| SL-01 | High | `frontend/package.json:19,26`; `frontend/package-lock.json` | The initial `npm audit` reported a high-severity React Router redirect/constructor-injection advisory, plus Vite/esbuild development-server exposure. | Pinned Vite to `6.4.5` and React Router DOM to `7.18.6`, including the lockfile. | `npm audit` and `npm audit --omit=dev` report zero vulnerabilities. Production browser checks loaded all seven routes with no console errors or failed requests. |
| SL-02 | Medium | `requirements.txt:1-8`; `requirements-dev.txt:1-5` | Runtime dependencies previously used open-ended minimums or no version; test/scanner-only packages were mixed into runtime installation. | Pinned direct runtime dependencies, removed unused direct requirements, and moved tests/scanners to pinned development requirements. | `pip-audit -r requirements.txt`: no known vulnerabilities. Full tests pass. |
| SL-03 | Low | `api/main.py:49-61` | CORS allowed every origin by default. | Production now defaults to no cross-origin access; development allows only `http://localhost:5173`. Explicit origins are parsed from `ALLOWED_ORIGINS`, wildcard origins are rejected, and only GET/OPTIONS are allowed without credentials. | Backend CORS tests pass. A production request with `Origin: https://attacker.example` returned no `Access-Control-Allow-Origin` header. |
| SL-04 | Medium | `api/main.py:63-176`; `api/service.py:272-290,340-355,393-407` | Public GET endpoints could repeatedly invoke expensive analytics, graph, ranking, or explanation work; model initialization failures could trigger repeated builds. | Added a bounded in-memory per-client rate limiter (120 GETs/minute, at most 4,096 client entries), capped analytics instances, and cached model-initialization failures so callers receive a generic 503 instead of rebuilding repeatedly. Existing season, similarity, and global-importance caches are bounded by the dataset/scopes. | Added 429 and single-build-after-failure tests; `python -m pytest -q` passes. |
| SL-05 | Medium | `api/main.py:181-311` | Search, ID, season, and ranking inputs were insufficiently bounded; `KeyError` details and unknown IDs could disclose internal lookup text. | Added search length, ID, season, age, minutes, value, and result-count limits; reject inverted ranges; return fixed 404/422 messages. | Added invalid-input and fixed-error-message tests; `python -m pytest -q` passes. |
| SL-06 | Low | `api/main.py:42,91-131`; `frontend/index.html:10`; `frontend/vercel.json:4-15` | Production API docs were enabled, security headers were absent, and the theme initializer was inline. The first CSP browser check also showed that Vite-inlined font data needed an explicit allowance. | `ENV=production` disables the docs/OpenAPI routes. Added CSP, nosniff, referrer, permissions, and frame protections to the API and Vercel. Moved theme initialization to `frontend/public/theme-init.js`; scripts remain self-only. CSP permits the data fonts emitted by the build and can allow an explicitly configured photo origin on the API. | Production `/docs`, `/redoc`, and `/openapi.json` returned SPA HTML rather than API docs/schema. `curl -I /health` returned 200 with all headers. The final Playwright route pass reported no console errors or failed requests. |
| SL-07 | Medium | `frontend/src/csv.ts:1-5`; `frontend/src/pages/Watchlist.tsx:16` | Spreadsheet formula-leading player names were exported as active CSV cells. | Prefixes cells beginning with `=`, `+`, `-`, `@`, tab, or carriage return with an apostrophe, then applies CSV quoting. | Added focused Node tests for formula prefixes, delimiters, and quotes; `npm test` passes. |
| SL-08 | Low | `frontend/src/photo-url.ts:1-9`; `frontend/src/format.ts:41-43` | The configured photo template was not restricted to HTTPS and inserted IDs without URL encoding. | Validate the parsed URL protocol as HTTPS and encode each substituted ID. | Added tests for HTTPS, HTTP/javascript rejection, and encoded IDs; `npm test` passes. |
| SL-09 | Low | `ml/model_integrity.py:13-45`; `ml/train_and_tune.py:168-173`; `ml/uncertainty.py:101-106`; `ml/forecast.py:90-95` | XGBoost model/metadata files had no integrity check before loading. The reviewed loaders use XGBoost JSON, not Python pickle/joblib deserialization, so no pickle-based code-execution path was found. | Added a SHA-256 manifest covering model JSON and metadata, verification before loading, fail-closed errors, and manifest regeneration after model saves. Replaced training-time `assert` checks flagged by Bandit with explicit runtime checks. | Tamper/missing-manifest and loader-order tests pass. `bandit -r api core ml etl -q` reports no findings. |
| SL-10 | Low | `Dockerfile:2-31`; `.dockerignore:1-12` | The final image previously ran as root; base tags were mutable; and the Docker ignore rules did not exclude all environment files, `.venv`, or nested `node_modules`. | Pinned Node and Python base images by verified digest, kept `npm ci`, added a non-root user and health check, set production mode, and expanded ignore rules. Docker copies only processed data. | Base tags/digests were verified against Docker Hub. Docker build/image inspection could not be run because Docker is not installed in this environment. |
| SL-11 | Low | `.github/workflows/tests.yml:8-37`; `.github/workflows/codeql.yml:11-34`; `.github/dependabot.yml:1-15` | The existing workflow used mutable action tags and had no explicit permissions, dependency update automation, or CodeQL workflow. | Added least-privilege workflow permissions, pinned actions to verified commit SHAs, added pip/npm/Actions Dependabot updates, and enabled scheduled CodeQL scans. | Workflow YAML/configuration was inspected; runtime CI execution is unavailable locally. |

## Scan and verification summary

- Initial frontend audit: 4 advisories (3 moderate, 1 high); production-only audit: 2 moderate. Final `npm audit` and `npm audit --omit=dev`: **0 vulnerabilities**.
- `pip-audit -r requirements.txt`: **no known vulnerabilities**.
- Initial Bandit scan found two low-severity `assert` checks in offline training verification; these are now explicit runtime checks. Final Bandit scan: **0 findings**.
- Secret-pattern scans found no private-key or credential-assignment matches in project sources. Git history could not be reviewed: the current branch has no commits.
- Source review found no `dangerouslySetInnerHTML`, `innerHTML`, `eval`, `new Function`, pickle/joblib loader, or external user-controlled anchor. `VITE_API_URL` and `VITE_PHOTO_URL_TEMPLATE` are the only Vite variables found; both are public configuration, not secrets.
- SPA traversal probes (`/..%2f..%2fetc/passwd`, `/%2e%2e/`, and encoded variants) returned the SPA fallback and did not reveal the outside-file marker. The existing resolved-path containment check was retained.
- Final validation: `python -m pytest -q` — **153 passed**; frontend `npm test` — **2 passed**; `npm run build` — **passed**. Production browser checks returned HTTP 200 for `/`, `/explore`, `/player/418560`, `/compare`, `/connect`, `/watchlist`, and `/method`, with no console errors or failed requests.
- `curl -I /health` in production returned HTTP 200 and the configured security headers. Production docs paths returned HTML SPA fallback, not API documentation or an OpenAPI document.

## Residual risk

- The API has no authentication by design and serves public football data. CORS is not an authorization boundary.
- Rate limiting is in-memory and keyed by the ASGI peer IP. Behind a reverse proxy, configure rate limiting at the trusted edge or configure trusted proxy handling; do not trust arbitrary client-supplied forwarding headers. Multiple application instances each have their own limiter.
- Python direct requirements are pinned, but the runtime dependency tree is not a hash-locked, signed artifact. Review dependency updates and rebuild from trusted package sources.
- The model manifest is not a digital signature and is stored alongside the models. It detects file drift/tampering when the manifest is trusted, but does not authenticate a repository or release whose manifest and model files were changed together. Obtain model files only from a trusted source.
- The Dockerfile was not built or inspected locally because Docker is unavailable.
- Git history and remote configuration were unavailable: `git rev-parse --show-toplevel` resolved to the user profile directory, the branch has no commits, and no project remote was configured. The source-tree scan did not find secret-pattern matches, but this cannot establish that historical secrets were never committed.
- Check the Transfermarkt/Kaggle dataset licence before public deployment.
- GitHub private vulnerability reporting must be enabled by the repository maintainer; no separate reporting email or project remote was available to configure.

## Deployment checklist

- Set `ENV=production`; set `PORT` as required by the host.
- For same-origin frontend/API hosting, leave `ALLOWED_ORIGINS` unset. If cross-origin hosting is required, set it to the exact frontend origin(s), comma-separated; never use `*`.
- Use HTTPS for the public site and API. If hosting them separately, set the public frontend `VITE_API_URL` and add only the API origin to `connect-src` in `frontend/vercel.json`.
- Treat all `VITE_*` values as public. Never put credentials or server secrets in frontend environment variables.
- If enabling portraits, use an HTTPS `VITE_PHOTO_URL_TEMPLATE`; set `PHOTO_URL_ORIGIN` for the API-served site, or add only the exact image host to Vercel's `img-src`.
- Keep model files and their SHA-256 manifest together and obtain both from a trusted release/source.
- Enable GitHub private vulnerability reporting and review Dependabot and CodeQL alerts.
