# Copy to config.py and fill in real values. config.py is gitignored.
DEBUG = True
SECRET_KEY = "REPLACE_ME"

# Django is served under a path prefix (e.g. /onw/) via FORCE_SCRIPT_NAME, and
# nginx proxies the full /onw/api/... through unchanged (does NOT strip it).
# Dev/localhost: "" (no prefix). Production sub-path: "/onw".
URL_PREFIX = ""

# Dev: frontend Vite on :5173 calls backend :8000 cross-origin.
FRONTEND_URLS = ["http://localhost:5173"]
BACKEND_URLS = ["http://localhost:8000"]

# Server public origins to include in CORS allow-list / CSRF_TRUSTED_ORIGINS.
ALLOWED_HOSTS = ["*"]

# Phase-1 duration: backend/is-dev-machine marker -> 60s (dev), else 15s (prod).
from datetime import timedelta  # noqa: E402
OPS_DURATION = timedelta(seconds=60)
