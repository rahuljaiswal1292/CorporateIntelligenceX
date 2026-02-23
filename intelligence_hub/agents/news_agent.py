"""
News Aggregation Agent

Autonomous agent for fetching recent news articles about the company.
Includes integrated news fetching and parsing logic.
"""

import json
import feedparser
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from typing import Dict, Optional, Callable, List

from .base_agent import BaseAgent
from intelligence_hub.graph.state import AgentState
from intelligence_hub.llm.connector import LLMConnector
from intelligence_hub.storage.corporate_profile_store import (
    CorporateProfileStore,
)
from intelligence_hub.prompts import load_prompt
from langchain_core.prompts import (
    ChatPromptTemplate,
)


class NewsAgent(BaseAgent):
    """Agent for news aggregation"""

    def __init__(
        self,
        company_name: str,
        llm_connector: LLMConnector,
        log_callback: Optional[Callable] = None,
        profile_store: Optional[CorporateProfileStore] = None,
    ):
        super().__init__(
            agent_name="News Agent",
            company_name=company_name,
            llm_connector=llm_connector,
            log_callback=log_callback,
            profile_store=profile_store,
        )

    def should_execute(self, state: AgentState) -> tuple[bool, str]:
        """
        Decide if news aggregation should run

        Args:
            state: Shared agent state

        Returns:
            (should_run, reasoning)
        """
        basic_profile = state.get("enrichments", {})

        # Load decision prompt
        decision_prompt = load_prompt("agent_news_decision.txt")

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", decision_prompt),
                (
                    "user",
                    "Analyze this company profile and decide if news aggregation should be performed:\n\n{profile_json}",
                ),
            ]
        )

        # Invoke LLM for decision
        chain = prompt | self.llm_connector.llm
        response = chain.invoke({"profile_json": json.dumps(basic_profile, indent=2)})

        # Parse decision
        try:
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            decision = json.loads(content.strip())
            should_run = decision.get("should_execute", False)
            reasoning = decision.get(
                "reasoning",
                "No reasoning provided",
            )

            return (should_run, reasoning)

        except Exception as e:
            self.log(
                f"Decision parsing failed: {e}, defaulting to SKIP",
                "WARNING",
            )
            return (False, f"Decision error: {e}")

    def _fetch_recent_news(
        self,
        company_name: str,
        max_articles: int = 10,
        days_back: int = 15,
    ) -> Dict:
        """
        Fetch recent news from Google News RSS

        Args:
            company_name: Company name to search
            max_articles: Maximum number of articles to return
            days_back: Days of history to search

        Returns:
            Dict with articles and metadata
        """
        result = {
            "articles": [],
            "total_found": 0,
            "query": company_name,
            "error": None,
        }

        try:
            # Build Google News RSS URL
            query = quote_plus(company_name)
            rss_url = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"

            self.log(f"Fetching news feed for: {company_name}")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)

            if not feed.entries:
                self.log(
                    "No news articles found",
                    "WARNING",
                )
                result["error"] = "No articles found"
                return result

            # Calculate date threshold
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Process entries
            articles = []
            for entry in feed.entries:
                # Parse published date
                published_date = None
                if hasattr(entry, "published_parsed"):
                    try:
                        published_date = datetime(*entry.published_parsed[:6])
                    except:
                        pass

                # Filter by date if available
                if published_date and published_date < cutoff_date:
                    continue

                # Extract article data
                article = {
                    "title": entry.get("title", ""),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "source": self._extract_source(entry),
                    "summary": entry.get("summary", ""),
                }

                articles.append(article)

                if len(articles) >= max_articles:
                    break

            result["articles"] = articles
            result["total_found"] = len(articles)

            self.log(f"Found {len(articles)} recent articles")

        except Exception as e:
            self.log(f"News fetch failed: {e}", "ERROR")
            result["error"] = str(e)

        return result

    def _extract_source(self, entry) -> str:
        """Extract source from RSS entry"""
        # Try to extract from source tag
        if hasattr(entry, "source") and hasattr(entry.source, "title"):
            return entry.source.title

        # Try to extract from title
        title = entry.get("title", "")
        if " - " in title:
            parts = title.split(" - ")
            return parts[-1]

        return "Unknown"

    def execute(self, state: AgentState) -> Dict:
        """
        Execute news aggregation

        Args:
            context: Context with basic profile

        Returns:
            Result with news data
        """
        basic_profile = state.get("enrichments", {})
        canonical_name = (
            basic_profile.get("canonical_name")
            or state.get("company_name")
            or self.company_name
            or "Unknown"
        )

        self.log("PROGRESS:0:Starting news search")
        self.log(f"Fetching recent news for: {canonical_name}")

        try:
            self.log("PROGRESS:30:Searching Google News")
            # Fetch news data
            news_data = self._fetch_recent_news(canonical_name)

            self.log("PROGRESS:70:Retrieved news articles")

            if news_data.get("error"):
                self.log(
                    f"News aggregation failed: {news_data['error']}",
                    "WARNING",
                )
                return {
                    "data": None,
                    "document_type": "news",
                    "metadata": {"error": news_data["error"]},
                }

            self.log(f"Found {len(news_data['articles'])} news articles")

            self.log("PROGRESS:90:Processing news data")

            enrichment = {
                "canonical_name": canonical_name,
                "articles": news_data["articles"],
                "total_articles": len(news_data["articles"]),
            }

            self.log("PROGRESS:100:News search complete")
            return {
                "data": enrichment,
                "document_type": "news",
                "metadata": {
                    "source": "google_news",
                    "article_count": len(news_data["articles"]),
                },
            }

        except Exception as e:
            self.log(
                f"News execution error: {e}",
                "ERROR",
            )
            raise
