#!/usr/bin/env python3
"""
HuggingHugh Twitter Bot - Standalone Script

Posts tweets about model trust scores manually.

Usage:
    python scripts/tweet.py --daily          # Post daily summary
    python scripts/tweet.py --tip            # Post a random tip
    python scripts/tweet.py --spotlight      # Spotlight a Grade A model
    python scripts/tweet.py --dry-run        # Show tweets without posting

Environment Variables Required:
    TWITTER_API_KEY
    TWITTER_API_SECRET
    TWITTER_ACCESS_TOKEN
    TWITTER_ACCESS_TOKEN_SECRET
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.social.twitter_bot import TwitterBot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def load_models_data() -> list:
    """Load models data from the API JSON file."""
    api_json = PROJECT_ROOT / "output" / "api" / "models.json"
    if not api_json.exists():
        logger.error(f"Models data not found: {api_json}")
        logger.error("Run a scan first: python scripts/run_daily_scan.py")
        return []

    data = json.loads(api_json.read_text())
    return data.get("models", [])


def load_leaderboard_data() -> list:
    """Load leaderboard data from the database."""
    try:
        from src.database import LeaderboardDB

        with LeaderboardDB() as db:
            return db.get_full_leaderboard()
    except Exception as e:
        logger.warning(f"Could not load leaderboard: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(
        description="HuggingHugh Twitter Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Tweet type (mutually exclusive)
    tweet_group = parser.add_mutually_exclusive_group(required=True)
    tweet_group.add_argument("--daily", action="store_true", help="Post daily summary tweet")
    tweet_group.add_argument("--tip", action="store_true", help="Post a random security tip")
    tweet_group.add_argument(
        "--spotlight", action="store_true", help="Spotlight a random Grade A model"
    )
    tweet_group.add_argument("--custom", type=str, metavar="TEXT", help="Post a custom tweet")
    tweet_group.add_argument("--test", action="store_true", help="Test Twitter API connection")

    parser.add_argument("--dry-run", action="store_true", help="Show tweet without posting")

    args = parser.parse_args()

    # Initialize bot
    bot = TwitterBot(dry_run=args.dry_run)

    if not bot.is_configured() and not args.dry_run:
        logger.error("Twitter API credentials not configured")
        logger.error("Set the following environment variables:")
        logger.error("  TWITTER_API_KEY")
        logger.error("  TWITTER_API_SECRET")
        logger.error("  TWITTER_ACCESS_TOKEN")
        logger.error("  TWITTER_ACCESS_TOKEN_SECRET")
        return 1

    # Test connection
    if args.test:
        logger.info("Testing Twitter API connection...")
        client = bot._get_client()
        if client:
            try:
                me = client.get_me()
                if me.data:
                    logger.info(f"Connected as: @{me.data.username}")
                    return 0
            except Exception as e:
                logger.error(f"Connection test failed: {e}")
                return 1
        else:
            logger.error("Failed to create Twitter client")
            return 1

    # Load data
    models_data = load_models_data()
    if not models_data and not args.custom and not args.tip:
        return 1

    # Post tweet based on type
    if args.daily:
        if not models_data:
            logger.error("No models data for daily summary")
            return 1
        leaderboard = load_leaderboard_data()
        tweets_posted = bot.run_daily_tweets(models_data, leaderboard)
        logger.info(f"Posted {tweets_posted} tweets")

    elif args.tip:
        content = bot.generate_tip_tweet()
        if bot.post_tweet(content):
            logger.info("Tip tweet posted")
        else:
            logger.error("Failed to post tip tweet")
            return 1

    elif args.spotlight:
        # Try Grade A first, fall back to Grade B
        grade_a = [m for m in models_data if m.get("trust_grade") == "A"]
        if not grade_a:
            logger.info("No Grade A models, trying Grade B...")
            grade_a = [m for m in models_data if m.get("trust_grade") == "B"]
        if not grade_a:
            logger.error("No Grade A or B models found")
            return 1
        import random

        model = random.choice(grade_a)
        content = bot.generate_grade_a_spotlight_tweet(model)
        if bot.post_tweet(content):
            logger.info(f"Spotlight tweet posted for {model.get('model_id')}")
        else:
            logger.error("Failed to post spotlight tweet")
            return 1

    elif args.custom:
        from src.social.twitter_bot import TweetContent

        content = TweetContent(text=args.custom, tweet_type="custom")
        if bot.post_tweet(content):
            logger.info("Custom tweet posted")
        else:
            logger.error("Failed to post custom tweet")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
