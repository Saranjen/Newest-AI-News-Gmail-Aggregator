"""
Daily digest pipeline entrypoint for automation (e.g. GitHub Actions).

Run from the repository root:
    python -m app.jobs.daily_digest
"""
from __future__ import annotations

import logging
import sys
from urllib.parse import urlparse

from app.load_env import load_project_env

load_project_env()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _log_database_target(url: str) -> None:
    """Log host/db name only (no credentials)."""
    try:
        normalized = url.replace("postgresql+psycopg2://", "postgresql://", 1)
        parsed = urlparse(normalized)
        host = parsed.hostname or "?"
        port = parsed.port
        db = (parsed.path or "/").strip("/").split("/")[0] or "?"
        if port:
            logger.info("Database target: host=%s port=%s db=%s", host, port, db)
        else:
            logger.info("Database target: host=%s db=%s", host, db)
    except Exception:
        logger.info("Database target: (unable to parse DATABASE_URL / connection string)")


def main() -> int:
    logger.info("Daily digest job started")
    try:
        from app.database.connection import engine, get_database_url
        from app.database.models import Base

        _log_database_target(get_database_url())

        Base.metadata.create_all(bind=engine)
        logger.info("Database schema ensured")
    except Exception:
        logger.exception("Daily digest job failed while ensuring database schema")
        return 1

    try:
        from app.daily_runner import run_daily_pipeline

        result = run_daily_pipeline(hours=None, top_n=10)
    except Exception:
        logger.exception("Daily digest job failed during pipeline execution")
        return 1

    if result.get("success"):
        logger.info(
            "Daily digest job finished successfully (duration=%.1fs)",
            result.get("duration_seconds", 0),
        )
        em = result.get("email") or {}
        if em.get("success") and em.get("email_sent") is False:
            logger.info(
                "Daily email was not sent — no digest items in lookback window (%s).",
                em.get("skip_reason", "skipped"),
            )
        return 0

    logger.error(
        "Daily digest job finished without success: %s",
        result.get("error") or result.get("email"),
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
