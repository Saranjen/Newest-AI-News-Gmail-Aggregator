# AI News Gmail Aggregator

Scrapes AI news sources, stores articles in Postgres, generates digests with OpenAI, and emails a daily summary.

## Local setup

1. Install dependencies (e.g. `uv sync` from `pyproject.toml`, or `pip install -r requirements.txt`).
2. Copy or create a `.env` in the repo root with your Postgres and API settings (see below).
3. Create tables: `python app/database/create_tables.py`
4. Run the pipeline once: `python main.py`  
   Or use the automation entrypoint: `python -m app.jobs.daily_digest`

## Environment variables

| Variable | Purpose |
|----------|---------|
| `DATABASE_URL` | Full Postgres URL. Used **on GitHub Actions** (where `GITHUB_ACTIONS=true`) or locally only if **`USE_DATABASE_URL=true`**. Otherwise ignored in favor of `POSTGRES_*`. |
| `USE_DATABASE_URL` | Set to `true` on your machine if you want `DATABASE_URL` instead of `POSTGRES_*` for local runs. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` | Default for **local** runs (e.g. Docker on `localhost`) |
| `OPENAI_API_KEY` | OpenAI API |
| `EMAIL_SENDER` | Gmail address used to sign in to SMTP |
| `EMAIL_RECIPIENT` | Where to send the digest (if omitted, defaults to the sender address) |
| `GMAIL_APP_PASSWORD` | Gmail app password for SMTP |
| `MY_EMAIL`, `APP_PASSWORD` | Legacy aliases for sender and app password |
| `PIPELINE_HOURS` | RSS scrape lookback (default **24** hours, max **336**). Only affects which feed items are considered new. |
| `EMAIL_DIGEST_HOURS` | How far back the **email** step queries the **`digests`** table (`created_at`). If unset, defaults to **max(`PIPELINE_HOURS`, 72)** so a day with no new RSS can still email digests from the last few days. Set **`24`** to match a strict 24h digest-only window. |

Optional: `PROXY_USERNAME`, `PROXY_PASSWORD` for YouTube if you use a proxy.

**Local vs cloud:** You can keep `DATABASE_URL` in `.env` (for reference or for Actions) while using Docker: local runs use **`POSTGRES_*`** unless you set `USE_DATABASE_URL=true`. The digest job logs **`Database target: host=... db=...`** so you can confirm which database is used.

The pipeline **always** runs the email step and queries the digest table; scrape emptiness does not skip that. RSS items must fall inside **`PIPELINE_HOURS`** to be scraped; existing digest rows must fall inside the **email lookback** above to be included in the mail.

## Automation (GitHub Actions)

The workflow [`.github/workflows/daily-news.yml`](.github/workflows/daily-news.yml) runs **once per day** on a cron schedule (13:00 UTC by default) and can be run **manually** from the Actions tab (**Run workflow**).

### Required GitHub Secrets

In the repository on GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | Hosted Postgres URL (must be reachable from the internet). GitHub sets `GITHUB_ACTIONS`, so this URL is picked automatically in the workflow. |
| `EMAIL_SENDER` | Gmail address that sends the mail |
| `EMAIL_RECIPIENT` | Inbox that receives the digest |
| `GMAIL_APP_PASSWORD` | Gmail [app password](https://support.google.com/accounts/answer/185833) |

The job installs dependencies from `requirements.txt`, then runs:

```bash
python -m app.jobs.daily_digest
```

Logs in Actions show when the job **starts**, **finishes**, or **fails** (including stack traces on errors).

**Branch:** workflows run from the default branch unless you change the file; merge `Daily_Automation` (or your working branch) into `main`/`master` so the schedule applies to the workflow version you want.
