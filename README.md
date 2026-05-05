# AI News Gmail Aggregator

A Python pipeline that collects AI-related **YouTube videos**, **OpenAI news articles**, and **Anthropic-linked articles** from public feeds, stores them in **PostgreSQL**, generates short **LLM digests**, ranks content for relevance, and sends a **daily HTML email** digest via **Gmail**.

---

## What it does

1. **Scrape** — Pulls recent items from configured sources within a time window (`PIPELINE_HOURS`, default 24 hours).
2. **Persist** — Writes normalized rows into Postgres (videos, OpenAI posts, Anthropic posts).
3. **Enrich** — Fetches **Anthropic** page content as markdown (Docling), and **YouTube** captions where available (`youtube-transcript-api`, optional proxy).
4. **Digest** — Uses an **OpenAI**-backed agent to summarize eligible articles into digest records.
5. **Email** — Uses another **OpenAI**-backed flow to curate and format a ranked **Gmail** digest (plain + HTML).

Entry points:

- `python main.py` — same pipeline; optional CLI args `[hours] [top_n]`.
- `python -m app.jobs.daily_digest` — intended for **cron / GitHub Actions** (ensures schema, then runs the full pipeline).

---

## Design intention

- **Single daily artifact** — One pass produces one coherent email instead of ad-hoc notifications.
- **Separation of concerns** — Scrapers only fetch and filter by time; processing steps prepare text; digest and email logic stay in dedicated services and agents.
- **Durable state** — Postgres is the source of truth so reruns, partial failures, and automation all see the same history.
- **Configurable windows** — RSS scrape lookback and digest-email lookback can differ (`PIPELINE_HOURS`, `EMAIL_DIGEST_HOURS`) so a quiet feed day does not automatically mean “no email” if recent digests already exist.
- **Automation-friendly** — The job is a **one-shot CLI** suitable for GitHub Actions: install deps, set secrets, run the module; no long-running server required.

---

## Content sources

### YouTube

- Channels are listed in [`app/config.py`](app/config.py) as **`YOUTUBE_CHANNELS`** (YouTube channel IDs). As shipped, the active channel is **Matthew Berman** (`UCawZsQWqfGSbCI5yjkdVkTA`); **Dave Ebbelaar**’s channel ID is in the same list but commented out—uncomment or add more IDs to scrape additional channels.
- Each channel is read via YouTube’s **public RSS** (`feeds/videos.xml?channel_id=…`).
- Recent uploads (within the scrape window, excluding Shorts in the scraper logic) are stored; **transcripts** are fetched with **`youtube-transcript-api`** when available. Optional **`PROXY_USERNAME` / `PROXY_PASSWORD`** enable a Webshare-style proxy for transcript calls if your network requires it.

### OpenAI

- Articles come from OpenAI’s official **news RSS** (`https://openai.com/news/rss.xml`), filtered by publish time within the same scrape window.

### Anthropic

- Items are loaded from **community-maintained RSS mirrors** (see [`app/scrapers/anthropic.py`](app/scrapers/anthropic.py)): news, research, and engineering feeds hosted on GitHub (`Olshansk/rss-feeds`), then deduplicated by GUID.
- Full-page **markdown** for digest generation is produced with **Docling** (`DocumentConverter`) from article URLs where conversion succeeds.

---

## Technology stack

| Layer | Choice |
|--------|--------|
| Language | **Python 3.12+** |
| Data store | **PostgreSQL** |
| ORM / DB access | **SQLAlchemy 2.x** + **psycopg2-binary** |
| LLM | **OpenAI** API (`openai` Python SDK) |
| Email | **Gmail** over **SMTP** (TLS), app passwords |
| Automation | **GitHub Actions** (`ubuntu-latest`, cron + `workflow_dispatch`) |
| Local DB | **Docker Compose** (see [`docker/docker-compose.yml`](docker/docker-compose.yml); default host port **5433**) |

---

## Main libraries

Declared in [`pyproject.toml`](pyproject.toml) (and mirrored in [`requirements.txt`](requirements.txt) for CI):

| Library | Role |
|---------|------|
| **feedparser** | RSS/Atom parsing for YouTube, OpenAI, and Anthropic feeds |
| **youtube-transcript-api** | YouTube caption fetch (optional Webshare proxy) |
| **requests** | HTTP client where needed across scrapers and tooling |
| **beautifulsoup4** / **markdownify** | HTML/XML handling and conversion helpers |
| **docling** | URL → document → markdown for Anthropic (and OpenAI scraper wiring) |
| **openai** | Chat/completions for digest, curation, and email agents |
| **pydantic** | Structured models for scraper outputs and agent payloads |
| **sqlalchemy** | Models, sessions, queries |
| **psycopg2-binary** | Postgres driver |
| **python-dotenv** | Load `.env` from repo root |
| **markdown** | Render digest content to HTML for email |

---

## Local setup

1. Install dependencies: `uv sync` (from `pyproject.toml`) or `pip install -r requirements.txt`.
2. Copy [`.env.example`](.env.example) to `.env` and fill in values: `cp .env.example .env`
3. Start Postgres (e.g. `docker compose -f docker/docker-compose.yml up -d`).
4. Create tables: `python app/database/create_tables.py`
5. Run the pipeline: `python main.py` or `python -m app.jobs.daily_digest`

