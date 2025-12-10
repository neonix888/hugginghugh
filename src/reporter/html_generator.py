"""
HTML Report Generator

Generates HTML reports for individual models and the dashboard.
"""
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


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
    ):
        """
        Initialize HTML report generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
            output_dir: Directory for output HTML files
            static_dir: Directory containing static assets (CSS, JS)
            base_url: Base URL for the site (for links)
        """
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.static_dir = Path(static_dir)
        self.base_url = base_url.rstrip("/")

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
    ) -> Path:
        """
        Generate HTML report for a single model.

        Args:
            model_metadata: Model metadata from fetcher
            sbom: SBOM dictionary
            vulnerabilities: Vulnerability scan results
            trust_score: TrustScore object
            license_analysis: License analysis results

        Returns:
            Path to generated HTML file
        """
        model_id = model_metadata.get("model_id", "unknown")
        safe_id = model_id.replace("/", "_")

        logger.info(f"Generating report for {model_id}")

        # Create model report directory
        report_dir = self.output_dir / "reports" / safe_id
        report_dir.mkdir(parents=True, exist_ok=True)

        # Prepare template context
        context = {
            "base_url": self.base_url,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "model": self._prepare_model_context(model_metadata),
            "sbom": sbom,
            "vulnerabilities": vulnerabilities,
            "trust_score": self._prepare_trust_score_context(trust_score),
            "license_analysis": license_analysis,
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

        logger.info(f"Report generated: {html_file}")
        return html_file

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
