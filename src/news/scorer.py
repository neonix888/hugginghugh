"""
Relevance Scorer for AI News

Scores news items based on relevance to AI security topics.
"""

import logging
import re
from difflib import SequenceMatcher
from pathlib import Path
from typing import Optional

import yaml

from .fetcher import NewsItem

logger = logging.getLogger(__name__)


class RelevanceScorer:
    """Scores news items for relevance to AI security."""

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize relevance scorer.

        Args:
            config_path: Path to news_sources.yaml config file
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "news_sources.yaml"

        self.config_path = config_path
        self.config = self._load_config()
        self.keywords = self.config.get("keywords", {})
        self.settings = self.config.get("settings", {})

        # Build keyword patterns for efficient matching
        self._build_patterns()

    def _load_config(self) -> dict:
        """Load configuration from YAML file."""
        try:
            with open(self.config_path) as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"keywords": {}, "settings": {}}

    def _build_patterns(self):
        """Build regex patterns for keyword matching."""
        self.patterns = {}

        for priority, keywords in self.keywords.items():
            if keywords:
                # Create case-insensitive pattern for each keyword
                pattern_str = "|".join(r"\b" + re.escape(kw.lower()) + r"\b" for kw in keywords)
                self.patterns[priority] = re.compile(pattern_str, re.IGNORECASE)

    def _calculate_text_score(self, text: str) -> float:
        """Calculate relevance score based on keyword matches."""
        if not text:
            return 0.0

        score = 0.0
        text_lower = text.lower()

        # High priority keywords (+15 each)
        if "high_priority" in self.patterns:
            matches = self.patterns["high_priority"].findall(text_lower)
            score += len(set(matches)) * 15

        # Medium priority keywords (+8 each)
        if "medium_priority" in self.patterns:
            matches = self.patterns["medium_priority"].findall(text_lower)
            score += len(set(matches)) * 8

        # Low priority keywords (+3 each)
        if "low_priority" in self.patterns:
            matches = self.patterns["low_priority"].findall(text_lower)
            score += len(set(matches)) * 3

        return score

    def score_item(self, item: NewsItem) -> float:
        """
        Calculate relevance score for a news item.

        Args:
            item: NewsItem to score

        Returns:
            Relevance score (higher = more relevant)
        """
        # Base score from source priority
        score = item.priority * 2

        # Score from title (weighted more heavily)
        title_score = self._calculate_text_score(item.title) * 2
        score += title_score

        # Score from summary
        summary_score = self._calculate_text_score(item.summary)
        score += summary_score

        # Bonus for security-focused sources
        if item.category == "security":
            score += 10

        # Bonus for HuggingFace-specific content
        if item.category == "huggingface":
            score += 15

        # Recency bonus (items from last 24 hours get +5)
        from datetime import datetime, timedelta, timezone

        if item.published > datetime.now(timezone.utc) - timedelta(hours=24):
            score += 5

        return score

    def score_items(self, items: list[NewsItem]) -> list[NewsItem]:
        """
        Score all items and update their relevance_score.

        Args:
            items: List of NewsItem objects

        Returns:
            Same list with updated relevance_score fields
        """
        for item in items:
            item.relevance_score = self.score_item(item)

        return items

    def filter_by_score(
        self, items: list[NewsItem], min_score: Optional[float] = None
    ) -> list[NewsItem]:
        """
        Filter items by minimum relevance score.

        Args:
            items: List of NewsItem objects
            min_score: Minimum score (uses config default if None)

        Returns:
            Filtered list
        """
        if min_score is None:
            min_score = self.settings.get("min_relevance_score", 10)

        return [item for item in items if item.relevance_score >= min_score]

    def deduplicate(
        self, items: list[NewsItem], similarity_threshold: Optional[float] = None
    ) -> list[NewsItem]:
        """
        Remove duplicate items based on title similarity.

        Args:
            items: List of NewsItem objects
            similarity_threshold: Similarity threshold (0-1)

        Returns:
            Deduplicated list
        """
        if similarity_threshold is None:
            similarity_threshold = self.settings.get("dedupe_similarity", 0.7)

        if not items:
            return []

        # Sort by score (highest first) so we keep the best version
        sorted_items = sorted(items, key=lambda x: x.relevance_score, reverse=True)
        unique_items = []

        for item in sorted_items:
            is_duplicate = False
            for existing in unique_items:
                similarity = SequenceMatcher(
                    None, item.title.lower(), existing.title.lower()
                ).ratio()
                if similarity >= similarity_threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)

        return unique_items

    def get_top_items(
        self,
        items: list[NewsItem],
        max_items: Optional[int] = None,
        deduplicate: bool = True,
        filter_low_score: bool = True,
    ) -> list[NewsItem]:
        """
        Get top scored items after filtering and deduplication.

        Args:
            items: List of NewsItem objects
            max_items: Maximum items to return
            deduplicate: Whether to remove duplicates
            filter_low_score: Whether to filter by minimum score

        Returns:
            Top items sorted by relevance
        """
        if max_items is None:
            max_items = self.settings.get("max_stories_per_digest", 8)

        # Score all items
        scored_items = self.score_items(items)

        # Filter by minimum score
        if filter_low_score:
            scored_items = self.filter_by_score(scored_items)

        # Deduplicate
        if deduplicate:
            scored_items = self.deduplicate(scored_items)

        # Sort by relevance score (descending)
        sorted_items = sorted(scored_items, key=lambda x: x.relevance_score, reverse=True)

        return sorted_items[:max_items]
