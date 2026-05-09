import logging
import os
from datetime import datetime
from typing import Optional

from app.load_env import load_project_env

load_project_env()

from app.runner import run_scrapers
from app.services.process_anthropic import process_anthropic_markdown
from app.services.process_youtube import process_youtube_transcripts
from app.services.process_digest import process_digests
from app.services.process_email import send_digest_email

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def default_pipeline_hours() -> int:
    """RSS scrape lookback; override with PIPELINE_HOURS (1–336, default 24)."""
    raw = (os.getenv("PIPELINE_HOURS") or "24").strip()
    try:
        h = int(raw)
    except ValueError:
        return 24
    return max(1, min(h, 24 * 14))


def email_digest_lookback_hours(scrape_hours: int) -> int:
    """How far back to query `digests` for email (`created_at`). Independent of RSS scrape window.

    Default: at least 72 hours so a quiet RSS day can still send digests created earlier.
    Override with EMAIL_DIGEST_HOURS (1–336). Set to match scrape only, e.g. ``24``.
    """
    raw = (os.getenv("EMAIL_DIGEST_HOURS") or "").strip()
    if raw:
        try:
            return max(1, min(int(raw), 24 * 14))
        except ValueError:
            pass
    return max(1, min(max(scrape_hours, 72), 24 * 14))


def run_daily_pipeline(hours: Optional[int] = None, top_n: int = 10) -> dict:
    if hours is None:
        hours = default_pipeline_hours()
    email_hours = email_digest_lookback_hours(hours)
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("Starting Daily AI News Aggregator Pipeline")
    logger.info("=" * 60)
    logger.info(
        "RSS scrape window: last %d hours (PIPELINE_HOURS); digest email DB lookback: last %d hours "
        "(EMAIL_DIGEST_HOURS or default max(scrape, 72))",
        hours,
        email_hours,
    )
    
    results = {
        "start_time": start_time.isoformat(),
        "scraping": {},
        "processing": {},
        "digests": {},
        "email": {},
        "success": False
    }
    
    try:
        logger.info("\n[1/5] Scraping articles from sources...")
        scraping_results = run_scrapers(hours=hours)
        results["scraping"] = {
            "youtube": len(scraping_results.get("youtube", [])),
            "openai": len(scraping_results.get("openai", [])),
            "anthropic": len(scraping_results.get("anthropic", []))
        }
        logger.info(f"✓ Scraped {results['scraping']['youtube']} YouTube videos, "
                    f"{results['scraping']['openai']} OpenAI articles, "
                    f"{results['scraping']['anthropic']} Anthropic articles")
        
        logger.info("\n[2/5] Processing Anthropic markdown...")
        anthropic_result = process_anthropic_markdown()
        results["processing"]["anthropic"] = anthropic_result
        logger.info(f"✓ Processed {anthropic_result['processed']} Anthropic articles "
                    f"({anthropic_result['failed']} failed)")
        
        logger.info("\n[3/5] Processing YouTube transcripts...")
        youtube_result = process_youtube_transcripts()
        results["processing"]["youtube"] = youtube_result
        logger.info(f"✓ Processed {youtube_result['processed']} transcripts "
                    f"({youtube_result['unavailable']} unavailable)")
        
        logger.info("\n[4/5] Creating digests for articles...")
        digest_result = process_digests()
        results["digests"] = digest_result
        logger.info(f"✓ Created {digest_result['processed']} digests "
                    f"({digest_result['failed']} failed out of {digest_result['total']} total)")
        
        logger.info("\n[5/5] Generating and sending email digest...")
        email_result = send_digest_email(hours=email_hours, top_n=top_n)
        results["email"] = email_result
        
        if email_result["success"]:
            results["success"] = True
            if email_result.get("email_sent", True):
                logger.info(
                    "✓ Email sent successfully with %s articles",
                    email_result["articles_count"],
                )
            else:
                logger.info(
                    "✓ Pipeline completed successfully; no email sent (no digest rows in "
                    "last %s hours matching window — %s).",
                    email_result.get("digest_lookback_hours", email_hours),
                    email_result.get("skip_reason", "skipped"),
                )
        else:
            err = email_result.get("error", "Unknown error")
            logger.error("✗ Failed to send email: %s", err)
        
    except Exception as e:
        logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        results["error"] = str(e)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["end_time"] = end_time.isoformat()
    results["duration_seconds"] = duration
    
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Summary")
    logger.info("=" * 60)
    logger.info(f"Duration: {duration:.1f} seconds")
    logger.info(f"Scraped: {results['scraping']}")
    logger.info(f"Processed: {results['processing']}")
    logger.info(f"Digests: {results['digests']}")
    email_line = "Failed"
    em = results.get("email") or {}
    if em.get("success"):
        email_line = "Sent" if em.get("email_sent", True) else f"Skipped — {em.get('skip_reason', 'no content')}"
    logger.info(f"Email: {email_line}")
    logger.info("=" * 60)
    
    return results


if __name__ == "__main__":
    import sys

    h: Optional[int] = None
    top = 10
    if len(sys.argv) > 1:
        h = int(sys.argv[1])
    if len(sys.argv) > 2:
        top = int(sys.argv[2])
    result = run_daily_pipeline(hours=h, top_n=top)
    exit(0 if result["success"] else 1)

