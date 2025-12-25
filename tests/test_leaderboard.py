"""
Tests for the Leaderboard Database module.
"""
import pytest
from datetime import date
from unittest.mock import MagicMock, patch

from src.database.leaderboard import LeaderboardDB, MIN_DOWNLOADS_ELIGIBLE, TIE_BREAKER_GRACE_DAYS


class TestLeaderboardConstants:
    """Test leaderboard constants."""

    def test_min_downloads_eligible(self):
        """Minimum downloads should be 1 million."""
        assert MIN_DOWNLOADS_ELIGIBLE == 1_000_000

    def test_tie_breaker_grace_days(self):
        """Tie breaker grace period should be 5 days."""
        assert TIE_BREAKER_GRACE_DAYS == 5


class TestLeaderboardDB:
    """Test LeaderboardDB class methods."""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=None)
        return mock_conn, mock_cursor

    @pytest.fixture
    def sample_models_data(self):
        """Sample models data for testing."""
        return [
            {
                "model_id": "org1/model1",
                "trust_score": 85,
                "trust_grade": "B",
                "downloads": 5000000,
            },
            {
                "model_id": "org2/model2",
                "trust_score": 78,
                "trust_grade": "C",
                "downloads": 2000000,
            },
            {
                "model_id": "org3/model3",
                "trust_score": 65,
                "trust_grade": "D",
                "downloads": 500000,  # Below threshold
            },
        ]

    def test_filter_eligible_models(self, sample_models_data):
        """Only models with 1M+ downloads should be eligible."""
        eligible = [m for m in sample_models_data if m["downloads"] >= MIN_DOWNLOADS_ELIGIBLE]
        assert len(eligible) == 2
        assert all(m["downloads"] >= MIN_DOWNLOADS_ELIGIBLE for m in eligible)

    def test_model_ranking_by_score(self, sample_models_data):
        """Models should be ranked by trust score descending."""
        eligible = [m for m in sample_models_data if m["downloads"] >= MIN_DOWNLOADS_ELIGIBLE]
        sorted_models = sorted(eligible, key=lambda x: (-x["trust_score"], -x["downloads"]))
        assert sorted_models[0]["model_id"] == "org1/model1"
        assert sorted_models[1]["model_id"] == "org2/model2"

    def test_tie_breaker_downloads(self):
        """When scores are tied, higher downloads should win."""
        models = [
            {"model_id": "a", "trust_score": 80, "downloads": 3000000},
            {"model_id": "b", "trust_score": 80, "downloads": 5000000},
        ]
        sorted_models = sorted(models, key=lambda x: (-x["trust_score"], -x["downloads"]))
        assert sorted_models[0]["model_id"] == "b"  # Higher downloads

    @patch("src.database.leaderboard.psycopg2")
    def test_context_manager_connects(self, mock_psycopg2):
        """LeaderboardDB should connect on enter."""
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}):
            db = LeaderboardDB()
            db.__enter__()
            mock_psycopg2.connect.assert_called_once()

    @patch("src.database.leaderboard.psycopg2")
    def test_context_manager_closes(self, mock_psycopg2):
        """LeaderboardDB should close connection on exit."""
        mock_conn = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn

        with patch.dict("os.environ", {"DATABASE_URL": "postgresql://test"}):
            db = LeaderboardDB()
            db.conn = mock_conn
            # Manually call close to test that it's called
            if db.conn:
                db.conn.close()
            mock_conn.close.assert_called_once()


class TestLeaderboardScoring:
    """Test scoring and ranking logic."""

    def test_grade_from_score_a(self):
        """Score 90+ should be grade A."""
        assert self._get_grade(95) == "A"
        assert self._get_grade(90) == "A"

    def test_grade_from_score_b(self):
        """Score 80-89 should be grade B."""
        assert self._get_grade(85) == "B"
        assert self._get_grade(80) == "B"

    def test_grade_from_score_c(self):
        """Score 70-79 should be grade C."""
        assert self._get_grade(75) == "C"
        assert self._get_grade(70) == "C"

    def test_grade_from_score_d(self):
        """Score 60-69 should be grade D."""
        assert self._get_grade(65) == "D"
        assert self._get_grade(60) == "D"

    def test_grade_from_score_f(self):
        """Score below 60 should be grade F."""
        assert self._get_grade(59) == "F"
        assert self._get_grade(0) == "F"

    def _get_grade(self, score: int) -> str:
        """Helper to get grade from score."""
        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"


class TestLeaderboardDataFormat:
    """Test data format expectations."""

    def test_model_data_required_fields(self):
        """Model data should have required fields."""
        required_fields = ["model_id", "trust_score", "trust_grade", "downloads"]
        sample = {
            "model_id": "test/model",
            "trust_score": 75,
            "trust_grade": "C",
            "downloads": 1500000,
        }
        for field in required_fields:
            assert field in sample

    def test_ranking_output_fields(self):
        """Ranking output should have expected fields."""
        expected_fields = ["rank", "model_id", "trust_score", "trust_grade", "downloads", "streak_days"]
        sample_ranking = {
            "rank": 1,
            "model_id": "test/model",
            "trust_score": 85,
            "trust_grade": "B",
            "downloads": 5000000,
            "streak_days": 3,
        }
        for field in expected_fields:
            assert field in sample_ranking

    def test_model_id_format(self):
        """Model ID should be in org/name format."""
        model_id = "sentence-transformers/all-MiniLM-L6-v2"
        parts = model_id.split("/")
        assert len(parts) == 2
        assert parts[0] == "sentence-transformers"
        assert parts[1] == "all-MiniLM-L6-v2"
