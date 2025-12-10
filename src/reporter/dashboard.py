"""
Dashboard Generator

Generates the main dashboard page with all models.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)


def format_number(num: int) -> str:
    """Format large numbers with K/M suffix."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


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


class DashboardGenerator:
    """Generates the main dashboard page."""

    def __init__(
        self,
        templates_dir: Path,
        output_dir: Path,
        base_url: str = "",
    ):
        """
        Initialize dashboard generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
            output_dir: Directory for output HTML files
            base_url: Base URL for the site
        """
        self.templates_dir = Path(templates_dir)
        self.output_dir = Path(output_dir)
        self.base_url = base_url.rstrip("/")

        # Set up Jinja2
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True,
        )

        # Add custom filters
        self.env.filters["format_number"] = format_number

    def generate_dashboard(
        self,
        models_data: list[dict[str, Any]],
    ) -> Path:
        """
        Generate the main dashboard page.

        Args:
            models_data: List of model data dictionaries with scan results

        Returns:
            Path to generated index.html
        """
        logger.info(f"Generating dashboard with {len(models_data)} models")

        # Calculate summary stats
        total_vulns = sum(
            m.get("vulnerabilities", {}).get("summary", {}).get("total", 0)
            for m in models_data
        )

        trust_scores = [m.get("trust_score", 0) for m in models_data if m.get("trust_score")]
        avg_trust = round(sum(trust_scores) / len(trust_scores)) if trust_scores else 0

        models_with_issues = sum(
            1 for m in models_data
            if m.get("vulnerabilities", {}).get("summary", {}).get("critical", 0) > 0
            or m.get("vulnerabilities", {}).get("summary", {}).get("high", 0) > 0
        )

        # Prepare model cards data
        model_cards = []
        for model in models_data:
            model_cards.append({
                "model_id": model.get("model_id", "unknown"),
                "model_name": model.get("model_name", "Unknown"),
                "author": model.get("author", "Unknown"),
                "safe_id": model.get("model_id", "unknown").replace("/", "_"),
                "downloads": model.get("downloads", 0),
                "downloads_formatted": format_number(model.get("downloads", 0)),
                "likes": model.get("likes", 0),
                "likes_formatted": format_number(model.get("likes", 0)),
                "vuln_count": model.get("vulnerabilities", {}).get("summary", {}).get("total", 0),
                "trust_score": model.get("trust_score", 0),
                "trust_grade": model.get("trust_grade", "?"),
                "trust_grade_class": get_trust_grade_class(model.get("trust_score", 0)),
                "pipeline_tag": model.get("pipeline_tag"),
                "library_name": model.get("library_name"),
                "has_safetensors": model.get("has_safetensors", False),
            })

        # Sort by downloads (should already be sorted, but ensure)
        model_cards.sort(key=lambda x: x["downloads"], reverse=True)

        # Prepare template context
        context = {
            "base_url": self.base_url,
            "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
            "total_models": len(models_data),
            "total_vulnerabilities": total_vulns,
            "avg_trust_score": avg_trust,
            "models_with_issues": models_with_issues,
            "models": model_cards,
        }

        # Render template
        template = self.env.get_template("dashboard.html")
        html_content = template.render(**context)

        # Write HTML file
        self.output_dir.mkdir(parents=True, exist_ok=True)
        html_file = self.output_dir / "index.html"
        html_file.write_text(html_content)

        logger.info(f"Dashboard generated: {html_file}")
        return html_file

    def generate_api_json(
        self,
        models_data: list[dict[str, Any]],
    ) -> Path:
        """
        Generate JSON API file with all models data.

        Args:
            models_data: List of model data dictionaries

        Returns:
            Path to generated JSON file
        """
        api_dir = self.output_dir / "api"
        api_dir.mkdir(parents=True, exist_ok=True)

        # Generate summary JSON
        summary = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total_models": len(models_data),
            "models": [
                {
                    "model_id": m.get("model_id"),
                    "author": m.get("author"),
                    "model_name": m.get("model_name"),
                    "downloads": m.get("downloads"),
                    "likes": m.get("likes"),
                    "trust_score": m.get("trust_score"),
                    "trust_grade": m.get("trust_grade"),
                    "vulnerability_count": m.get("vulnerabilities", {}).get("summary", {}).get("total", 0),
                    "critical_count": m.get("vulnerabilities", {}).get("summary", {}).get("critical", 0),
                    "high_count": m.get("vulnerabilities", {}).get("summary", {}).get("high", 0),
                    "has_safetensors": m.get("has_safetensors"),
                    "license": m.get("license"),
                    "report_url": f"/reports/{m.get('model_id', '').replace('/', '_')}/index.html",
                }
                for m in models_data
            ],
        }

        json_file = api_dir / "models.json"
        json_file.write_text(json.dumps(summary, indent=2))

        logger.info(f"API JSON generated: {json_file}")
        return json_file

    def generate_about_page(self) -> Path:
        """Generate the about page."""
        about_content = """{% extends "base.html" %}

{% block title %}About - HuggingHugh{% endblock %}

{% block content %}
<div class="container">
    <div class="page-header">
        <h1>About HuggingHugh</h1>
        <p class="subtitle">Nutrition Labels for AI Models</p>
    </div>

    <div class="card" style="margin-bottom: var(--space-xl);">
        <div class="card-body">
            <h2 style="margin-bottom: var(--space-md);">What is this?</h2>
            <p style="margin-bottom: var(--space-md);">
                HuggingHugh provides Software Bill of Materials (SBOM) reports for the most popular
                models on HuggingFace Hub. Think of it as <strong>nutrition labels for AI models</strong> —
                helping you understand what dependencies, vulnerabilities, and licenses are involved
                before you integrate a model into your project.
            </p>
            <p>
                Just like food nutrition labels help you make informed dietary choices, HuggingHugh
                helps you make informed decisions about the AI models you consume.
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: var(--space-xl);">
        <div class="card-body">
            <h2 style="margin-bottom: var(--space-md);">What's in a report?</h2>
            <ul style="padding-left: var(--space-lg); line-height: 1.8;">
                <li><strong>Trust Score (0-100)</strong> — An overall assessment based on security, licensing, and quality factors</li>
                <li><strong>Vulnerability Scan</strong> — CVEs found in inferred dependencies (via Grype)</li>
                <li><strong>License Analysis</strong> — Model license, commercial use permissions, copyleft risks</li>
                <li><strong>SBOM Components</strong> — Full list of inferred dependencies in CycloneDX format</li>
                <li><strong>Security Indicators</strong> — SafeTensors usage, verified organization status</li>
            </ul>
        </div>
    </div>

    <div class="card" style="margin-bottom: var(--space-xl);">
        <div class="card-body">
            <h2 style="margin-bottom: var(--space-md);">Methodology</h2>
            <p style="margin-bottom: var(--space-md);">
                For each model, we:
            </p>
            <ol style="padding-left: var(--space-lg); line-height: 1.8;">
                <li>Fetch metadata from the HuggingFace Hub API</li>
                <li>Infer dependencies based on the library (transformers, diffusers, etc.) and model architecture</li>
                <li>Generate an SBOM using Syft</li>
                <li>Scan for vulnerabilities using Grype</li>
                <li>Analyze the license from model card data</li>
                <li>Calculate a trust score based on multiple factors</li>
            </ol>
            <p style="margin-top: var(--space-md); color: var(--text-muted);">
                <strong>Note:</strong> Dependency inference is not perfect. The actual dependencies may vary
                based on your specific environment and usage patterns.
            </p>
        </div>
    </div>

    <div class="card" style="margin-bottom: var(--space-xl);">
        <div class="card-body">
            <h2 style="margin-bottom: var(--space-md);">Trust Score Factors</h2>
            <table class="vuln-table">
                <thead>
                    <tr>
                        <th>Factor</th>
                        <th>Weight</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>No Critical/High CVEs</td>
                        <td>20%</td>
                        <td>Dependencies free of critical and high severity vulnerabilities</td>
                    </tr>
                    <tr>
                        <td>Verified Organization</td>
                        <td>15%</td>
                        <td>Published by a known, verified organization (Meta, Google, etc.)</td>
                    </tr>
                    <tr>
                        <td>SafeTensors Format</td>
                        <td>15%</td>
                        <td>Uses secure safetensors format instead of pickle-based files</td>
                    </tr>
                    <tr>
                        <td>Clear License</td>
                        <td>15%</td>
                        <td>License is clearly specified and appropriate for use</td>
                    </tr>
                    <tr>
                        <td>No Pickle Files</td>
                        <td>10%</td>
                        <td>Does not contain pickle files (arbitrary code execution risk)</td>
                    </tr>
                    <tr>
                        <td>Model Card Quality</td>
                        <td>10%</td>
                        <td>Has comprehensive documentation (README, config, tags)</td>
                    </tr>
                    <tr>
                        <td>Recent Updates</td>
                        <td>10%</td>
                        <td>Model has been updated within the last 90 days</td>
                    </tr>
                    <tr>
                        <td>Community Engagement</td>
                        <td>5%</td>
                        <td>Downloads and likes indicate community trust</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div class="card" style="background: linear-gradient(135deg, #fef3c7 0%, #fff7ed 100%);">
        <div class="card-body" style="text-align: center; padding: var(--space-2xl);">
            <h2 style="margin-bottom: var(--space-md);">Support This Project</h2>
            <p style="color: var(--text-muted); margin-bottom: var(--space-lg); max-width: 500px; margin-left: auto; margin-right: auto;">
                HuggingHugh is a free community resource. Running daily scans and hosting costs money.
                If you find this useful, consider buying me a coffee!
            </p>
            <a href="https://buymeacoffee.com/hugginghugh" target="_blank" class="btn btn-coffee" style="font-size: 1.125rem; padding: var(--space-md) var(--space-xl);">
                ☕ Buy me a coffee
            </a>
        </div>
    </div>
</div>
{% endblock %}
"""
        # Write template temporarily and render
        about_template = self.templates_dir / "about.html"
        about_template.write_text(about_content)

        template = self.env.get_template("about.html")
        html_content = template.render(
            base_url=self.base_url,
            last_updated=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        )

        html_file = self.output_dir / "about.html"
        html_file.write_text(html_content)

        logger.info(f"About page generated: {html_file}")
        return html_file
