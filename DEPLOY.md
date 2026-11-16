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
| `ALLOWED_ORIGINS` | Only needed if the site is hosted separately from the API, e.g. `https://yoursite.com` |

## Before going public

- Add `data/processed/clubs.csv` for club names (see README).
- The dataset is Transfermarkt data from Kaggle: check its licence before publishing it.
