"""
Tests for the Trust Score Calculator.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.generator.trust_scorer import WEIGHTS, TrustFactor, TrustScore, TrustScorer


class TestTrustScorer:
    """Test suite for TrustScorer class."""

    @pytest.fixture
    def scorer(self):
        """Create a TrustScorer instance."""
        return TrustScorer()

    @pytest.fixture
    def base_metadata(self):
        """Base model metadata for testing."""
        return {
            "author": "test-org",
            "is_verified_org": False,
            "has_safetensors": True,
            "has_pickle": False,
            "downloaded_files": ["README.md", "config.json"],
            "card_data": {"description": "Test model"},
            "tags": ["pytorch", "transformers", "text-generation"],
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "downloads": 1000000,
            "likes": 500,
        }

    @pytest.fixture
    def base_vuln_results(self):
        """Base vulnerability results."""
        return {
            "summary": {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
        }

    @pytest.fixture
    def base_license(self):
        """Base license analysis."""
        return {
            "model": {
                "category": "permissive",
                "name": "Apache 2.0",
                "commercial_use": True,
            }
        }

    # Test weight validation
    def test_weights_sum_to_100(self, scorer):
        """Weights should sum to 100."""
        assert sum(scorer.weights.values()) == 100

    def test_custom_weights_normalized(self):
        """Custom weights should be normalized to 100."""
        custom_weights = {k: v * 2 for k, v in WEIGHTS.items()}  # Sum to 200
        scorer = TrustScorer(weights=custom_weights)
        assert sum(scorer.weights.values()) == pytest.approx(100, rel=0.01)

    # Test grade calculation
    @pytest.mark.parametrize(
        "score,expected_grade",
        [
            (95, "A"),
            (90, "A"),
            (89, "B"),
            (80, "B"),
            (79, "C"),
            (70, "C"),
            (69, "D"),
            (60, "D"),
            (59, "F"),
            (0, "F"),
        ],
    )
    def test_grade_calculation(self, scorer, score, expected_grade):
        """Test grade assignment for different scores."""
        assert scorer._get_grade(score) == expected_grade

    # Test verified organization scoring
    def test_verified_org_full_points(self, scorer):
        """Verified org should get full points."""
        metadata = {"author": "google", "is_verified_org": True}
        factor = scorer._score_verified_org(metadata)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_known_author_partial_points(self, scorer):
        """Known authors get partial points (85% for well-known AI labs)."""
        metadata = {"author": "stabilityai", "is_verified_org": False}
        factor = scorer._score_verified_org(metadata)
        assert factor.score == 0.85
        assert factor.status == "pass"  # Well-known orgs now get "pass" status

    def test_unknown_author_minimal_points(self, scorer):
        """Unknown authors get minimal points (40%)."""
        metadata = {"author": "random-user", "is_verified_org": False}
        factor = scorer._score_verified_org(metadata)
        assert factor.score == 0.4
        assert factor.status == "warn"

    # Test safetensors scoring
    def test_safetensors_only_full_points(self, scorer):
        """Safetensors only should get full points."""
        metadata = {"has_safetensors": True, "has_pickle": False}
        factor = scorer._score_safetensors(metadata)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_safetensors_with_pickle_partial(self, scorer):
        """Safetensors with pickle gets partial points."""
        metadata = {"has_safetensors": True, "has_pickle": True}
        factor = scorer._score_safetensors(metadata)
        assert factor.score == 0.7
        assert factor.status == "warn"

    def test_pickle_only_no_points(self, scorer):
        """Pickle only gets no points."""
        metadata = {"has_safetensors": False, "has_pickle": True}
        factor = scorer._score_safetensors(metadata)
        assert factor.score == 0.0
        assert factor.status == "fail"

    # Test vulnerability scoring
    def test_no_vulns_full_points(self, scorer):
        """No vulnerabilities should get full points."""
        vuln_results = {"summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}}
        factor = scorer._score_vulnerabilities(vuln_results)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_high_vulns_partial_points(self, scorer):
        """High vulns get partial points."""
        vuln_results = {"summary": {"critical": 0, "high": 2, "medium": 0, "low": 0}}
        factor = scorer._score_vulnerabilities(vuln_results)
        assert factor.score == 0.7
        assert factor.status == "warn"

    def test_critical_vulns_low_points(self, scorer):
        """Critical vulns get low points."""
        vuln_results = {"summary": {"critical": 2, "high": 0, "medium": 0, "low": 0}}
        factor = scorer._score_vulnerabilities(vuln_results)
        assert factor.score == 0.4
        assert factor.status == "warn"

    def test_many_critical_vulns_no_points(self, scorer):
        """Many critical vulns get no points."""
        vuln_results = {"summary": {"critical": 5, "high": 0, "medium": 0, "low": 0}}
        factor = scorer._score_vulnerabilities(vuln_results)
        assert factor.score == 0.0
        assert factor.status == "fail"

    # Test license scoring
    def test_permissive_license_full_points(self, scorer):
        """Permissive license gets full points."""
        license_analysis = {
            "model": {"category": "permissive", "name": "MIT", "commercial_use": True}
        }
        factor = scorer._score_license(license_analysis)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_commercial_license_high_points(self, scorer):
        """Commercial license gets high points."""
        license_analysis = {
            "model": {"category": "model-specific", "name": "Llama", "commercial_use": True}
        }
        factor = scorer._score_license(license_analysis)
        assert factor.score == 0.8
        assert factor.status == "pass"

    def test_restrictive_license_partial_points(self, scorer):
        """Restrictive license gets partial points."""
        license_analysis = {
            "model": {"category": "copyleft", "name": "GPL", "commercial_use": False}
        }
        factor = scorer._score_license(license_analysis)
        assert factor.score == 0.4
        assert factor.status == "warn"

    def test_unknown_license_no_points(self, scorer):
        """Unknown license gets no points."""
        license_analysis = {
            "model": {"category": "unknown", "name": "Unknown", "commercial_use": False}
        }
        factor = scorer._score_license(license_analysis)
        assert factor.score == 0.0
        assert factor.status == "fail"

    # Test recency scoring
    def test_recent_update_full_points(self, scorer):
        """Recent update gets full points."""
        metadata = {"last_modified": datetime.now(timezone.utc).isoformat()}
        factor = scorer._score_recency(metadata)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_old_update_partial_points(self, scorer):
        """Old update gets partial points."""
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        metadata = {"last_modified": old_date.isoformat()}
        factor = scorer._score_recency(metadata)
        assert factor.score == 0.7
        assert factor.status == "pass"

    def test_very_old_update_low_points(self, scorer):
        """Very old update gets low points."""
        old_date = datetime.now(timezone.utc) - timedelta(days=200)
        metadata = {"last_modified": old_date.isoformat()}
        factor = scorer._score_recency(metadata)
        assert factor.score == 0.2
        assert factor.status == "warn"

    def test_unknown_update_date(self, scorer):
        """Unknown update date gets neutral score."""
        metadata = {"last_modified": None}
        factor = scorer._score_recency(metadata)
        assert factor.score == 0.5
        assert factor.status == "warn"

    # Test community engagement
    def test_high_engagement_full_points(self, scorer):
        """High engagement gets full points."""
        metadata = {"downloads": 50000000, "likes": 2000}  # Very popular
        factor = scorer._score_community(metadata)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_medium_engagement_partial_points(self, scorer):
        """Medium engagement gets partial points."""
        metadata = {"downloads": 100000, "likes": 100}
        factor = scorer._score_community(metadata)
        assert 0.3 <= factor.score <= 0.8

    def test_low_engagement_minimal_points(self, scorer):
        """Low engagement gets minimal points."""
        metadata = {"downloads": 100, "likes": 5}
        factor = scorer._score_community(metadata)
        assert factor.score < 0.5
        assert factor.status == "warn"

    # Test no pickle scoring
    def test_no_pickle_full_points(self, scorer):
        """No pickle files gets full points."""
        metadata = {"has_pickle": False, "has_safetensors": True}
        factor = scorer._score_no_pickle(metadata)
        assert factor.score == 1.0
        assert factor.status == "pass"

    def test_pickle_with_safetensors_partial(self, scorer):
        """Pickle with safetensors gets partial points."""
        metadata = {"has_pickle": True, "has_safetensors": True}
        factor = scorer._score_no_pickle(metadata)
        assert factor.score == 0.5
        assert factor.status == "warn"

    def test_pickle_only_no_points(self, scorer):
        """Pickle only gets no points."""
        metadata = {"has_pickle": True, "has_safetensors": False}
        factor = scorer._score_no_pickle(metadata)
        assert factor.score == 0.0
        assert factor.status == "fail"

    # Test full calculation
    def test_calculate_score_returns_trust_score(
        self, scorer, base_metadata, base_vuln_results, base_license
    ):
        """calculate_score should return TrustScore object."""
        result = scorer.calculate_score(base_metadata, base_vuln_results, base_license)
        assert isinstance(result, TrustScore)
        assert 0 <= result.total_score <= 100
        assert result.grade in ["A", "B", "C", "D", "F"]
        assert len(result.factors) == 8  # 8 trust factors
        assert isinstance(result.summary, str)

    def test_calculate_score_all_factors_present(
        self, scorer, base_metadata, base_vuln_results, base_license
    ):
        """All 8 factors should be present in result."""
        result = scorer.calculate_score(base_metadata, base_vuln_results, base_license)
        factor_names = [f.name for f in result.factors]
        expected_factors = [
            "Verified Organization",
            "Safe Serialization",  # Renamed from "SafeTensors Format"
            "No Critical/High CVEs",
            "Clear License",
            "Model Card Quality",
            "Recent Updates",
            "Community Engagement",
            "No Pickle Files",
        ]
        for expected in expected_factors:
            assert expected in factor_names

    def test_score_color_property(self, scorer, base_metadata, base_vuln_results, base_license):
        """TrustScore should have correct color property."""
        result = scorer.calculate_score(base_metadata, base_vuln_results, base_license)
        assert result.color.startswith("#")
        assert len(result.color) == 7  # #RRGGBB format

    def test_high_score_summary_positive(self, scorer):
        """High scores should have positive summary."""
        # Create ideal metadata
        metadata = {
            "author": "google",
            "is_verified_org": True,
            "has_safetensors": True,
            "has_pickle": False,
            "downloaded_files": ["README.md", "config.json"],
            "card_data": {"description": "Test"},
            "tags": ["a", "b", "c"],
            "last_modified": datetime.now(timezone.utc).isoformat(),
            "downloads": 50000000,
            "likes": 2000,
        }
        vuln = {"summary": {"critical": 0, "high": 0, "medium": 0, "low": 0}}
        license_info = {"model": {"category": "permissive", "name": "MIT", "commercial_use": True}}

        result = scorer.calculate_score(metadata, vuln, license_info)
        assert "high trust score" in result.summary.lower()

    def test_low_score_summary_negative(self, scorer):
        """Low scores should have concerning summary."""
        # Create poor metadata
        metadata = {
            "author": "unknown",
            "is_verified_org": False,
            "has_safetensors": False,
            "has_pickle": True,
            "downloaded_files": [],
            "card_data": {},
            "tags": [],
            "last_modified": None,
            "downloads": 10,
            "likes": 0,
        }
        vuln = {"summary": {"critical": 5, "high": 3, "medium": 0, "low": 0}}
        license_info = {
            "model": {"category": "unknown", "name": "Unknown", "commercial_use": False}
        }

        result = scorer.calculate_score(metadata, vuln, license_info)
        assert "concern" in result.summary.lower() or "low" in result.summary.lower()


class TestTrustFactor:
    """Test TrustFactor dataclass."""

    def test_trust_factor_creation(self):
        """TrustFactor should be creatable with all fields."""
        factor = TrustFactor(
            name="Test Factor",
            weight=10,
            score=0.8,
            points=8.0,
            reason="Test reason",
            status="pass",
            tooltip="Test tooltip",
        )
        assert factor.name == "Test Factor"
        assert factor.weight == 10
        assert factor.score == 0.8
        assert factor.points == 8.0
        assert factor.reason == "Test reason"
        assert factor.status == "pass"
        assert factor.tooltip == "Test tooltip"

    def test_trust_factor_default_tooltip(self):
        """TrustFactor should have default empty tooltip."""
        factor = TrustFactor(
            name="Test",
            weight=10,
            score=1.0,
            points=10.0,
            reason="Test",
            status="pass",
        )
        assert factor.tooltip == ""
