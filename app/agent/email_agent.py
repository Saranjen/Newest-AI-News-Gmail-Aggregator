import os
from datetime import datetime
from typing import List, Optional
from openai import OpenAI
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class EmailIntroduction(BaseModel):
    greeting: str = Field(description="Personalized greeting with user's name and date")
    introduction: str = Field(description="2-3 sentence overview of what's in the top 10 ranked articles")


class RankedArticleDetail(BaseModel):
    digest_id: str
    rank: int
    relevance_score: float
    title: str
    summary: str
    url: str
    article_type: str
    reasoning: Optional[str] = None


class EmailDigestResponse(BaseModel):
    introduction: EmailIntroduction
    articles: List[RankedArticleDetail]
    total_ranked: int
    top_n: int
    
    def to_markdown(self) -> str:
        markdown = f"{self.introduction.greeting}\n\n"
        markdown += f"{self.introduction.introduction}\n\n"
        markdown += "---\n\n"
        
        for article in self.articles:
            markdown += f"## {article.title}\n\n"
            markdown += f"{article.summary}\n\n"
            markdown += f"[Read more →]({article.url})\n\n"
            markdown += "---\n\n"
        
        return markdown


class EmailDigest(BaseModel):
    introduction: EmailIntroduction
    ranked_articles: List[dict] = Field(description="Top 10 ranked articles with their details")


class DigestOverviewBody(BaseModel):
    overview: str = Field(
        description="2-3 sentence neutral overview of the ranked articles only; no greeting, no reader name"
    )


OVERVIEW_PROMPT = """You write the middle section of a daily AI newsletter.

Write exactly one short paragraph (2-3 sentences) that previews the themes of the articles listed.
- Do not greet the reader or use anyone's name.
- Do not say "In today's digest" unless it reads naturally; focus on substance.
- Professional, clear, engaging tone.

The email software will add a separate greeting line with the reader's first name and the date."""


class EmailAgent:
    def __init__(self, user_profile: dict):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o-mini"
        self.user_profile = user_profile

    @staticmethod
    def _article_summaries_block(ranked_articles: List, max_items: int) -> str:
        top = ranked_articles[:max_items]
        lines = []
        for idx, article in enumerate(top):
            title = article.title if hasattr(article, "title") else article.get("title", "N/A")
            score = (
                article.relevance_score
                if hasattr(article, "relevance_score")
                else article.get("relevance_score", 0)
            )
            lines.append(f"{idx + 1}. {title} (Score: {float(score):.1f}/10)")
        return "\n".join(lines)

    def generate_digest_overview(self, ranked_articles: List, limit: int = 10) -> str:
        """One LLM call per run: shared paragraph for all recipients that day."""
        if not ranked_articles:
            return "No articles were ranked today."
        article_summaries = self._article_summaries_block(ranked_articles, limit)
        user_prompt = f"""Ranked articles for today's digest:

{article_summaries}

Write only the overview paragraph as instructed."""

        try:
            response = self.client.responses.parse(
                model=self.model,
                instructions=OVERVIEW_PROMPT,
                temperature=0.55,
                input=user_prompt,
                text_format=DigestOverviewBody,
            )
            parsed = response.output_parsed
            return (parsed.overview if parsed else "").strip() or (
                "Here are today's top AI news picks ranked for relevance."
            )
        except Exception as e:
            print(f"Error generating digest overview: {e}")
            return "Here are today's top AI news articles ranked by relevance to your interests."

    def introduction_for_recipient(self, first_name: str, overview_paragraph: str) -> EmailIntroduction:
        """No LLM: templated greeting + shared overview (saves tokens when mailing many people)."""
        raw = (first_name or "there").strip() or "there"
        name = raw.split()[0] if raw.split() else "there"
        current_date = datetime.now().strftime("%B %d, %Y")
        return EmailIntroduction(
            greeting=f"Hey {name}, here is your daily digest of AI news for {current_date}.",
            introduction=overview_paragraph,
        )

    def create_email_digest(
        self,
        ranked_articles: List[dict],
        limit: int = 10,
        recipient_display_name: Optional[str] = None,
    ) -> EmailDigest:
        top_articles = ranked_articles[:limit]
        overview = self.generate_digest_overview(top_articles, limit=limit)
        raw = (recipient_display_name or self.user_profile.get("name") or "there").strip() or "there"
        name = raw.split()[0] if raw.split() else "there"
        introduction = self.introduction_for_recipient(name, overview)

        return EmailDigest(introduction=introduction, ranked_articles=top_articles)

    def create_email_digest_response(
        self,
        ranked_articles: List[RankedArticleDetail],
        total_ranked: int,
        limit: int = 10,
        recipient_display_name: Optional[str] = None,
        shared_overview: Optional[str] = None,
    ) -> EmailDigestResponse:
        top_articles = ranked_articles[:limit]
        overview = (
            shared_overview
            if shared_overview is not None
            else self.generate_digest_overview(top_articles, limit=limit)
        )
        raw = (recipient_display_name or self.user_profile.get("name") or "there").strip() or "there"
        name = raw.split()[0] if raw.split() else "there"
        introduction = self.introduction_for_recipient(name, overview)

        return EmailDigestResponse(
            introduction=introduction,
            articles=top_articles,
            total_ranked=total_ranked,
            top_n=limit,
        )

