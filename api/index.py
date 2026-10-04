"""
Vercel serverless entry point: exposes the FastAPI backend in ../backend as one function.

vercel.json rewrites every /api/* request here; FastAPI still sees the original path,
so the routers keep their /api/... prefixes.
"""
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Must be set before app.config is imported.
os.environ.setdefault("SERVERLESS", "1")
# scikit-learn is left out of the function bundle to stay under Vercel's size limit;
# the game director falls back to its rule-based behaviour model.
os.environ.setdefault("IBM_DISABLE_ML", "1")

if not os.environ.get("DATABASE_URL"):
    raise RuntimeError(
        "DATABASE_URL is not set. Add a Postgres database to the Vercel project "
        "(Storage → Neon) or set DATABASE_URL in Project Settings → Environment Variables."
    )

from app.database.session import init_db  # noqa: E402
from app.main import app  # noqa: E402,F401  (Vercel serves this ASGI app)

# The ASGI lifespan hook is not guaranteed to run on Vercel, so create tables on cold start.
try:
    init_db()
except Exception:  # a concurrent cold start may race on the seed rows; tables still exist
    logging.getLogger(__name__).exception("init_db failed on cold start")
