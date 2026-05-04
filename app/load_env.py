"""Load `.env` from the repository root regardless of current working directory."""
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_project_env() -> None:
    load_dotenv(REPO_ROOT / ".env")
