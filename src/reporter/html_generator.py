"""
HTML Report Generator

Generates HTML reports for individual models and the dashboard.
"""
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

# Minimum downloads for leaderboard eligibility
MIN_DOWNLOADS_ELIGIBLE = 1_000_000


def format_number(num: int) -> str:
    """Format large numbers with K/M suffix."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_size(gb: float) -> str:
    """Format size in GB."""
    if gb >= 1:
        return f"{gb:.1f} GB"
    else:
        return f"{gb * 1024:.0f} MB"


def get_trust_grade_class(score: int) -> str:
    """Get CSS class for trust score."""
    if score >= 80:
        return "excellent"
    elif score >= 70:
        return "good"
    elif score >= 60:
        return "moderate"
    elif score >= 40:
        return "low"
    else:
        return "poor"


class HTMLReportGenerator:
    """Generates HTML reports from scan data."""

    def __init__(
        self,
        templates_dir: Path,
        output_dir: Path,
        static_dir: Path,
        base_url: str = "",
        site_url: str = "https://hugginghugh.com",
    ):
        """
        Initialize HTML report generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
            output_dir: Directory for output HTML files
            static_dir: Directory containing static assets (CSS, JS)
            base_url: Base URL for relative links
            site_url: Absolute URL for SEO meta tags
        """
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.static_dir = Path(static_dir)
        self.base_url = base_url.rstrip("/")
        self.site_url = site_url.rstrip("/")

        # Set up Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

        # Add custom filters
        self.env.filters["format_number"] = format_number
        self.env.filters["format_size"] = format_size

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_model_report(
        self,
        model_metadata: dict,
        sbom: dict,
        vulnerabilities: dict,
        trust_score,  # TrustScore dataclass
        license_analysis: dict,
        db=None,  # Optional LeaderboardDB instance for history
    ) -> Path:
        """
        Generate HTML report for a single model.

        Args:
            model_metadata: Model metadata from fetcher
            sbom: SBOM dictionary
            vulnerabilities: Vulnerability scan results
            trust_score: TrustScore object
            license_analysis: License analysis results
            db: Optional LeaderboardDB instance for fetching history

        Returns:
            Path to generated HTML file
        """
        model_id = model_metadata.get("model_id", "unknown")
        safe_id = model_id.replace("/", "_")

        logger.info(f"Generating report for {model_id}")

        # Create model report directory
        report_dir = self.output_dir / "reports" / safe_id
        report_dir.mkdir(parents=True, exist_ok=True)

        # Fetch history data if database available
        history_data = self._get_history_data(model_id, model_metadata, db)

        # Prepare template context
        context = {
            "base_url": self.base_url,
            "site_url": self.site_url,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "model": self._prepare_model_context(model_metadata),
            "sbom": sbom,
            "vulnerabilities": vulnerabilities,
            "trust_score": self._prepare_trust_score_context(trust_score),
            "license_analysis": license_analysis,
            "history": history_data,
            "has_history": bool(history_data.get("score_history")),
            "is_eligible": model_metadata.get("downloads", 0) >= MIN_DOWNLOADS_ELIGIBLE,
        }

        # Render template
        template = self.env.get_template("model_report.html")
        html_content = template.render(**context)

        # Write HTML file
        html_file = report_dir / "index.html"
        html_file.write_text(html_content)

        # Write SBOM JSON
        sbom_file = report_dir / "sbom.cdx.json"
        sbom_file.write_text(json.dumps(sbom, indent=2))

        # Write vulnerabilities JSON
        vuln_file = report_dir / "vulnerabilities.json"
        vuln_file.write_text(json.dumps(vulnerabilities, indent=2))

        # Write history JSON if available
        if history_data.get("score_history"):
            history_file = report_dir / "history.json"
            history_file.write_text(json.dumps(history_data, indent=2))

        logger.info(f"Report generated: {html_file}")
        return html_file

    def _get_history_data(
        self, model_id: str, metadata: dict, db
    ) -> dict[str, Any]:
        """
        Fetch history data for a model from the database.

        Args:
            model_id: Model ID
            metadata: Model metadata
            db: LeaderboardDB instance

        Returns:
            Dictionary with score history, rank history, and stats
        """
        if db is None:
            return {}

        try:
            # Get 90 days of history
            score_history = db.get_model_history(model_id, days=90)

            # Get rank history if eligible
            downloads = metadata.get("downloads", 0)
            rank_history = []
            if downloads >= MIN_DOWNLOADS_ELIGIBLE:
                rank_history = db.get_rank_history(model_id, days=90)

            # Get stats
            stats = db.get_model_stats(model_id)

            return {
                "score_history": score_history,
                "rank_history": rank_history,
                "stats": stats,
            }
        except Exception as e:
            logger.warning(f"Failed to fetch history for {model_id}: {e}")
            return {}

    def _prepare_model_context(self, metadata: dict) -> dict:
        """Prepare model data for template context."""
        return {
            "model_id": metadata.get("model_id", "unknown"),
            "model_name": metadata.get("model_name", "Unknown"),
            "author": metadata.get("author", "Unknown"),
            "downloads": metadata.get("downloads", 0),
            "downloads_formatted": format_number(metadata.get("downloads", 0)),
            "likes": metadata.get("likes", 0),
            "likes_formatted": format_number(metadata.get("likes", 0)),
            "size_formatted": format_size(metadata.get("total_size_gb", 0)),
            "file_count": metadata.get("file_count", 0),
            "has_safetensors": metadata.get("has_safetensors", False),
            "has_pickle": metadata.get("has_pickle", False),
            "is_verified_org": metadata.get("is_verified_org", False),
            "pipeline_tag": metadata.get("pipeline_tag"),
            "library_name": metadata.get("library_name"),
            "tags": metadata.get("tags", []),
            "license": metadata.get("license"),
            "last_modified_formatted": self._format_date(metadata.get("last_modified")),
        }

    def _prepare_trust_score_context(self, trust_score) -> dict:
        """Prepare trust score for template context."""
        return {
            "total_score": trust_score.total_score,
            "grade": trust_score.grade,
            "color": trust_score.color,
            "summary": trust_score.summary,
            "factors": [
                {
                    "name": f.name,
                    "weight": f.weight,
                    "score": f.score,
                    "points": f.points,
                    "reason": f.reason,
                    "status": f.status,
                    "tooltip": f.tooltip,
                }
                for f in trust_score.factors
            ],
        }

    def _format_date(self, date_str: Optional[str]) -> str:
        """Format date string for display."""
        if not date_str:
            return "Unknown"
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            return str(date_str)[:10]

    def copy_static_assets(self):
        """Copy static assets to output directory."""
        output_static = self.output_dir / "static"
        if output_static.exists():
            shutil.rmtree(output_static)
        shutil.copytree(self.static_dir, output_static)
        logger.info(f"Static assets copied to {output_static}")