---

## Environment variables

### `.env` (local)

Use a `.env` file in the repo root (see [`.env.example`](.env.example)). Typical keys:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for digest, curation, and email agents. |
| `MY_EMAIL` | Gmail address used as SMTP login and default “from” / recipient when `EMAIL_RECIPIENT` is unset. |
| `APP_PASSWORD` | Gmail [app password](https://support.google.com/accounts/answer/185833) for `MY_EMAIL`. |
| `DATABASE_URL` | Full Postgres URI. **Locally:** only used if `USE_DATABASE_URL=true` (otherwise ignored in favor of `POSTGRES_*`). **On GitHub Actions:** set as a secret; `GITHUB_ACTIONS=true` enables this URL. |
| `USE_DATABASE_URL` | Set to `true` to connect using `DATABASE_URL` on your machine; omit or `false` to use `POSTGRES_*` only. |
| `POSTGRES_USER` | Postgres user (e.g. `postgres`). |
| `POSTGRES_PASSWORD` | Postgres password. |
| `POSTGRES_DB` | Database name (e.g. `ai_news_aggregator`). |
| `POSTGRES_HOST` | Host (e.g. `localhost`). |
| `POSTGRES_PORT` | Host port; this repo’s Docker Compose defaults to **5433** on the host. |

The digest job logs **`Database target: host=... db=...`** (no password) so you can confirm which database is used.

**Alternative Gmail names (optional):** you can use `EMAIL_SENDER`, `EMAIL_RECIPIENT`, and `GMAIL_APP_PASSWORD` instead of / in addition to `MY_EMAIL` / `APP_PASSWORD`; the app prefers the `EMAIL_*` names when both are set. The **GitHub Actions** workflow uses the `EMAIL_*` / `GMAIL_APP_PASSWORD` secret names—set those in the repo to match, or align your secrets with what the workflow expects.

### Optional

| Variable | Purpose |
|----------|---------|
| `PIPELINE_HOURS` | RSS scrape lookback (default **24**, max **336**). |
| `EMAIL_DIGEST_HOURS` | Digest rows considered for email (`created_at`). Default: **max(`PIPELINE_HOURS`, 72)** unless set. |
| `PROXY_USERNAME`, `PROXY_PASSWORD` | Optional Webshare-style proxy for YouTube transcripts. |

---

## Automation (GitHub Actions)

**Idea:** Run **PostgreSQL** on a host reachable from the internet (Neon, Supabase, Railway, Render, or your own). Copy the provider’s **connection string** and store it as the **`DATABASE_URL` secret** in GitHub, together with OpenAI and Gmail secrets. The workflow [`.github/workflows/daily-news.yml`](.github/workflows/daily-news.yml) runs **once per day** at **13:00 UTC** by default (`cron: "0 13 * * *"`) and executes `python -m app.jobs.daily_digest`, so **digest generation and email run automatically** on that schedule without your laptop.

The workflow runs `pip install -r requirements.txt` then the digest module, and supports **Run workflow** (manual) from the Actions tab.

### Setting it up (checklist)

1. **Default branch** — Ensure `.github/workflows/daily-news.yml` exists on **`main`/`master`** (GitHub’s `schedule` trigger only uses the default branch).
2. **Hosted Postgres** — Create a database; copy the URI (`postgresql://` or `postgres://`). Use **`?sslmode=require`** if the provider requires TLS. Allow inbound from the internet where applicable.
3. **Repository secrets** — **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | What to paste |
|--------|----------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | Hosted Postgres URI (**not** `localhost` on your Mac) |
| `EMAIL_SENDER` | Gmail sender |
| `EMAIL_RECIPIENT` | Digest recipient |
| `GMAIL_APP_PASSWORD` | Gmail [app password](https://support.google.com/accounts/answer/185833) |

Actions **does not** read your local `.env`.

4. **Smoke test** — **Actions → Daily news digest → Run workflow** on the default branch; inspect logs for the **digest** job.
5. **Schedule** — After a green manual run, cron runs daily; small schedule drift is normal on GitHub.

The Actions database is **separate** from local Docker unless you point both at the same URL on purpose. The digest entrypoint runs **`create_all`** so missing tables are created on first run.

### Optional workflow tweaks

- Edit **`cron`** in [`.github/workflows/daily-news.yml`](.github/workflows/daily-news.yml) for a different **UTC** time.
- The workflow sets **`PIPELINE_HOURS: "72"`** for RSS lookback in CI; change or remove in YAML if you prefer.

---

## Project layout (high level)

- `app/scrapers/` — YouTube, OpenAI, Anthropic RSS ingestion  
- `app/database/` — SQLAlchemy models, connection, repository  
- `app/services/` — Markdown/transcript processing, digest generation, email send  
- `app/agent/` — OpenAI-backed agents (digest, curation, email)  
- `app/daily_runner.py` — Orchestrates the five pipeline stages  
- `app/jobs/daily_digest.py` — Automation entrypoint  
- `.github/workflows/` — Scheduled GitHub Actions workflow  

---

## Disclaimer

This project reads **public** RSS feeds and third-party feed mirrors; follow each provider’s terms, robots guidance, and rate limits. For Gmail, use an account with **2-Step Verification** and an **[app password](https://support.google.com/accounts/answer/185833)** for SMTP, per Google’s current requirements.
