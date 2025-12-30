"""
RSS Feed Fetcher for AI News

Fetches news from configured RSS feeds with caching and error handling.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import feedparser
import yaml

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """Represents a single news item."""

    title: str
    url: str
    source: str
    category: str
    published: datetime
    summary: str = ""
    priority: int = 5
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "url": self.url,
            "source": self.source,
            "category": self.category,
            "published": self.published.isoformat(),
            "summary": self.summary,
            "priority": self.priority,
            "relevance_score": self.relevance_score,
        }


@dataclass
class FetchResult:
    """Result of fetching from a single source."""

    source_name: str
    items: list = field(default_factory=list)
    error: Optional[str] = None
    fetch_time: float = 0.0


class NewsFetcher:
    """Fetches news from multiple RSS sources."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize news fetcher.

        Args:
            config_path: Path to news_sources.yaml config file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "news_sources.yaml"

        self.config_path = config_path
        self.config = self._load_config()
        self.sources = self.config.get("sources", [])
        self.settings = self.config.get("settings", {})

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"sources": [], "keywords": {}, "settings": {}}

    def _parse_date(self, entry: dict) -> datetime:
        """Parse date from feed entry."""
        # Try different date fields
        for date_field in ["published_parsed", "updated_parsed", "created_parsed"]:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    import time

                    parsed = getattr(entry, date_field)
                    return datetime(*parsed[:6], tzinfo=timezone.utc)
                except Exception:
                    pass

        # Try string parsing
        for date_field in ["published", "updated", "created"]:
            if hasattr(entry, date_field) and getattr(entry, date_field):
                try:
                    from email.utils import parsedate_to_datetime

                    return parsedate_to_datetime(getattr(entry, date_field))
                except Exception:
                    pass

        # Default to now
        return datetime.now(timezone.utc)

    def _fetch_single_source(self, source: dict) -> FetchResult:
        """Fetch news from a single RSS source."""
        import time

        start_time = time.time()

        source_name = source.get("name", "Unknown")
        url = source.get("url", "")
        priority = source.get("priority", 5)
        category = source.get("category", "general")

        result = FetchResult(source_name=source_name)

        try:
            feed = feedparser.parse(url)

            if feed.bozo and not feed.entries:
                result.error = f"Feed error: {feed.bozo_exception}"
                logger.warning(f"Error fetching {source_name}: {result.error}")
                return result

            max_age = timedelta(hours=self.settings.get("max_age_hours", 48))
            cutoff_time = datetime.now(timezone.utc) - max_age

            for entry in feed.entries:
                try:
                    published = self._parse_date(entry)

                    # Skip old entries
                    if published < cutoff_time:
                        continue

                    # Get summary
                    summary = ""
                    if hasattr(entry, "summary"):
                        summary = entry.summary
                    elif hasattr(entry, "description"):
                        summary = entry.description

                    # Clean HTML from summary
                    import re

                    summary = re.sub(r"<[^>]+>", "", summary)
                    summary = summary[:500] if len(summary) > 500 else summary

                    item = NewsItem(
                        title=entry.get("title", "Untitled"),
                        url=entry.get("link", ""),
                        source=source_name,
                        category=category,
                        published=published,
                        summary=summary.strip(),
                        priority=priority,
                    )
                    result.items.append(item)

                except Exception as e:
                    logger.debug(f"Error parsing entry from {source_name}: {e}")
                    continue

            result.fetch_time = time.time() - start_time
            logger.info(
                f"Fetched {len(result.items)} items from {source_name} in {result.fetch_time:.2f}s"
            )

        except Exception as e:
            result.error = str(e)
            logger.error(f"Failed to fetch {source_name}: {e}")

        return result

    def fetch_all(self, max_workers: int = 5) -> list[NewsItem]:
        """
        Fetch news from all configured sources.

        Args:
            max_workers: Maximum parallel fetches

        Returns:
            List of NewsItem objects
        """
        all_items = []

        logger.info(f"Fetching from {len(self.sources)} sources...")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._fetch_single_source, source): source
                for source in self.sources
            }

            for future in as_completed(futures):
                result = future.result()
                if result.items:
                    all_items.extend(result.items)

        logger.info(f"Total items fetched: {len(all_items)}")
        return all_items

    def fetch_by_category(self, category: str) -> list[NewsItem]:
        """Fetch news from sources in a specific category."""
        filtered_sources = [s for s in self.sources if s.get("category") == category]
        original_sources = self.sources
        self.sources = filtered_sources

        try:
            items = self.fetch_all()
        finally:
            self.sources = original_sources

        return items
