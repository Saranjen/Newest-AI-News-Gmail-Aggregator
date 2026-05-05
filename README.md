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
| `DATABASE_URL` | Optional. Full Postgres URL (e.g. in GitHub Actions). If unset, `POSTGRES_*` is used. |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB` | Local Postgres when `DATABASE_URL` is not set |
| `OPENAI_API_KEY` | OpenAI API |
| `EMAIL_SENDER` | Gmail address used to sign in to SMTP |
| `EMAIL_RECIPIENT` | Where to send the digest (if omitted, defaults to the sender address) |
| `GMAIL_APP_PASSWORD` | Gmail app password for SMTP |
| `MY_EMAIL`, `APP_PASSWORD` | Legacy aliases for sender and app password |

Optional: `PROXY_USERNAME`, `PROXY_PASSWORD` for YouTube if you use a proxy.

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
