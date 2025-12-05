import os
import re
from urllib.parse import urlparse
import redis


def _normalize_redis_env(value: str) -> str:
    """Normalize various Redis environment value formats into a plain URI.

    Accepts raw URIs or strings containing a `redis-cli` invocation and extracts the -u value.
    Converts `redis://` + `--tls` hints into `redis://`.
    """
    if not value:
        return value
    s = value.strip()
    m = re.search(r"-u\s+([^\s]+)", s)
    if m:
        s = m.group(1)
    if "--tls" in value and s.startswith("redis://"):
        s = "redis://" + s[len("redis://"):]
    # If host is Upstash and scheme is redis, keep redis:// (TLS handling happens via ssl_kwargs)
    try:
        p = urlparse(s)
        hostname = (p.hostname or "").lower()
        if hostname.endswith("upstash.io") and p.scheme == "redis":
            s = "redis://" + s[len("redis://"):]
    except Exception:
        pass
    return s


def _masked(uri: str) -> str:
    try:
        p = urlparse(uri)
        if p.username:
            user = p.username
            host = p.hostname or ""
            port = f":{p.port}" if p.port else ""
            return f"{p.scheme}://{user}:***@{host}{port}"
    except Exception:
        pass
    return uri


# Read REDIS_URL from env and normalize
raw = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_URL = _normalize_redis_env(raw)
print(f"[redis_client] connecting to Redis broker: {_masked(REDIS_URL)}")

# Use redis.from_url which handles redis://
try:
    # Allow disabling SSL verification in environments without system CAs.
    _verify_env = os.getenv("REDIS_SSL_VERIFY", "1").lower()
    _verify = _verify_env not in ("0", "false", "no")
    ssl_kwargs = {}
    if REDIS_URL.startswith("redis://"):
        if _verify:
            ssl_kwargs["ssl_cert_reqs"] = getattr(__import__("ssl"), "CERT_REQUIRED")
        else:
            ssl_kwargs["ssl_cert_reqs"] = getattr(__import__("ssl"), "CERT_NONE")
        ca_path = os.getenv("REDIS_CA_CERTS")
        if ca_path:
            ssl_kwargs["ssl_ca_certs"] = ca_path

    redis_client = redis.from_url(REDIS_URL, decode_responses=True, **ssl_kwargs)
except Exception:
    # Fallback to localhost if parsing fails
    redis_client = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
