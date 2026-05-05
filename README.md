# AI News Gmail Aggregator

Scrapes AI news sources, stores articles in Postgres, generates digests with OpenAI, and emails a daily summary.

## Local setup

1. Install dependencies (e.g. `uv sync` from `pyproject.toml`, or `pip install -r requirements.txt`).
2. Copy [`.env.example`](.env.example) to `.env` and fill in secrets: `cp .env.example .env`
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

The workflow [`.github/workflows/daily-news.yml`](.github/workflows/daily-news.yml) runs **once per day** at **13:00 UTC** (`cron: "0 13 * * *"`) and supports **manual** runs. It runs `pip install -r requirements.txt` then `python -m app.jobs.daily_digest`.

### Setting it up (checklist)

1. **Put the workflow on your default branch**  
   GitHub only runs `schedule` from **`main`** or **`master`** (whatever is default). Merge or push so `.github/workflows/daily-news.yml` exists on that branch.

2. **Create hosted Postgres** (GitHub cannot use `localhost` on your laptop)  
   Use something like [Neon](https://neon.tech), [Supabase](https://supabase.com), [Railway](https://railway.app), or [Render](https://render.com/docs/postgresql) and create a database. Copy the **connection URI** (usually `postgresql://` or `postgres://`).  
   - If the provider requires TLS, append **`?sslmode=require`** to the URL if their docs say so.  
   - Allow **connections from the internet** (not “localhost only”). Many free tiers allow all IPs by default.

3. **Add repository secrets**  
   On GitHub: **Settings → Secrets and variables → Actions → New repository secret**. Create each name **exactly** as below (names are case-sensitive):

| Secret | What to paste |
|--------|----------------|
| `OPENAI_API_KEY` | Your OpenAI API key |
| `DATABASE_URL` | The **hosted** Postgres URI (not `localhost`) |
| `EMAIL_SENDER` | Gmail address used to sign in to SMTP |
| `EMAIL_RECIPIENT` | Address that should receive the digest |
| `GMAIL_APP_PASSWORD` | Gmail [app password](https://support.google.com/accounts/answer/185833) for `EMAIL_SENDER` |

Your laptop **`.env` is not used** in Actions; only these secrets (and the workflow `env` block) apply.

4. **Smoke-test with a manual run**  
   **Actions → “Daily news digest” → Run workflow →** choose your **default** branch → **Run workflow**. Open the run → **digest** → **Run daily digest** and read the log. Fix any connection or auth errors before relying on the schedule.

5. **Scheduled runs**  
   After a successful manual run, the same workflow will run daily on the cron above. There can be small delays around the scheduled minute; that is normal on GitHub.

**Note:** The Actions database is **separate** from local Docker. Data does not sync unless you migrate or point both at the same cloud DB on purpose. The job creates tables if missing (`create_all` in the digest entrypoint).

### Optional workflow tweaks

- Change schedule: edit `cron` in [`.github/workflows/daily-news.yml`](.github/workflows/daily-news.yml) (times are **UTC**).  
- RSS lookback in CI: the workflow sets `PIPELINE_HOURS: "72"`; adjust or remove in the YAML if you want different behavior.
