"""HTTP API for subscriber signup + sample digest.

Locally, serves the Vite-built SPA from ``static/``. On Vercel, the SPA is built to ``app/spa_dist/`` so files exist inside the serverless bundle; ``StaticFiles`` mounts them at ``/`` (API routes above still win).

Run API (repo root): ``uvicorn app.api.server:app --reload --host 127.0.0.1 --port 8000``

Develop UI with hot reload (proxies to API): ``cd frontend && npm install && npm run dev``
Then open Vite’s URL (e.g. http://127.0.0.1:5173). Production bundle: ``cd frontend && npm run build`` (writes to ``static/`` locally, ``app/spa_dist/`` when ``VERCEL`` is set).
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from app.database.repository import Repository
from app.load_env import load_project_env
from app.services.process_email import send_sample_digest_email

load_project_env()

REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "static"
PUBLIC_DIR = REPO_ROOT / "public"
SPA_DIST_DIR = REPO_ROOT / "app" / "spa_dist"


def _is_vercel_runtime() -> bool:
    return os.getenv("VERCEL", "").strip().lower() in ("1", "true", "yes")


def _spa_mount_directory() -> Path | None:
    """Directory containing Vite ``index.html`` + ``assets/`` for StaticFiles."""
    if _is_vercel_runtime():
        if SPA_DIST_DIR.is_dir():
            return SPA_DIST_DIR
        if PUBLIC_DIR.is_dir():
            return PUBLIC_DIR
        return None
    if STATIC_DIR.is_dir():
        return STATIC_DIR
    return None


class SubscriberBody(BaseModel):
    email: EmailStr
    first_name: str = Field(default="", max_length=200)
    last_name: str = Field(default="", max_length=200)


app = FastAPI(title="AI News Digest", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/subscribe")
def subscribe(body: SubscriberBody):
    """Subscribe email to the daily digest (upsert)."""
    try:
        Repository().upsert_subscriber_subscribe(
            email=str(body.email),
            first_name=body.first_name or None,
            last_name=body.last_name or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"ok": True, "message": "You're subscribed to the daily digest."}


@app.post("/demo")
def demo(body: SubscriberBody):
    """Record demo request and send one sample digest email immediately."""
    try:
        Repository().upsert_subscriber_demo_request(
            email=str(body.email),
            first_name=body.first_name or None,
            last_name=body.last_name or None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    recipient = {
        "email": str(body.email),
        "first_name": body.first_name or None,
        "last_name": body.last_name or None,
    }
    result = send_sample_digest_email(recipient)
    if not result.get("success"):
        raise HTTPException(
            status_code=503,
            detail=result.get("error") or "Could not generate sample digest.",
        )
    return {
        "ok": True,
        "message": "Sample digest sent — check your inbox.",
        "digest_hours_used": result.get("digest_hours_used"),
    }


# SPA: API routes above take precedence; mount serves ``/`` and hashed assets.
_site_dir = _spa_mount_directory()
if _site_dir is not None:
    app.mount("/", StaticFiles(directory=str(_site_dir), html=True), name="site")
