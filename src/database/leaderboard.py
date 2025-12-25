"""
Leaderboard Database Operations

Handles all PostgreSQL operations for the HuggingHugh leaderboard:
- Recording daily score snapshots
- Computing and storing rankings
- Tie-breaker logic with 5-day grace period
- Historical queries for hall of fame
"""
import logging
import os
from datetime import date, datetime, timedelta
from typing import Any, Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Minimum downloads to be eligible for leaderboard
MIN_DOWNLOADS_ELIGIBLE = 1_000_000

# Tie-breaker grace period in days
TIE_BREAKER_GRACE_DAYS = 5


class LeaderboardDB:
    """Database operations for the leaderboard."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection URL. If not provided, uses DATABASE_URL env var.
        """
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable not set")

        self._conn = None

    def connect(self):
        """Establish database connection."""
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self.database_url)
        return self._conn

    def close(self):
        """Close database connection."""
        if self._conn and not self._conn.closed:
            self._conn.close()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def record_scan_results(self, scan_date: date, models_data: list[dict[str, Any]]) -> int:
        """
        Record all model scores for a daily scan.

        Args:
            scan_date: Date of the scan
            models_data: List of model data dictionaries from the scan

        Returns:
            Number of records inserted
        """
        conn = self.connect()
        cursor = conn.cursor()

        inserted = 0
        for model in models_data:
            try:
                vuln_summary = model.get("vulnerabilities", {}).get("summary", {})

                cursor.execute("""
                    INSERT INTO score_history (
                        scan_date, model_id, trust_score, trust_grade,
                        downloads, likes, vuln_count, vuln_critical, vuln_high,
                        has_safetensors, license
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (scan_date, model_id) DO UPDATE SET
                        trust_score = EXCLUDED.trust_score,
                        trust_grade = EXCLUDED.trust_grade,
                        downloads = EXCLUDED.downloads,
                        likes = EXCLUDED.likes,
                        vuln_count = EXCLUDED.vuln_count,
                        vuln_critical = EXCLUDED.vuln_critical,
                        vuln_high = EXCLUDED.vuln_high,
                        has_safetensors = EXCLUDED.has_safetensors,
                        license = EXCLUDED.license
                """, (
                    scan_date,
                    model.get("model_id"),
                    model.get("trust_score", 0),
                    model.get("trust_grade", "F"),
                    model.get("downloads", 0),
                    model.get("likes", 0),
                    vuln_summary.get("total", 0),
                    vuln_summary.get("critical", 0),
                    vuln_summary.get("high", 0),
                    model.get("has_safetensors", False),
                    model.get("license"),
                ))
                inserted += 1
            except Exception as e:
                logger.error(f"Error recording {model.get('model_id')}: {e}")

        conn.commit()
        cursor.close()
        logger.info(f"Recorded {inserted} model scores for {scan_date}")
        return inserted

    def compute_rankings(self, scan_date: date) -> list[dict[str, Any]]:
        """
        Compute rankings for eligible models with tie-breaker logic.

        Eligibility: downloads >= 1M
        Tie-breaker:
          1. If scores equal, model that achieved rank first wins
          2. 5-day grace period: within 5 days, higher downloads wins
          3. After 5 days, first-to-achieve holds rank

        Args:
            scan_date: Date to compute rankings for

        Returns:
            List of ranked models
        """
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get today's eligible models sorted by score (desc), then downloads (desc)
        cursor.execute("""
            SELECT model_id, trust_score, trust_grade, downloads, likes,
                   vuln_count, has_safetensors, license
            FROM score_history
            WHERE scan_date = %s AND downloads >= %s
            ORDER BY trust_score DESC, downloads DESC
        """, (scan_date, MIN_DOWNLOADS_ELIGIBLE))

        todays_models = cursor.fetchall()

        # Get previous rankings for comparison
        cursor.execute("""
            SELECT rank, model_id, trust_score, first_achieved_rank_date, streak_days
            FROM current_rankings
            ORDER BY rank
        """)
        previous_rankings = {r["model_id"]: dict(r) for r in cursor.fetchall()}

        # Compute new rankings with tie-breaker logic
        new_rankings = []
        current_rank = 0
        prev_score = None

        for model in todays_models:
            current_rank += 1
            model_id = model["model_id"]
            score = model["trust_score"]

            # Determine first_achieved_rank_date
            if model_id in previous_rankings:
                prev = previous_rankings[model_id]
                prev_rank = prev["rank"]

                # Check if this model held this rank before
                if prev_rank == current_rank and prev["trust_score"] == score:
                    # Same rank and score - keep original date, increment streak
                    first_achieved = prev["first_achieved_rank_date"]
                    streak = prev["streak_days"] + 1
                else:
                    # New rank or score change
                    first_achieved = scan_date
                    streak = 1

                rank_change = prev_rank - current_rank  # Positive = moved up
            else:
                # New to rankings
                first_achieved = scan_date
                streak = 1
                rank_change = 0

            new_rankings.append({
                "rank": current_rank,
                "model_id": model_id,
                "trust_score": score,
                "trust_grade": model["trust_grade"],
                "downloads": model["downloads"],
                "likes": model["likes"],
                "vuln_count": model["vuln_count"],
                "has_safetensors": model["has_safetensors"],
                "first_achieved_rank_date": first_achieved,
                "streak_days": streak,
                "previous_rank": previous_rankings.get(model_id, {}).get("rank"),
                "rank_change": rank_change,
            })

        # Apply tie-breaker logic for models with same score
        new_rankings = self._apply_tie_breaker(new_rankings, scan_date)

        # Update current_rankings table
        self._update_current_rankings(new_rankings)

        cursor.close()
        return new_rankings

    def _apply_tie_breaker(
        self, rankings: list[dict], scan_date: date
    ) -> list[dict]:
        """
        Apply tie-breaker logic to rankings.

        For tied scores:
        - Within 5-day grace period: higher downloads wins
        - After grace period: first to achieve wins
        """
        # Group by score
        score_groups = {}
        for r in rankings:
            score = r["trust_score"]
            if score not in score_groups:
                score_groups[score] = []
            score_groups[score].append(r)

        # Re-sort within each tied group
        final_rankings = []
        for score in sorted(score_groups.keys(), reverse=True):
            group = score_groups[score]

            if len(group) == 1:
                final_rankings.extend(group)
            else:
                # Apply tie-breaker
                grace_cutoff = scan_date - timedelta(days=TIE_BREAKER_GRACE_DAYS)

                def tie_breaker_key(m):
                    first_date = m["first_achieved_rank_date"]
                    if isinstance(first_date, str):
                        first_date = datetime.strptime(first_date, "%Y-%m-%d").date()

                    # Within grace period: sort by downloads (desc)
                    # After grace period: sort by first_achieved_date (asc)
                    if first_date >= grace_cutoff:
                        # Within grace - higher downloads wins (negative for desc sort)
                        return (0, -m["downloads"])
                    else:
                        # Past grace - earlier date wins
                        return (1, first_date)

                group.sort(key=tie_breaker_key)
                final_rankings.extend(group)

        # Re-assign ranks
        for i, r in enumerate(final_rankings, 1):
            r["rank"] = i

        return final_rankings

    def _update_current_rankings(self, rankings: list[dict]):
        """Update the current_rankings table with new rankings."""
        conn = self.connect()
        cursor = conn.cursor()

        # Clear existing rankings
        cursor.execute("DELETE FROM current_rankings")

        # Insert new rankings
        for r in rankings:
            cursor.execute("""
                INSERT INTO current_rankings (
                    rank, model_id, trust_score, trust_grade, downloads,
                    first_achieved_rank_date, streak_days, previous_rank, rank_change
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                r["rank"],
                r["model_id"],
                r["trust_score"],
                r["trust_grade"],
                r["downloads"],
                r["first_achieved_rank_date"],
                r["streak_days"],
                r["previous_rank"],
                r["rank_change"],
            ))

        conn.commit()
        cursor.close()
        logger.info(f"Updated current rankings with {len(rankings)} models")

    def get_top_n(self, n: int = 3) -> list[dict[str, Any]]:
        """
        Get top N models from current rankings.

        Args:
            n: Number of top models to return

        Returns:
            List of top N ranked models
        """
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT rank, model_id, trust_score, trust_grade, downloads,
                   first_achieved_rank_date, streak_days, previous_rank, rank_change
            FROM current_rankings
            ORDER BY rank
            LIMIT %s
        """, (n,))

        results = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        return results

    def get_full_leaderboard(self) -> list[dict[str, Any]]:
        """
        Get full leaderboard (all eligible models).

        Returns:
            List of all ranked models
        """
        return self.get_top_n(n=1000)  # Effectively all

    def get_model_history(
        self, model_id: str, days: int = 30
    ) -> list[dict[str, Any]]:
        """
        Get score history for a specific model.

        Args:
            model_id: Model ID to query
            days: Number of days of history

        Returns:
            List of daily scores
        """
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT scan_date, trust_score, trust_grade, downloads, vuln_count
            FROM score_history
            WHERE model_id = %s AND scan_date >= %s
            ORDER BY scan_date DESC
        """, (model_id, date.today() - timedelta(days=days)))

        results = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        return results

    def get_most_improved(self, days: int = 7) -> list[dict[str, Any]]:
        """
        Get models with biggest score improvements over N days.

        Args:
            days: Number of days to compare

        Returns:
            List of models with their improvement delta
        """
        conn = self.connect()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        compare_date = date.today() - timedelta(days=days)

        cursor.execute("""
            WITH today AS (
                SELECT model_id, trust_score
                FROM score_history
                WHERE scan_date = (SELECT MAX(scan_date) FROM score_history)
            ),
            past AS (
                SELECT model_id, trust_score
                FROM score_history
                WHERE scan_date = %s
            )
            SELECT
                t.model_id,
                t.trust_score as current_score,
                p.trust_score as past_score,
                (t.trust_score - p.trust_score) as improvement
            FROM today t
            JOIN past p ON t.model_id = p.model_id
            WHERE t.trust_score > p.trust_score
            ORDER BY improvement DESC
            LIMIT 10
        """, (compare_date,))

        results = [dict(r) for r in cursor.fetchall()]
        cursor.close()
        return results

    def record_hall_of_fame(
        self,
        category: str,
        model_id: str,
        value: int,
        achieved_date: date,
        details: Optional[dict] = None,
    ):
        """Record a hall of fame achievement."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO hall_of_fame (category, model_id, value, achieved_date, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (category, model_id, value, achieved_date, psycopg2.extras.Json(details)))

        conn.commit()
        cursor.close()
        logger.info(f"Recorded hall of fame: {category} - {model_id}")

    def get_eligible_count(self, scan_date: date) -> int:
        """Get count of eligible models (1M+ downloads) for a scan date."""
        conn = self.connect()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT COUNT(*) FROM score_history
            WHERE scan_date = %s AND downloads >= %s
        """, (scan_date, MIN_DOWNLOADS_ELIGIBLE))

        count = cursor.fetchone()[0]
        cursor.close()
        return count
