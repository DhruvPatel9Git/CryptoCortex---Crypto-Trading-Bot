**Deploying CryptoCortex Backend on Render (step-by-step)**

This document explains how to deploy the `Backend` FastAPI app and a Celery worker on Render using the Dockerfile added to `Backend/Dockerfile`.

Prerequisites

- A Render account (https://render.com)
- A GitHub/GitLab repo connected to Render (or you can deploy from Docker image)
- A MongoDB instance (MongoDB Atlas or a provider) and a connection URI
- A Redis instance (Render Redis, Redis Cloud, or similar) for Celery broker

Files added

- `Backend/Dockerfile` — container image for the backend and worker
- `Backend/.dockerignore` — files excluded from the image build

1. Prepare environment variables
   On Render, the Web Service and Worker both need access to a set of environment variables. Common variables used by this project:

- `MONGODB_URI` — MongoDB connection string for Beanie/Motor
- `REDIS_URL` — Redis URL for Celery broker (e.g. `redis://:password@host:6379/0`)
- `SECRET_KEY` — your app secret if used
- `ENV` — set to `production` or `staging` as desired
- Any Binance API keys if your app needs them: `BINANCE_API_KEY`, `BINANCE_SECRET`

2. Create the Web Service in Render

- In the Render dashboard, click "New" → "Web Service".
- Connect your Git repo and choose the branch you want to deploy.
- Environment: Docker
- Dockerfile Path: `Backend/Dockerfile`
- Build Command: leave blank (Render will use Dockerfile)
- Start Command: leave blank (the Dockerfile's `CMD` runs Gunicorn). Alternatively you can override to:
  - `gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:$PORT --workers 2`
- Set Environment variables (see step 1). Add `PORT=8000` if Render doesn't set it automatically.

Notes: The Dockerfile copies `Backend/` into `/app` and runs `main:app` (so FastAPI `main.py` must expose `app`). If your import path differs, update `CMD`.

3. Create a Worker service for Celery

- In Render, click "New" → "Worker".
- Use the same repo and branch.
- Environment: Docker
- Dockerfile Path: `Backend/Dockerfile`
- Start Command: a Celery worker command. Example safe-for-Windows-style concurrency (use `solo` pool):

  celery -A celery_app.app worker --loglevel=info --pool=solo

Replace `celery_app.app` if your Celery app object is located elsewhere (the project uses `Backend/celery_app.py`). If you need periodic tasks (beat) you can create a second worker with `celery -A celery_app.app beat --loglevel=info` or run `celery -A celery_app.app worker --loglevel=info & celery -A celery_app.app beat --loglevel=info` in a custom start script (not recommended).

4. Redis and MongoDB

- Render provides managed Redis as an addon; you can also use Redis Cloud or AWS ElastiCache. Point `REDIS_URL` to that Redis instance.
- For MongoDB, Render may not host MongoDB directly depending on your plan — use MongoDB Atlas and paste the connection string into `MONGODB_URI`.

5. Deploy and test

- Deploy the Web Service; watch the build logs.
- Once the web service is up, deploy the worker. Check worker logs for Celery registration and tasks.
- Verify that the FastAPI endpoints respond.

6. Common troubleshooting

- Import errors: check that the application entrypoint `main:app` imports correctly in the container (module paths depend on Docker COPY location).
- Long model files: the repo contains a `bert_squad_model/` directory — you should not include large model files in the image. Instead, store the model in cloud storage and download it during build or on startup, or mount it as volume.
- Secrets: never check secrets into repo; use Render environment variables.

7. Optional: Automatic deploy using `render.yaml`

You can add a `render.yaml` file at the repo root that defines both web and worker services and managed resources. Render docs show the correct syntax; I can help generate a `render.yaml` tailored to this repo if you want (I didn't add one automatically to avoid making presumptive service names).

If you want, I can:

- generate a `render.yaml` for one-click deploys,
- add a small healthcheck endpoint if needed,
- or create a lightweight startup script that downloads the BERT model from an S3/GCS bucket on container start.

Repository additions and how to use them

- A sample `render.yaml` has been added to the repo root for a one-click manifest deploy (`render.yaml`). Edit the placeholders (envVars) in that file on Render or in the repo before deploying.
- The repo includes `Backend/startup.sh` and `Backend/scripts/download_bert_model.py`. To use them, set the environment variable `BERT_MODEL_URL` in your Render service to a Hugging Face model id (for example `bert-large-uncased-whole-word-masking-finetuned-squad`) or another path supported by `transformers.from_pretrained`.

Example: set `BERT_MODEL_URL` in Render to `bert-large-uncased-whole-word-masking-finetuned-squad` (or another model). On container start the script will download tokenizer and model to `./chatbot/bert_squad_model` if it does not exist, then start the web server.

If you prefer to include the model in the image (bigger image but faster startup), move the download step into the Dockerfile during build instead of runtime.
