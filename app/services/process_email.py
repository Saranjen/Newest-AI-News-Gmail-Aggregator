import logging
from datetime import datetime
from typing import List, Optional, Tuple

from dotenv import load_dotenv

load_dotenv()

from app.agent.email_agent import EmailAgent, RankedArticleDetail, EmailDigestResponse
from app.agent.curator_agent import CuratorAgent
from app.profiles.user_profile import USER_PROFILE
from app.database.repository import Repository
from app.services.email import digest_to_html, get_digest_recipients, send_email

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Demo/sample digest: widen window until digests exist (24h → 72h → 7d).
DEMO_DIGEST_FALLBACK_HOURS: Tuple[int, ...] = (24, 72, 168)


def _first_word(full_name: str) -> str:
    parts = (full_name or "").strip().split()
    return parts[0] if parts else ""


def _recipient_display_name(rec: dict) -> str:
    fn = (rec.get("first_name") or "").strip()
    if fn:
        return _first_word(fn)
    profile = (USER_PROFILE.get("name") or "").strip()
    return _first_word(profile) or "there"


def _build_ranked_article_details(hours: int) -> Tuple[List[RankedArticleDetail], int]:
    curator = CuratorAgent(USER_PROFILE)
    repo = Repository()

    digests = repo.get_recent_digests(hours=hours)
    total = len(digests)

    if total == 0:
        logger.warning("No digests found from the last %d hours", hours)
        raise ValueError("No digests available")

    logger.info("Ranking %d digests for email generation", total)
    ranked_articles = curator.rank_digests(digests)

    if not ranked_articles:
        logger.error("Failed to rank digests")
        raise ValueError("Failed to rank articles")

    article_details = [
        RankedArticleDetail(
            digest_id=a.digest_id,
            rank=a.rank,
            relevance_score=a.relevance_score,
            reasoning=a.reasoning,
            title=next((d["title"] for d in digests if d["id"] == a.digest_id), ""),
            summary=next((d["summary"] for d in digests if d["id"] == a.digest_id), ""),
            url=next((d["url"] for d in digests if d["id"] == a.digest_id), ""),
            article_type=next((d["article_type"] for d in digests if d["id"] == a.digest_id), ""),
        )
        for a in ranked_articles
    ]
    return article_details, len(ranked_articles)


def build_ranked_article_details_with_fallback(
    hours_sequence: Tuple[int, ...] = DEMO_DIGEST_FALLBACK_HOURS,
) -> Tuple[List[RankedArticleDetail], int, int]:
    """Try successive digest lookback windows until ranked content exists."""
    last_err: Optional[Exception] = None
    for h in hours_sequence:
        try:
            details, total = _build_ranked_article_details(hours=h)
            logger.info("Using digest lookback window: last %d hours", h)
            return details, total, h
        except ValueError as e:
            last_err = e
            logger.info("No ranked digests in last %d hours, widening window...", h)
    raise ValueError(last_err or "No digests available")


def send_sample_digest_email(
    recipient: dict,
    top_n: int = 10,
) -> dict:
    """Send one sample digest (demo). Uses 24h → 72h → 7d fallback for article windows."""
    try:
        article_details, total_ranked, hours_used = build_ranked_article_details_with_fallback()
        email_agent = EmailAgent(USER_PROFILE)
        display = _recipient_display_name(recipient)
        top_articles = article_details[:top_n]
        shared_overview = email_agent.generate_digest_overview(top_articles, limit=top_n)
        intro = email_agent.introduction_for_recipient(display, shared_overview)
        result = EmailDigestResponse(
            introduction=intro,
            articles=top_articles,
            total_ranked=total_ranked,
            top_n=top_n,
        )
        subject = f"Sample AI News Digest - {datetime.now().strftime('%B %d, %Y')}"
        send_email(
            subject=subject,
            body_text=result.to_markdown(),
            body_html=digest_to_html(result),
            recipients=[recipient["email"].strip()],
        )
        return {
            "success": True,
            "subject": subject,
            "articles_count": len(result.articles),
            "digest_hours_used": hours_used,
        }
    except ValueError as e:
        logger.error("Sample digest failed: %s", e)
        return {"success": False, "error": str(e)}


def generate_email_digest(
    hours: int = 24,
    top_n: int = 10,
    recipient_display_name: Optional[str] = None,
) -> EmailDigestResponse:
    """Build one digest email body. If ``recipient_display_name`` is omitted, uses profile name."""
    article_details, total_ranked = _build_ranked_article_details(hours)
    email_agent = EmailAgent(USER_PROFILE)
    name = recipient_display_name
    if name is None:
        profile = (USER_PROFILE.get("name") or "").strip()
        name = _first_word(profile) or "there"
    logger.info("Generating email digest with top %d articles", top_n)
    top_articles = article_details[:top_n]
    overview = email_agent.generate_digest_overview(top_articles, limit=top_n)
    intro = email_agent.introduction_for_recipient(name, overview)
    email_digest = EmailDigestResponse(
        introduction=intro,
        articles=top_articles,
        total_ranked=total_ranked,
        top_n=top_n,
    )
    logger.info("Email digest generated successfully")
    logger.info("\n=== Email Introduction ===")
    logger.info(email_digest.introduction.greeting)
    logger.info("\n%s", email_digest.introduction.introduction)
    return email_digest


def send_digest_email(hours: int = 24, top_n: int = 10) -> dict:
    try:
        article_details, total_ranked = _build_ranked_article_details(hours)
        email_agent = EmailAgent(USER_PROFILE)
        recipients = get_digest_recipients()
        subject = f"Daily AI News Digest - {datetime.now().strftime('%B %d, %Y')}"
        articles_in_digest = 0

        top_articles = article_details[:top_n]
        shared_overview = email_agent.generate_digest_overview(top_articles, limit=top_n)
        logger.info("Generated one shared digest overview for all recipients (single LLM call)")

        for rec in recipients:
            display = _recipient_display_name(rec)
            intro = email_agent.introduction_for_recipient(display, shared_overview)
            result = EmailDigestResponse(
                introduction=intro,
                articles=top_articles,
                total_ranked=total_ranked,
                top_n=top_n,
            )
            markdown_content = result.to_markdown()
            html_content = digest_to_html(result)
            send_email(
                subject=subject,
                body_text=markdown_content,
                body_html=html_content,
                recipients=[rec["email"]],
            )
            logger.info("Sent digest to %s (%s)", rec["email"], display)
            articles_in_digest = len(result.articles)

        logger.info("Email sent successfully to %d recipient(s)", len(recipients))
        return {
            "success": True,
            "subject": subject,
            "articles_count": articles_in_digest,
            "recipients_count": len(recipients),
        }
    except ValueError as e:
        logger.error("Error sending email: %s", e)
        return {
            "success": False,
            "error": str(e),
        }


if __name__ == "__main__":
    result = send_digest_email(hours=24, top_n=10)
    if result["success"]:
        print("\n=== Email Digest Sent ===")
        print(f"Subject: {result['subject']}")
        print(f"Recipients: {result['recipients_count']}")
    else:
        print(f"Error: {result['error']}")
