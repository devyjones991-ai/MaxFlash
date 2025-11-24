"""
Sentiment analysis module for crypto market news.
Fetches news from RSS feeds and calculates sentiment polarity.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import feedparser
from textblob import TextBlob

from utils.logger_config import setup_logging

logger = setup_logging()


class SentimentAnalyzer:
    """
    Analyzes market sentiment using news RSS feeds and TextBlob.
    """

    def __init__(self):
        """Initialize SentimentAnalyzer with default feeds."""
        self.feeds = [
            "https://cointelegraph.com/rss",
            "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "https://cryptopotato.com/feed/",
            "https://news.bitcoin.com/feed/",
        ]
        self.keywords = {
            "BTC": ["bitcoin", "btc"],
            "ETH": ["ethereum", "eth"],
            "SOL": ["solana", "sol"],
            "XRP": ["ripple", "xrp"],
            "BNB": ["binance coin", "bnb"],
        }
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = timedelta(minutes=15)
        self.last_update = datetime.min

    async def fetch_news(self) -> List[Dict[str, Any]]:
        """
        Fetch news from all configured RSS feeds.

        Returns:
            List of news items with title, link, summary, and published date.
        """
        news_items = []

        # Check cache first (simple in-memory cache for now)
        if datetime.now() - self.last_update < self.cache_ttl and "all_news" in self.cache:
            return self.cache["all_news"]

        logger.info(f"Fetching news from {len(self.feeds)} sources...")

        for url in self.feeds:
            try:
                # feedparser is synchronous, so we run it in a thread if needed,
                # but for this scale direct call is usually fine or we can wrap in to_thread
                feed = await asyncio.to_thread(feedparser.parse, url)

                for entry in feed.entries[:10]:  # Top 10 per feed
                    published = self._parse_date(entry)

                    # Filter old news (> 24h)
                    if datetime.now() - published > timedelta(hours=24):
                        continue

                    news_items.append(
                        {
                            "title": entry.title,
                            "summary": getattr(entry, "summary", ""),
                            "link": entry.link,
                            "published": published,
                            "source": feed.feed.get("title", "Unknown"),
                        }
                    )
            except Exception as e:
                logger.error(f"Error fetching feed {url}: {e}")

        # Deduplicate by title
        unique_news = {item["title"]: item for item in news_items}.values()
        sorted_news = sorted(unique_news, key=lambda x: x["published"], reverse=True)

        self.cache["all_news"] = list(sorted_news)
        self.last_update = datetime.now()

        logger.info(f"Fetched {len(sorted_news)} unique news items")
        return list(sorted_news)

    def _parse_date(self, entry: Any) -> datetime:
        """Parse feedparser date to datetime."""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        return datetime.now()

    def analyze_text(self, text: str) -> float:
        """
        Analyze sentiment of a text string.

        Returns:
            Polarity score between -1.0 (negative) and 1.0 (positive).
        """
        blob = TextBlob(text)
        return blob.sentiment.polarity

    async def get_sentiment_for_symbol(self, symbol: str) -> Dict[str, Any]:
        """
        Calculate sentiment score for a specific symbol.

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')

        Returns:
            Dictionary with score, label, and relevant news count.
        """
        base_currency = symbol.split("/")[0].upper()
        target_keywords = self.keywords.get(base_currency, [base_currency.lower()])

        news = await self.fetch_news()
        relevant_news = []
        total_score = 0.0

        for item in news:
            text = f"{item['title']} {item['summary']}".lower()
            if any(k in text for k in target_keywords):
                score = self.analyze_text(text)
                # Weight recent news more heavily? For now, flat weight.
                total_score += score
                item["sentiment"] = score
                relevant_news.append(item)

        count = len(relevant_news)
        avg_score = total_score / count if count > 0 else 0.0

        # Normalize score to 0-100 scale for easier UI display?
        # Or keep -1 to 1. Let's keep -1 to 1 for logic.

        if avg_score > 0.1:
            label = "POSITIVE"
        elif avg_score < -0.1:
            label = "NEGATIVE"
        else:
            label = "NEUTRAL"

        return {
            "score": avg_score,
            "label": label,
            "news_count": count,
            "top_news": relevant_news[:3],  # Return top 3 relevant articles
        }

    async def get_market_sentiment(self) -> Dict[str, Any]:
        """
        Calculate overall market sentiment.
        """
        news = await self.fetch_news()
        if not news:
            return {"score": 0, "label": "NEUTRAL"}

        total_score = sum(self.analyze_text(f"{item['title']} {item['summary']}") for item in news)
        avg_score = total_score / len(news)

        if avg_score > 0.1:
            label = "BULLISH"
        elif avg_score < -0.1:
            label = "BEARISH"
        else:
            label = "NEUTRAL"

        return {"score": avg_score, "label": label, "news_count": len(news)}
