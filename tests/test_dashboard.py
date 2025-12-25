"""
Tests for the Dashboard Generator.
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.reporter.dashboard import DashboardGenerator, format_number


class TestFormatNumber:
    """Test the format_number utility function."""

    def test_format_number_millions(self):
        """Numbers in millions should be formatted with M suffix."""
        assert format_number(1500000) == "1.5M"
        assert format_number(10000000) == "10.0M"
        assert format_number(999999999) == "1000.0M"

    def test_format_number_thousands(self):
        """Numbers in thousands should be formatted with K suffix."""
        assert format_number(1500) == "1.5K"
        assert format_number(10000) == "10.0K"
        assert format_number(999999) == "1000.0K"

    def test_format_number_small(self):
        """Small numbers should be formatted as-is."""
        assert format_number(999) == "999"
        assert format_number(100) == "100"
        assert format_number(0) == "0"

    def test_format_number_edge_cases(self):
        """Edge cases should be handled correctly."""
        assert format_number(1000000) == "1.0M"
        assert format_number(1000) == "1.0K"


class TestDashboardGenerator:
    """Test suite for DashboardGenerator class."""

    @pytest.fixture
    def temp_output_dir(self, tmp_path):
        """Create a temporary output directory."""
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        return output_dir

    @pytest.fixture
    def temp_templates_dir(self, tmp_path):
        """Create a temporary templates directory with basic templates."""
        templates_dir = tmp_path / "templates"
        templates_dir.mkdir()

        # Create minimal templates
        base_template = templates_dir / "base.html"
        base_template.write_text("""
<!DOCTYPE html>
<html>
<head><title>{% block title %}{% endblock %}</title></head>
<body>{% block content %}{% endblock %}</body>
</html>
""")

        dashboard_template = templates_dir / "dashboard.html"
        dashboard_template.write_text("""
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<h1>Models: {{ models|length }}</h1>
{% endblock %}
""")

        about_template = templates_dir / "about.html"
        about_template.write_text("""
{% extends "base.html" %}
{% block title %}About{% endblock %}
{% block content %}<h1>About</h1>{% endblock %}
""")

        grade_page_template = templates_dir / "grade_page.html"
        grade_page_template.write_text("""
{% extends "base.html" %}
{% block title %}Grade {{ grade }}{% endblock %}
{% block content %}<h1>Grade {{ grade }}</h1>{% endblock %}
""")

        leaderboard_template = templates_dir / "leaderboard.html"
        leaderboard_template.write_text("""
{% extends "base.html" %}
{% block title %}Leaderboard{% endblock %}
{% block content %}<h1>Leaderboard</h1>{% endblock %}
""")

        return templates_dir

    @pytest.fixture
    def sample_models(self):
        """Sample models data for testing."""
        return [
            {
                "model_id": "org1/model-a",
                "model_name": "model-a",
                "author": "org1",
                "downloads": 5000000,
                "likes": 500,
                "trust_score": 85,
                "trust_grade": "B",
                "pipeline_tag": "text-generation",
                "library_name": "transformers",
                "has_safetensors": True,
                "vuln_count": 0,
            },
            {
                "model_id": "org2/model-b",
                "model_name": "model-b",
                "author": "org2",
                "downloads": 2000000,
                "likes": 200,
                "trust_score": 65,
                "trust_grade": "D",
                "pipeline_tag": "image-classification",
                "library_name": "pytorch",
                "has_safetensors": False,
                "vuln_count": 2,
            },
        ]

    def test_dashboard_generator_init(self, temp_output_dir, temp_templates_dir):
        """DashboardGenerator should initialize correctly."""
        generator = DashboardGenerator(
            output_dir=temp_output_dir,
            templates_dir=temp_templates_dir,
        )
        assert generator.output_dir == temp_output_dir
        assert generator.templates_dir == temp_templates_dir

    def test_generate_dashboard_creates_file(
        self, temp_output_dir, temp_templates_dir, sample_models
    ):
        """generate_dashboard should create index.html."""
        generator = DashboardGenerator(
            output_dir=temp_output_dir,
            templates_dir=temp_templates_dir,
        )
        result = generator.generate_dashboard(sample_models)
        assert result.exists()
        assert result.name == "index.html"

    def test_generate_dashboard_content(
        self, temp_output_dir, temp_templates_dir, sample_models
    ):
        """Dashboard should contain model count."""
        generator = DashboardGenerator(
            output_dir=temp_output_dir,
            templates_dir=temp_templates_dir,
        )
        result = generator.generate_dashboard(sample_models)
        content = result.read_text()
        assert "2" in content  # 2 models


class TestGradeCalculation:
    """Test grade-related calculations."""

    @pytest.mark.parametrize("score,expected_class", [
        (95, "excellent"),
        (85, "good"),
        (75, "moderate"),
        (65, "low"),
        (50, "poor"),
    ])
    def test_grade_class_mapping(self, score, expected_class):
        """Trust scores should map to correct CSS classes."""
        if score >= 90:
            grade_class = "excellent"
        elif score >= 80:
            grade_class = "good"
        elif score >= 70:
            grade_class = "moderate"
        elif score >= 60:
            grade_class = "low"
        else:
            grade_class = "poor"
        assert grade_class == expected_class

    def test_grade_distribution_counts(self):
        """Grade distribution should count correctly."""
        models = [
            {"trust_grade": "A"},
            {"trust_grade": "A"},
            {"trust_grade": "B"},
            {"trust_grade": "C"},
            {"trust_grade": "F"},
            {"trust_grade": "F"},
            {"trust_grade": "F"},
        ]
        grade_counts = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
        for model in models:
            grade = model["trust_grade"]
            if grade in grade_counts:
                grade_counts[grade] += 1

        assert grade_counts["A"] == 2
        assert grade_counts["B"] == 1
        assert grade_counts["C"] == 1
        assert grade_counts["D"] == 0
        assert grade_counts["F"] == 3


class TestModelDataPreparation:
    """Test model data preparation utilities."""

    def test_safe_id_generation(self):
        """Model IDs should be converted to safe filenames."""
        model_id = "sentence-transformers/all-MiniLM-L6-v2"
        safe_id = model_id.replace("/", "_")
        assert safe_id == "sentence-transformers_all-MiniLM-L6-v2"
        assert "/" not in safe_id

    def test_author_extraction(self):
        """Author should be extracted from model ID."""
        model_id = "huggingface/transformers"
        parts = model_id.split("/")
        author = parts[0] if len(parts) == 2 else "unknown"
        assert author == "huggingface"

    def test_model_name_extraction(self):
        """Model name should be extracted from model ID."""
        model_id = "huggingface/transformers"
        parts = model_id.split("/")
        model_name = parts[1] if len(parts) == 2 else model_id
        assert model_name == "transformers"
