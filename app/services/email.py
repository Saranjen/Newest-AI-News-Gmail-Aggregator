import os
import smtplib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import markdown

from app.load_env import load_project_env

load_project_env()


def _smtp_sender() -> str:
    for key in ("EMAIL_SENDER", "MY_EMAIL"):
        v = (os.getenv(key) or "").strip()
        if v:
            return v
    return ""


def _smtp_password() -> str:
    return (os.getenv("GMAIL_APP_PASSWORD") or os.getenv("APP_PASSWORD") or "").strip()


def _default_recipients() -> list[str]:
    explicit = (os.getenv("EMAIL_RECIPIENT") or "").strip()
    if explicit:
        return [p.strip() for p in explicit.split(",") if p.strip()]
    sender = _smtp_sender()
    if sender:
        return [sender]
    raise ValueError("Set EMAIL_RECIPIENT or EMAIL_SENDER/MY_EMAIL for recipients")


def _recipients_from_env_digest_fallback() -> list[dict]:
    raw = (os.getenv("EMAIL_RECIPIENT") or "").strip()
    if not raw:
        return []
    fn = (os.getenv("DIGEST_FALLBACK_FIRST_NAME") or "").strip() or None
    ln = (os.getenv("DIGEST_FALLBACK_LAST_NAME") or "").strip() or None
    return [
        {"email": p.strip(), "first_name": fn, "last_name": ln}
        for p in raw.split(",")
        if p.strip()
    ]


def get_digest_recipients() -> list[dict]:
    """Resolve digest recipients: ``subscribers`` with ``is_subscribed`` first, then legacy ``digest_recipients``, then ``EMAIL_RECIPIENT``.

    Each item is ``{"email": str, "first_name": str | None, "last_name": str | None}``.
    Env: ``DIGEST_USE_SUBSCRIBERS_TABLE`` (default true), ``DIGEST_RECIPIENTS_FROM_DB`` for legacy table,
    ``DIGEST_FALLBACK_FIRST_NAME`` / ``DIGEST_FALLBACK_LAST_NAME`` for env-only recipients.
    """
    use_subscribers = os.getenv("DIGEST_USE_SUBSCRIBERS_TABLE", "true").lower() in ("1", "true", "yes")
    rows: list[dict] = []
    if use_subscribers:
        try:
            from app.database.repository import Repository

            rows = Repository().get_subscribed_subscribers()
        except Exception:
            rows = []
    use_legacy = os.getenv("DIGEST_RECIPIENTS_FROM_DB", "true").lower() in ("1", "true", "yes")
    if not rows and use_legacy:
        try:
            from app.database.repository import Repository

            rows = Repository().get_active_digest_recipients()
        except Exception:
            rows = []
    if not rows:
        rows = _recipients_from_env_digest_fallback()
    if not rows:
        raise ValueError(
            "No digest recipients: subscribe via /subscribe or add rows to subscribers / digest_recipients "
            "or set EMAIL_RECIPIENT (comma-separated)."
        )
    return rows


def send_email(subject: str, body_text: str, body_html: str = None, recipients: list = None):
    sender = _smtp_sender()
    password = _smtp_password()
    if not sender:
        raise ValueError("EMAIL_SENDER or MY_EMAIL must be set")
    if not password:
        raise ValueError("GMAIL_APP_PASSWORD or APP_PASSWORD must be set")

    if recipients is None:
        recipients = _default_recipients()

    recipients = [r for r in recipients if r is not None]
    if not recipients:
        raise ValueError("No valid recipients provided")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(sender, password)
        for to_addr in recipients:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = to_addr

            part1 = MIMEText(body_text, "plain")
            msg.attach(part1)

            if body_html:
                part2 = MIMEText(body_html, "html")
                msg.attach(part2)

            smtp.sendmail(sender, [to_addr], msg.as_string())


def markdown_to_html(markdown_text: str) -> str:
    html = markdown.markdown(markdown_text, extensions=['extra', 'nl2br'])
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        h2 {{
            font-size: 18px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 24px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        p {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        strong {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        em {{
            font-style: italic;
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }}
        .introduction {{
            color: #4a4a4a;
            margin-bottom: 20px;
        }}
        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }}
    </style>
</head>
<body>
{html}
</body>
</html>"""


def digest_to_html(digest_response) -> str:
    from app.agent.email_agent import EmailDigestResponse
    
    if not isinstance(digest_response, EmailDigestResponse):
        return markdown_to_html(digest_response.to_markdown() if hasattr(digest_response, 'to_markdown') else str(digest_response))
    
    html_parts = []
    greeting_html = markdown.markdown(digest_response.introduction.greeting, extensions=['extra', 'nl2br'])
    introduction_html = markdown.markdown(digest_response.introduction.introduction, extensions=['extra', 'nl2br'])
    html_parts.append(f'<div class="greeting">{greeting_html}</div>')
    html_parts.append(f'<div class="introduction">{introduction_html}</div>')
    html_parts.append('<hr>')
    
    for article in digest_response.articles:
        html_parts.append(f'<h3>{html.escape(article.title)}</h3>')
        summary_html = markdown.markdown(article.summary, extensions=['extra', 'nl2br'])
        html_parts.append(f'<div>{summary_html}</div>')
        html_parts.append(f'<p><a href="{html.escape(article.url)}" class="article-link">Read more →</a></p>')
        html_parts.append('<hr>')
    
    html_content = '\n'.join(html_parts)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        h3 {{
            font-size: 16px;
            font-weight: 600;
            color: #1a1a1a;
            margin-top: 20px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        p {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        strong {{
            font-weight: 600;
            color: #1a1a1a;
        }}
        em {{
            font-style: italic;
            color: #666;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e5e5e5;
            margin: 20px 0;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 500;
            color: #1a1a1a;
            margin-bottom: 12px;
        }}
        .introduction {{
            color: #4a4a4a;
            margin-bottom: 20px;
        }}
        .article-link {{
            display: inline-block;
            margin-top: 8px;
            color: #0066cc;
            font-size: 14px;
        }}
        .greeting p {{
            margin: 0;
        }}
        .introduction p {{
            margin: 0;
        }}
        div {{
            margin: 8px 0;
            color: #4a4a4a;
        }}
        div p {{
            margin: 4px 0;
        }}
    </style>
</head>
<body>
{html_content}
</body>
</html>"""


def send_email_to_self(subject: str, body: str):
    send_email(subject, body, recipients=_default_recipients())


if __name__ == "__main__":
    send_email_to_self("Test from Python", "Hello from my script.")