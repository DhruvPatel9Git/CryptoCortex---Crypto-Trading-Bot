import os
import re
import importlib.util
from urllib.parse import urlparse, urlunparse
from celery import Celery
import ssl
from datetime import timedelta

# For local development, prefer loading environment variables from a .env file
# if python-dotenv is available. This ensures running `celery -A celery_app` from
# the project root picks up the same REDIS_URL set in Backend/.env without
# requiring manual export in the shell.
try:
    from dotenv import load_dotenv
    # Prefer Backend/.env (same folder) but fall back to repo root .env
    backend_env = os.path.join(os.path.dirname(__file__), '.env')
    repo_env = os.path.join(os.path.dirname(__file__), '..', '.env')
    loaded = False
    for dotenv_path in (backend_env, repo_env):
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
            print(f"[celery_app] loaded environment from {dotenv_path}")
            loaded = True
            break
    if not loaded:
        # nothing found; continue silently
        pass
except Exception:
    # If dotenv isn't installed, skip silently; users must export env vars manually
    pass


def _normalize_redis_env(value: str) -> str:
    """Normalize various Redis environment value formats into a plain URI.

    Handles values like:
      - the raw URI: redis://... or rediss://...
      - a redis-cli command such as: 'redis-cli --tls -u redis://...'
    Also converts 'redis://...' + '--tls' into 'redis://...'.
    """
    if not value:
        return value

    s = value.strip()

    # If someone pasted a redis-cli invocation, extract the -u argument
    m = re.search(r"-u\s+([^\s]+)", s)
    if m:
        s = m.group(1)

    # If --tls was present on the original string and scheme is redis, keep redis scheme
    if "--tls" in value and s.startswith("redis://"):
        s = "redis://" + s[len("redis://"):]

    # If host looks like Upstash (or other known TLS-only providers) and scheme is redis,
    # promote to rediss so Kombu/Celery uses TLS without requiring the env var to change.
    try:
        p = urlparse(s)
        hostname = (p.hostname or "").lower()
        if hostname.endswith("upstash.io") and p.scheme == "redis":
            s = "redis://" + s[len("redis://"):]
    except Exception:
        pass

    return s


REDIS_URL = _normalize_redis_env(os.getenv("REDIS_URL", "redis://localhost:6379/0"))

# Determine whether we should set SSL options for the broker based on the URL
_ssl_opts = None
try:
    _verify_env = os.getenv("REDIS_SSL_VERIFY", "1").lower()
    _verify = _verify_env not in ("0", "false", "no")
    ca_path = os.getenv("REDIS_CA_CERTS")

    _p_temp = urlparse(REDIS_URL)
    _hostname_temp = (_p_temp.hostname or "").lower()
    # If scheme is explicitly rediss or host looks like Upstash, prepare ssl options
    # Per request, use CERT_NONE to disable certificate verification.
    if _p_temp.scheme == "rediss" or _hostname_temp.endswith("upstash.io"):
        _ssl_opts = {"ssl_cert_reqs": ssl.CERT_NONE}
        if ca_path:
            _ssl_opts["ssl_ca_certs"] = ca_path
except Exception:
    _ssl_opts = None

# Determine which module import style will work in this process:
# - If the parent package `Backend` is importable, use the fully-qualified names.
# - Otherwise, use top-level module names so Celery can be started from the `Backend/` folder.
includes = []
if importlib.util.find_spec("Backend") is not None:
    includes = [
        "Backend.trade_tasks",
        "Backend.fetch_binance.background_jobs",
    ]
else:
    includes = [
        "trade_tasks",
        "fetch_binance.background_jobs",
    ]

# Create Celery app instance with a context-aware include list so the worker
# registers tasks whether started from repo root or the Backend/ folder.
# Note: we intentionally do NOT set the result backend here. We must apply
# SSL options (if applicable) to `app.conf` before configuring the result
# backend so Kombu/Celery does not raise validation errors about missing
# `ssl_cert_reqs` for rediss:// URLs.
app = Celery(
    "cryptocortex",
    broker=REDIS_URL,
    include=includes,
)

# Basic Celery configuration (result backend set below after SSL options)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    result_expires=3600,
)

# Apply prepared SSL options to Celery if applicable. This must be set before
# we assign the `result_backend` so the backend can be initialized with the
# correct SSL options and avoid Kombu/Celery validation errors.
if _ssl_opts:
    try:
        app.conf.broker_use_ssl = _ssl_opts
        app.conf.result_backend_use_ssl = _ssl_opts
        print(f"[celery_app] broker_use_ssl set (ssl_cert_reqs={'CERT_REQUIRED' if _ssl_opts.get('ssl_cert_reqs')==ssl.CERT_REQUIRED else 'CERT_NONE'})")
    except Exception:
        # On error, don't prevent import — we'll rely on default behavior and logs
        print("[celery_app] failed to set broker_use_ssl; continuing without it")

# Now set the result backend URL so Celery's backend initialization sees
# the SSL options above.
# Some Celery/redis-backend versions require that a `rediss://` URL include
# an `ssl_cert_reqs` query parameter. To avoid that strict URL validation we
# present the backend as a `redis://` URL (no scheme-level validation) while
# keeping `broker` as the original `REDIS_URL` and providing `result_backend_use_ssl`.
try:
    _p_result = urlparse(REDIS_URL)
    if _p_result.scheme == "rediss":
        # Some Celery redis backend implementations validate that a rediss://
        # URL includes an `ssl_cert_reqs` parameter. Append the required
        # query params so the backend accepts the URL and still uses TLS.
        ca_path = os.getenv("REDIS_CA_CERTS") or ""
        query_parts = ["ssl_cert_reqs=CERT_NONE"]
        if ca_path:
            query_parts.append(f"ssl_ca_certs={ca_path}")
        query = "&".join(query_parts)
        REDIS_RESULT_BACKEND = urlunparse((
            "rediss",
            _p_result.netloc,
            _p_result.path or "",
            "",
            query,
            "",
        ))
    else:
        REDIS_RESULT_BACKEND = REDIS_URL
except Exception:
    REDIS_RESULT_BACKEND = REDIS_URL

app.conf.result_backend = REDIS_RESULT_BACKEND

# Example beat schedule placeholder — add periodic tasks here as needed
app.conf.beat_schedule = {
    # "example-every-5-mins": {
    #     "task": "fetch_binance.background_jobs.settle_filled_limit_orders_task",
    #     "schedule": timedelta(minutes=5),
    #     "args": ()
    # },
}


# Print a masked broker URL on import to help debug connection issues.
# We avoid printing secrets: password is replaced with '***'.
try:
    _p = urlparse(REDIS_URL)
    if _p.username or _p.password:
        netloc = ""
        if _p.username:
            netloc += _p.username
            if _p.password:
                netloc += ":***"
            netloc += "@"
        host = _p.hostname or ""
        port = f":{_p.port}" if _p.port else ""
        netloc += f"{host}{port}"
        masked = urlunparse((_p.scheme, netloc, "", "", "", ""))
    else:
        masked = REDIS_URL
    # Only print a short debug message; this helps verify worker uses the right broker
    print(f"[celery_app] Using broker: {masked}")
except Exception:
    # If parsing fails, still print the raw (untouched) value but warn
    print("[celery_app] Using broker (raw): <unable to mask>")
