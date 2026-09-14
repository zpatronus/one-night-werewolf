# Copy to config.py and fill in real values. config.py is gitignored.
DEBUG = True
SECRET_KEY = "REPLACE_ME"

# nginx strips the site prefix and forwards /api/... to Django, so the
# backend URLconf always serves under /api/. Leave URL_PREFIX "" unless you
# mount the Django URLconf itself under a sub-path.
URL_PREFIX = ""

# Dev: frontend Vite on :5173 calls backend :8000 cross-origin.
FRONTEND_URLS = ["http://localhost:5173"]
BACKEND_URLS = ["http://localhost:8000"]

# Server public origins to include in CORS allow-list / CSRF_TRUSTED_ORIGINS.
ALLOWED_HOSTS = ["*"]

# Phase-1 duration: backend/is-dev-machine marker -> 60s (dev), else 15s (prod).
from datetime import timedelta  # noqa: E402
OPS_DURATION = timedelta(seconds=60)
