"""
Daily digest pipeline entrypoint for automation (e.g. GitHub Actions).

Run from the repository root:
    python -m app.jobs.daily_digest
"""
from __future__ import annotations

import logging
import sys

from app.load_env import load_project_env

load_project_env()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def main() -> int:
    logger.info("Daily digest job started")
    try:
        from app.database.connection import engine
        from app.database.models import Base

        Base.metadata.create_all(bind=engine)
        logger.info("Database schema ensured")
    except Exception:
        logger.exception("Daily digest job failed while ensuring database schema")
        return 1

    try:
        from app.daily_runner import run_daily_pipeline

        result = run_daily_pipeline(hours=24, top_n=10)
    except Exception:
        logger.exception("Daily digest job failed during pipeline execution")
        return 1

    if result.get("success"):
        logger.info(
            "Daily digest job finished successfully (duration=%.1fs)",
            result.get("duration_seconds", 0),
        )
        return 0

    logger.error(
        "Daily digest job finished without success: %s",
        result.get("error") or result.get("email"),
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
