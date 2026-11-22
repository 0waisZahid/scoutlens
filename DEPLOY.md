# Deploying ScoutLens

The API serves the built website, so the whole app is **one service on one URL**.
The `Dockerfile` builds the frontend, then runs `uvicorn` on `$PORT` (default 7860).

## Check it works locally (needs Docker Desktop)

```powershell
docker build -t scoutlens .
docker run -p 7860:7860 scoutlens
```
Open http://localhost:7860 (the first page takes about 5 seconds while the models load).

## Option A: Hugging Face Spaces (free, a good fit for ML apps)

1. Create an account, then New Space, choose **Docker** as the SDK, keep it public or private.
2. Put this block at the very top of `README.md` in the Space (not required in your main repo):
   ```
   ---
   title: ScoutLens
   sdk: docker
   app_port: 7860
   ---
   ```
3. Push your repo to the Space's git URL (or upload the files). It builds and starts by itself.

## Option B: Render / Railway / Fly.io

Create a web service from the GitHub repo, choose **Docker**, no start command needed.
Check the plan's memory limit: the app needs roughly 500 MB with models loaded, so a 512 MB free plan may be too small.

## Settings

| Variable | Meaning |
|---|---|
| `PORT` | Port to listen on (most hosts set this for you) |
| `ENV` | Set to `production` to disable API docs and use production CORS defaults. |
| `ALLOWED_ORIGINS` | Comma-separated frontend origins when the site is hosted separately. Production allows no cross-origin requests by default; `*` is rejected. |
| `PHOTO_URL_ORIGIN` | Optional HTTPS origin that matches `VITE_PHOTO_URL_TEMPLATE` when the API serves the built site. |

## Before going public

- Add `data/processed/clubs.csv` for club names (see README).
- The dataset is Transfermarkt data from Kaggle: check its licence before publishing it.
- Use HTTPS and set `ALLOWED_ORIGINS` to the exact frontend origin only when cross-origin hosting is required.
- If deploying the frontend separately, set its public `VITE_API_URL` and update `connect-src` in `frontend/vercel.json` to the API origin.
- If enabling portraits on the API-served site, set `PHOTO_URL_ORIGIN` to the same HTTPS origin as the public `VITE_PHOTO_URL_TEMPLATE`.
- If enabling portraits on Vercel, add only that HTTPS host to `img-src` in `frontend/vercel.json`.


## Security settings you must set (added after the security review)

| Where | Setting | Why |
|---|---|---|
| API host | `ENV=production` | Turns off /docs and /openapi.json. The Dockerfile sets it already. |
| API host | `ALLOWED_ORIGINS=https://your-site.vercel.app` | Only needed if the website is hosted separately (Vercel). Never `*`. |
| `frontend/vercel.json` | Replace `https://YOUR-API-HOST.example` in `connect-src` with your API's real https address | Otherwise the browser blocks every API call and the site shows "can't reach the API". |
| Vercel project | `VITE_API_URL=https://your-api-host` | Where the built site sends API calls. |

After retraining or replacing a model file, regenerate its checksum or the API will refuse to start:

```
python -c "from ml.model_integrity import write_model_manifest; write_model_manifest()"
```
