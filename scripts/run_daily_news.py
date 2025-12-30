#!/usr/bin/env python3
"""
HuggingHugh Daily News Digest Generator

Fetches AI news from RSS feeds, scores for relevance,
and generates a daily blog post digest.

Usage:
    python scripts/run_daily_news.py                    # Generate and deploy
    python scripts/run_daily_news.py --dry-run          # Preview without writing
    python scripts/run_daily_news.py --no-deploy        # Generate but don't deploy
    python scripts/run_daily_news.py --force            # Overwrite existing digest
"""

import argparse
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.news import DigestGenerator, NewsFetcher, RelevanceScorer
from src.reporter.blog import BlogGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(PROJECT_ROOT / "logs" / "news.log"),
    ],
)
logger = logging.getLogger(__name__)


def deploy_blog(output_dir: Path) -> bool:
    """Deploy blog to production servers."""
    try:
        # Copy to both domains
        domains = [
            "/var/www/hugginghugh.com/blog/",
            "/var/www/hugginghugh.etcbin.io/blog/",
        ]

        for domain in domains:
            subprocess.run(
                ["sudo", "cp", "-r"] + list(map(str, output_dir.glob("*"))) + [domain],
                check=True,
            )
            subprocess.run(
                ["sudo", "chown", "-R", "www-data:www-data", domain],
                check=True,
            )

        logger.info("Blog deployed to production")
        return True
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Generate daily AI news digest")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without writing files",
    )
    parser.add_argument(
        "--no-deploy",
        action="store_true",
        help="Generate but don't deploy to production",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing digest for today",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("=" * 60)
    logger.info("HuggingHugh Daily News Digest Generator")
    logger.info("=" * 60)

    # Initialize components
    content_dir = PROJECT_ROOT / "content" / "blog"
    output_dir = PROJECT_ROOT / "output" / "blog"

    fetcher = NewsFetcher()
    scorer = RelevanceScorer()
    digest_gen = DigestGenerator(content_dir=content_dir)

    # Check if digest already exists
    if digest_gen.digest_exists() and not args.force:
        logger.info("Digest already exists for today. Use --force to overwrite.")
        return 0

    # Fetch news
    logger.info("Fetching news from RSS feeds...")
    items = fetcher.fetch_all()
    logger.info(f"Fetched {len(items)} total items")

    if not items:
        logger.error("No items fetched. Check network and RSS feeds.")
        return 1

    # Score and filter
    logger.info("Scoring items for relevance...")
    top_items = scorer.get_top_items(items)
    logger.info(f"Selected {len(top_items)} top items after scoring and filtering")

    if len(top_items) < 3:
        logger.warning("Not enough relevant items for digest (minimum 3)")
        return 1

    # Show preview
    logger.info("\nTop stories for today's digest:")
    for i, item in enumerate(top_items, 1):
        logger.info(f"  {i}. [{item.relevance_score:.0f}] {item.title[:60]}...")
        logger.info(f"     Source: {item.source} | Category: {item.category}")

    # Generate digest
    logger.info("\nGenerating digest...")
    digest_path = digest_gen.generate_digest(top_items, dry_run=args.dry_run)

    if args.dry_run:
        logger.info("[DRY RUN] No files written")
        return 0

    if not digest_path:
        logger.error("Failed to generate digest")
        return 1

    logger.info(f"Digest written to: {digest_path}")

    # Generate blog HTML
    logger.info("\nGenerating blog HTML...")
    blog_gen = BlogGenerator(
        templates_dir=PROJECT_ROOT / "templates",
        content_dir=PROJECT_ROOT / "content",
        output_dir=PROJECT_ROOT / "output",
        base_url="",
    )
    blog_gen.generate_all()
    logger.info(f"Blog HTML generated in: {output_dir}")

    # Deploy
    if not args.no_deploy:
        logger.info("\nDeploying to production...")
        if deploy_blog(output_dir):
            logger.info("Deployment successful!")
        else:
            logger.error("Deployment failed")
            return 1
    else:
        logger.info("[NO DEPLOY] Skipping production deployment")

    logger.info("\n" + "=" * 60)
    logger.info("Daily news digest generation complete!")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
