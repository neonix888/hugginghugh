"""
Digest Generator for AI News

Generates blog posts from curated news items.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from .fetcher import NewsItem

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Generates daily news digest blog posts."""

    def __init__(self, content_dir: Optional[Path] = None):
        """
        Initialize digest generator.

        Args:
            content_dir: Path to blog content directory
        """
        if content_dir is None:
            content_dir = Path(__file__).parent.parent.parent / "content" / "blog"

        self.content_dir = content_dir
        self.content_dir.mkdir(parents=True, exist_ok=True)

    def _format_date(self, dt: datetime) -> str:
        """Format datetime for display."""
        return dt.strftime("%B %d, %Y")

    def _generate_slug(self, date: datetime) -> str:
        """Generate URL slug for digest."""
        return f"ai-news-digest-{date.strftime('%Y-%m-%d')}"

    def _categorize_items(self, items: list[NewsItem]) -> dict[str, list[NewsItem]]:
        """Group items by category."""
        categories = {}
        for item in items:
            cat = item.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        return categories

    def _generate_intro(self, items: list[NewsItem], date: datetime) -> str:
        """Generate intro paragraph based on content."""
        security_count = sum(1 for i in items if i.category == "security")
        research_count = sum(1 for i in items if i.category == "research")

        intro = f"Here's your daily roundup of the most relevant AI and ML news for {self._format_date(date)}. "

        if security_count > 0:
            intro += f"Today's digest includes {security_count} security-focused {'story' if security_count == 1 else 'stories'}. "

        if research_count > 0:
            intro += f"We're also covering {research_count} research {'development' if research_count == 1 else 'developments'}. "

        intro += "Click through to read the full articles from our curated sources."

        return intro

    def _generate_story_section(self, item: NewsItem, index: int) -> str:
        """Generate markdown section for a single story."""
        section = f"### {index}. {item.title}\n\n"

        if item.summary:
            # Clean and truncate summary
            summary = item.summary.strip()
            if len(summary) > 300:
                summary = summary[:297] + "..."
            section += f"{summary}\n\n"

        section += f"**Source:** [{item.source}]({item.url})"

        # Add time ago
        from datetime import timezone

        now = datetime.now(timezone.utc)
        hours_ago = (now - item.published).total_seconds() / 3600
        if hours_ago < 1:
            time_str = "just now"
        elif hours_ago < 24:
            time_str = f"{int(hours_ago)} hours ago"
        else:
            days = int(hours_ago / 24)
            time_str = f"{days} {'day' if days == 1 else 'days'} ago"

        section += f" | *{time_str}*\n\n"

        return section

    def generate_digest(
        self,
        items: list[NewsItem],
        date: Optional[datetime] = None,
        dry_run: bool = False,
    ) -> Optional[Path]:
        """
        Generate a daily digest blog post.

        Args:
            items: Curated list of NewsItem objects
            date: Date for the digest (defaults to today)
            dry_run: If True, don't write file

        Returns:
            Path to generated file, or None if not enough items
        """
        if date is None:
            date = datetime.now()

        if len(items) < 3:
            logger.warning(f"Not enough items for digest: {len(items)} (minimum 3)")
            return None

        slug = self._generate_slug(date)
        title = f"AI News Digest: {self._format_date(date)}"

        # Generate frontmatter
        frontmatter = f"""---
title: "{title}"
slug: {slug}
date: {date.strftime('%Y-%m-%d')}
category: News Digest
excerpt: "Daily roundup of AI and ML news - {len(items)} curated stories on security, research, and industry developments."
read_time: {max(3, len(items))}
---
"""

        # Generate intro
        content = self._generate_intro(items, date) + "\n\n"

        # Categorize items
        categories = self._categorize_items(items)

        # Category display order and labels
        category_labels = {
            "security": "Security & Safety",
            "huggingface": "HuggingFace & Models",
            "research": "Research & Papers",
            "industry": "Industry News",
            "tech": "Tech & Development",
            "general": "Other News",
        }

        category_order = ["security", "huggingface", "research", "industry", "tech", "general"]

        # Generate sections by category
        story_index = 1
        for cat in category_order:
            if cat in categories and categories[cat]:
                cat_items = categories[cat]
                content += f"## {category_labels.get(cat, cat.title())}\n\n"

                for item in cat_items:
                    content += self._generate_story_section(item, story_index)
                    story_index += 1

        # Add footer
        content += """---

## About This Digest

This digest is automatically curated from leading AI and tech news sources, filtered for relevance to AI security and the ML ecosystem. Stories are scored and ranked based on their relevance to model security, supply chain safety, and the broader AI landscape.

Want to see how your favorite models score on security? Check our [model dashboard](/) for trust scores on the top 500 HuggingFace models.
"""

        # Combine frontmatter and content
        full_content = frontmatter + "\n" + content

        if dry_run:
            logger.info(f"[DRY RUN] Would generate digest: {slug}")
            logger.info(f"Title: {title}")
            logger.info(f"Stories: {len(items)}")
            return None

        # Write file
        output_path = self.content_dir / f"{slug}.md"
        with open(output_path, "w") as f:
            f.write(full_content)

        logger.info(f"Generated digest: {output_path}")
        return output_path

    def digest_exists(self, date: Optional[datetime] = None) -> bool:
        """Check if a digest already exists for the given date."""
        if date is None:
            date = datetime.now()

        slug = self._generate_slug(date)
        return (self.content_dir / f"{slug}.md").exists()
