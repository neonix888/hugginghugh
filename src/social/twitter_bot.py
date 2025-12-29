"""
Twitter Bot for HuggingHugh.

Posts automated tweets about model trust scores, leaderboard changes,
and security alerts.

Requires Twitter API v2 credentials set as environment variables:
- TWITTER_API_KEY
- TWITTER_API_SECRET
- TWITTER_ACCESS_TOKEN
- TWITTER_ACCESS_TOKEN_SECRET
"""

import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Tweet templates
TEMPLATES = {
    "daily_summary": [
        "Daily scan complete: {total} models analyzed\n\n"
        "Top performer: {top_model} ({top_grade} {top_score})\n"
        "Avg trust score: {avg_score}\n"
        "Models with critical vulns: {critical_count}\n\n"
        "Full dashboard: https://hugginghugh.com",
        "HuggingHugh scanned {total} AI models today\n\n"
        "Leader: {top_model}\n"
        "Grade: {top_grade} | Score: {top_score}/100\n\n"
        "Check your favorite model: https://hugginghugh.com",
    ],
    "new_leader": [
        "New #1 on the HuggingHugh Leaderboard!\n\n"
        "{model_id} takes the top spot\n"
        "Trust Score: {score}/100 ({grade})\n\n"
        "See the full leaderboard: https://hugginghugh.com/leaderboard.html",
        "Leaderboard shake-up!\n\n"
        "{model_id} is now the most trusted model\n"
        "Score: {score} | Grade: {grade}\n\n"
        "https://hugginghugh.com/leaderboard.html",
    ],
    "score_improvement": [
        "Score improvement alert!\n\n"
        "{model_id} improved from {old_score} to {new_score}\n"
        "New grade: {grade}\n\n"
        "Report: https://hugginghugh.com/reports/{safe_id}/",
        "{model_id} leveled up!\n\n"
        "Trust score: {old_score} -> {new_score} (+{delta})\n"
        "Grade: {grade}\n\n"
        "https://hugginghugh.com/reports/{safe_id}/",
    ],
    "security_alert": [
        "Security Alert\n\n"
        "{model_id} has {critical} critical and {high} high severity vulnerabilities\n\n"
        "Review before using in production:\n"
        "https://hugginghugh.com/reports/{safe_id}/",
        "Vulnerability found in popular model\n\n"
        "{model_id}\n"
        "Critical: {critical} | High: {high}\n\n"
        "Full report: https://hugginghugh.com/reports/{safe_id}/",
    ],
    "grade_a_highlight": [
        "Grade A Model Spotlight\n\n"
        "{model_id}\n"
        "Trust Score: {score}/100\n"
        "Downloads: {downloads}\n\n"
        "SafeTensors | Verified Publisher | No Critical CVEs\n\n"
        "https://hugginghugh.com/reports/{safe_id}/",
    ],
    "weekly_stats": [
        "Weekly HuggingHugh Stats\n\n"
        "Models scanned: {total}\n"
        "Grade A models: {grade_a}\n"
        "Grade F models: {grade_f}\n"
        "Total vulnerabilities found: {total_vulns}\n\n"
        "https://hugginghugh.com",
    ],
    "tip": [
        "AI Security Tip\n\n"
        "Always check for SafeTensors format before downloading models. "
        "Pickle files can execute arbitrary code!\n\n"
        "Learn more: https://hugginghugh.com/blog/pickle-files-hidden-danger.html",
        "Did you know?\n\n"
        "HuggingHugh generates free SBOMs for the top 1000 HuggingFace models.\n\n"
        "Check your model's security posture:\n"
        "https://hugginghugh.com",
        "Before deploying an AI model, ask:\n\n"
        "- Does it use SafeTensors?\n"
        "- Any known CVEs in dependencies?\n"
        "- What's the license?\n\n"
        "We answer these for 1000+ models:\n"
        "https://hugginghugh.com",
    ],
}


@dataclass
class TweetContent:
    """Represents a tweet to be posted."""

    text: str
    tweet_type: str
    model_id: Optional[str] = None
    metadata: Optional[dict] = None


