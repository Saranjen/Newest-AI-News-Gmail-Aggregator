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
| `DATABASE_URL` | Optional. Full Postgres URL (e.g. in GitHub Actions). **If this is set, it overrides all `POSTGRES_*` variables.** |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` | Local Postgres when `DATABASE_URL` is unset or empty |
| `OPENAI_API_KEY` | OpenAI API |
| `EMAIL_SENDER` | Gmail address used to sign in to SMTP |
| `EMAIL_RECIPIENT` | Where to send the digest (if omitted, defaults to the sender address) |
| `GMAIL_APP_PASSWORD` | Gmail app password for SMTP |
| `MY_EMAIL`, `APP_PASSWORD` | Legacy aliases for sender and app password |

Optional: `PROXY_USERNAME`, `PROXY_PASSWORD` for YouTube if you use a proxy.

### After a merge: “it used to email / my DB had articles”

The automation work introduced **`DATABASE_URL`**. If you added it to `.env` for GitHub Actions (e.g. Neon/Supabase) but still run **locally** against Docker Postgres, the app will use **`DATABASE_URL` first** — often an **empty or different** database — so you see **no stored articles**, **no recent digests**, and email can fail even though your old Docker DB still has data.

**Fix for local runs:** remove or comment out `DATABASE_URL` in `.env`, or point it at the same instance you use with Docker. When you run `python -m app.jobs.daily_digest`, the first log line after startup includes **`Database target: host=... db=...`** (no password) so you can confirm which server you hit.

Separately, the email step only loads digests whose **`created_at` is within the last 24 hours**; older digests are ignored. Scrapers only keep items whose **RSS publish time** is inside that same window.

## Automation (GitHub Actions)

The workflow [`.github/workflows/daily-news.yml`](.github/workflows/daily-news.yml) runs **once per day** on a cron schedule (13:00 UTC by default) and can be run **manually** from the Actions tab (**Run workflow**).

### Required GitHub Secrets

In the repository on GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Add:

| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |
| `DATABASE_URL` | Postgres connection string (`postgresql://...` or `postgres://...`) |
| `EMAIL_SENDER` | Gmail address that sends the mail |
| `EMAIL_RECIPIENT` | Inbox that receives the digest |
| `GMAIL_APP_PASSWORD` | Gmail [app password](https://support.google.com/accounts/answer/185833) |

The job installs dependencies from `requirements.txt`, then runs:

```bash
python -m app.jobs.daily_digest
```

Logs in Actions show when the job **starts**, **finishes**, or **fails** (including stack traces on errors).

**Branch:** workflows run from the default branch unless you change the file; merge `Daily_Automation` (or your working branch) into `main`/`master` so the schedule applies to the workflow version you want.
