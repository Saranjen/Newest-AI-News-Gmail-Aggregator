import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.load_env import load_project_env

load_project_env()


def get_database_url() -> str:
    """Resolve DB URL.

    - **Local (default):** use `POSTGRES_*` even if `DATABASE_URL` is in `.env`, so a
      cloud URL copied for GitHub docs does not override Docker Postgres.
    - **GitHub Actions:** `GITHUB_ACTIONS=true` → use `DATABASE_URL` when set.
    - **Vercel:** `VERCEL=1` → use `DATABASE_URL` when set.
    - **Force URL locally:** set `USE_DATABASE_URL=true` to use `DATABASE_URL`.
    """
    url = (os.getenv("DATABASE_URL") or "").strip()
    in_github_actions = os.getenv("GITHUB_ACTIONS", "").lower() == "true"
    on_vercel = os.getenv("VERCEL", "").lower() == "1"
    use_database_url = os.getenv("USE_DATABASE_URL", "").lower() in ("1", "true", "yes")
    if url and (in_github_actions or use_database_url or on_vercel):
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    # Match docker compose default host port when .env is missing
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "ai_news_aggregator")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

engine = create_engine(get_database_url())
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    return SessionLocal()