class TwitterBot:
    """
    Twitter bot for HuggingHugh announcements.

    Posts tweets about model trust scores, leaderboard changes,
    and security findings.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        dry_run: bool = False,
    ):
        """
        Initialize Twitter bot.

        Args:
            api_key: Twitter API key (or set TWITTER_API_KEY env var)
            api_secret: Twitter API secret (or set TWITTER_API_SECRET env var)
            access_token: Twitter access token (or set TWITTER_ACCESS_TOKEN env var)
            access_token_secret: Twitter access token secret (or set TWITTER_ACCESS_TOKEN_SECRET env var)
            dry_run: If True, don't actually post tweets
        """
        self.api_key = api_key or os.environ.get("TWITTER_API_KEY")
        self.api_secret = api_secret or os.environ.get("TWITTER_API_SECRET")
        self.access_token = access_token or os.environ.get("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = access_token_secret or os.environ.get(
            "TWITTER_ACCESS_TOKEN_SECRET"
        )
        self.dry_run = dry_run
        self.client = None

        # Track posted tweets to avoid duplicates
        self.posted_today: list[str] = []

    def is_configured(self) -> bool:
        """Check if Twitter credentials are configured."""
        return all(
            [
                self.api_key,
                self.api_secret,
                self.access_token,
                self.access_token_secret,
            ]
        )

    def _get_client(self):
        """Get or create Twitter API client."""
        if self.client is not None:
            return self.client

        if not self.is_configured():
            logger.warning("Twitter API credentials not configured")
            return None

        try:
            import tweepy

            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret,
            )
            logger.info("Twitter client initialized")
            return self.client

        except ImportError:
            logger.error("tweepy not installed. Run: pip install tweepy")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            return None

    def _format_number(self, num: int) -> str:
        """Format large numbers with K/M suffix."""
        if num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)

    def _select_template(self, tweet_type: str) -> str:
        """Select a random template for the given tweet type."""
        templates = TEMPLATES.get(tweet_type, [])
        if not templates:
            raise ValueError(f"Unknown tweet type: {tweet_type}")
        return random.choice(templates)

    def generate_daily_summary(
        self,
        models_data: list[dict[str, Any]],
    ) -> TweetContent:
        """
        Generate a daily summary tweet.

        Args:
            models_data: List of model scan results

        Returns:
            TweetContent for the daily summary
        """
        # Calculate stats
        total = len(models_data)
        scores = [m.get("trust_score", 0) for m in models_data]
        avg_score = round(sum(scores) / len(scores)) if scores else 0

        critical_count = sum(
            1
            for m in models_data
            if m.get("vulnerabilities", {}).get("summary", {}).get("critical", 0) > 0
        )

        # Find top performer
        top_model = max(models_data, key=lambda x: x.get("trust_score", 0))

        template = self._select_template("daily_summary")
        text = template.format(
            total=total,
            top_model=top_model.get("model_id", "Unknown"),
            top_grade=top_model.get("trust_grade", "?"),
            top_score=top_model.get("trust_score", 0),
            avg_score=avg_score,
            critical_count=critical_count,
        )

        return TweetContent(
            text=text,
            tweet_type="daily_summary",
            metadata={"total": total, "avg_score": avg_score},
        )

    def generate_new_leader_tweet(
        self,
        model_id: str,
        score: int,
        grade: str,
    ) -> TweetContent:
        """Generate a tweet for a new leaderboard leader."""
        template = self._select_template("new_leader")
        text = template.format(
            model_id=model_id,
            score=score,
            grade=grade,
        )

        return TweetContent(
            text=text,
            tweet_type="new_leader",
            model_id=model_id,
        )

    def generate_score_improvement_tweet(
        self,
        model_id: str,
        old_score: int,
        new_score: int,
        grade: str,
    ) -> TweetContent:
        """Generate a tweet for a significant score improvement."""
        safe_id = model_id.replace("/", "_")
        delta = new_score - old_score

        template = self._select_template("score_improvement")
        text = template.format(
            model_id=model_id,
            old_score=old_score,
            new_score=new_score,
            delta=delta,
            grade=grade,
            safe_id=safe_id,
        )

        return TweetContent(
            text=text,
            tweet_type="score_improvement",
            model_id=model_id,
        )

    def generate_security_alert_tweet(
        self,
        model_id: str,
        critical: int,
        high: int,
    ) -> TweetContent:
        """Generate a security alert tweet."""
        safe_id = model_id.replace("/", "_")

        template = self._select_template("security_alert")
        text = template.format(
            model_id=model_id,
            critical=critical,
            high=high,
            safe_id=safe_id,
        )

        return TweetContent(
            text=text,
            tweet_type="security_alert",
            model_id=model_id,
        )

    def generate_grade_a_spotlight_tweet(
        self,
        model_data: dict[str, Any],
    ) -> TweetContent:
        """Generate a spotlight tweet for a Grade A model."""
        model_id = model_data.get("model_id", "Unknown")
        safe_id = model_id.replace("/", "_")

        template = self._select_template("grade_a_highlight")
        text = template.format(
            model_id=model_id,
            score=model_data.get("trust_score", 0),
            downloads=self._format_number(model_data.get("downloads", 0)),
            safe_id=safe_id,
        )

        return TweetContent(
            text=text,
            tweet_type="grade_a_highlight",
            model_id=model_id,
        )

    def generate_tip_tweet(self) -> TweetContent:
        """Generate a random security tip tweet."""
        template = self._select_template("tip")
        return TweetContent(
            text=template,
            tweet_type="tip",
        )

    def post_tweet(self, content: TweetContent) -> bool:
        """
        Post a tweet.

        Args:
            content: TweetContent to post

        Returns:
            True if posted successfully, False otherwise
        """
        # Check for duplicates
        if content.text in self.posted_today:
            logger.info(f"Skipping duplicate tweet: {content.tweet_type}")
            return False

        if self.dry_run:
            logger.info(f"[DRY RUN] Would post tweet ({content.tweet_type}):")
            logger.info(f"  {content.text[:100]}...")
            self.posted_today.append(content.text)
            return True

        client = self._get_client()
        if not client:
            logger.warning("Cannot post tweet: Twitter client not available")
            return False

        try:
            response = client.create_tweet(text=content.text)
            tweet_id = response.data.get("id") if response.data else None
            logger.info(f"Tweet posted: {content.tweet_type} (ID: {tweet_id})")
            self.posted_today.append(content.text)
            return True

        except Exception as e:
            logger.error(f"Failed to post tweet: {e}")
            return False

    def run_daily_tweets(
        self,
        models_data: list[dict[str, Any]],
        leaderboard_data: Optional[list[dict[str, Any]]] = None,
        previous_leader: Optional[str] = None,
    ) -> int:
        """
        Run daily tweet routine.

        Posts:
        1. Daily summary
        2. New leader announcement (if changed)
        3. Random Grade A spotlight (occasionally)

        Args:
            models_data: List of model scan results
            leaderboard_data: Current leaderboard rankings
            previous_leader: Previous day's leader model_id

        Returns:
            Number of tweets posted
        """
        posted = 0

        # Always post daily summary
        summary = self.generate_daily_summary(models_data)
        if self.post_tweet(summary):
            posted += 1

        # Check for new leader
        if leaderboard_data and len(leaderboard_data) > 0:
            current_leader = leaderboard_data[0].get("model_id")
            if previous_leader and current_leader != previous_leader:
                leader_tweet = self.generate_new_leader_tweet(
                    model_id=current_leader,
                    score=leaderboard_data[0].get("trust_score", 0),
                    grade=leaderboard_data[0].get("trust_grade", "?"),
                )
                if self.post_tweet(leader_tweet):
                    posted += 1

        # Occasionally spotlight a Grade A model (20% chance)
        if random.random() < 0.2:
            grade_a_models = [m for m in models_data if m.get("trust_grade") == "A"]
            if grade_a_models:
                spotlight_model = random.choice(grade_a_models)
                spotlight = self.generate_grade_a_spotlight_tweet(spotlight_model)
                if self.post_tweet(spotlight):
                    posted += 1

        # Occasionally post a tip (10% chance)
        if random.random() < 0.1:
            tip = self.generate_tip_tweet()
            if self.post_tweet(tip):
                posted += 1

        logger.info(f"Daily tweet routine complete: {posted} tweets posted")
        return posted


def run_twitter_bot(
    models_data: list[dict[str, Any]],
    leaderboard_data: Optional[list[dict[str, Any]]] = None,
    dry_run: bool = False,
) -> int:
    """
    Convenience function to run the Twitter bot.

    Args:
        models_data: List of model scan results
        leaderboard_data: Current leaderboard rankings
        dry_run: If True, don't actually post tweets

    Returns:
        Number of tweets posted
    """
    bot = TwitterBot(dry_run=dry_run)

    if not bot.is_configured() and not dry_run:
        logger.info("Twitter bot not configured (missing API credentials)")
        return 0

    return bot.run_daily_tweets(models_data, leaderboard_data)
