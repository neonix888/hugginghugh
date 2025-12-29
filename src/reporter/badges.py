"""
Badge Generator for HuggingHugh.

Generates embeddable SVG badges for model trust scores.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Badge color scheme based on grade
GRADE_COLORS = {
    "A": {"bg": "#22c55e", "label": "Trust Score"},  # Green
    "B": {"bg": "#84cc16", "label": "Trust Score"},  # Lime
    "C": {"bg": "#eab308", "label": "Trust Score"},  # Yellow
    "D": {"bg": "#f97316", "label": "Trust Score"},  # Orange
    "F": {"bg": "#ef4444", "label": "Trust Score"},  # Red
}

# SVG badge template (shields.io style)
BADGE_SVG_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{aria_label}">
  <title>{title}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{value_width}" height="20" fill="{color}"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{label_x}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{label}</text>
    <text x="{label_x}" y="140" transform="scale(.1)" fill="#fff">{label}</text>
    <text aria-hidden="true" x="{value_x}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{value}</text>
    <text x="{value_x}" y="140" transform="scale(.1)" fill="#fff">{value}</text>
  </g>
</svg>"""

# Compact badge (just score)
BADGE_COMPACT_TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" aria-label="{aria_label}">
  <title>{title}</title>
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{width}" height="20" fill="{color}"/>
    <rect width="{width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{center_x}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)">{value}</text>
    <text x="{center_x}" y="140" transform="scale(.1)" fill="#fff">{value}</text>
  </g>
</svg>"""


def calculate_text_width(text: str) -> int:
    """Estimate text width in pixels for SVG."""
    # Approximate character widths for Verdana at font-size 11
    char_widths = {
        "i": 4,
        "l": 4,
        "I": 5,
        "1": 6,
        "t": 5,
        "f": 5,
        "r": 5,
        "j": 4,
        " ": 4,
        ".": 4,
        "-": 5,
        ":": 4,
    }
    width = 0
    for char in text:
        if char in char_widths:
            width += char_widths[char]
        elif char.isupper():
            width += 8
        elif char.isdigit():
            width += 7
        else:
            width += 7
    return width + 10  # Add padding


def generate_badge_svg(
    label: str,
    value: str,
    color: str,
    style: str = "default",
) -> str:
    """
    Generate a shields.io-style SVG badge.

    Args:
        label: Left side text (e.g., "HuggingHugh")
        value: Right side text (e.g., "A 92")
        color: Background color for value section
        style: "default" or "compact"

    Returns:
        SVG string
    """
    if style == "compact":
        width = calculate_text_width(value) + 10
        return BADGE_COMPACT_TEMPLATE.format(
            width=width,
            color=color,
            value=value,
            center_x=width * 5,  # Multiply by 10 for transform scale, divide by 2 for center
            aria_label=f"HuggingHugh: {value}",
            title=f"HuggingHugh Trust Score: {value}",
        )

    label_width = calculate_text_width(label)
    value_width = calculate_text_width(value)
    total_width = label_width + value_width

    return BADGE_SVG_TEMPLATE.format(
        width=total_width,
        label_width=label_width,
        value_width=value_width,
        color=color,
        label=label,
        value=value,
        label_x=label_width * 5,  # Center of label section (scaled)
        value_x=label_width * 10 + value_width * 5,  # Center of value section (scaled)
        aria_label=f"{label}: {value}",
        title=f"{label}: {value}",
    )


class BadgeGenerator:
    """Generates embeddable badges for model trust scores."""

    def __init__(
        self,
        output_dir: Path,
        site_url: str = "https://hugginghugh.com",
    ):
        """
        Initialize badge generator.

        Args:
            output_dir: Directory for output files
            site_url: Base URL for badge links
        """
        self.output_dir = Path(output_dir)
        self.site_url = site_url.rstrip("/")
        self.badges_dir = self.output_dir / "badges"
        self.api_dir = self.output_dir / "api" / "badges"

    def generate_model_badge(
        self,
        model_id: str,
        trust_score: int,
        trust_grade: str,
    ) -> dict[str, Path]:
        """
        Generate badges for a single model.

        Args:
            model_id: Model identifier (e.g., "meta-llama/Llama-2-7b")
            trust_score: Trust score (0-100)
            trust_grade: Trust grade (A-F)

        Returns:
            Dict of badge type to file path
        """
        safe_id = model_id.replace("/", "_")
        model_dir = self.badges_dir / safe_id
        model_dir.mkdir(parents=True, exist_ok=True)

        color = GRADE_COLORS.get(trust_grade, GRADE_COLORS["F"])["bg"]

        badges = {}

        # Full badge with label
        full_svg = generate_badge_svg(
            label="HuggingHugh",
            value=f"{trust_grade} {trust_score}",
            color=color,
        )
        full_path = model_dir / "badge.svg"
        full_path.write_text(full_svg)
        badges["full"] = full_path

        # Grade-only badge
        grade_svg = generate_badge_svg(
            label="HuggingHugh",
            value=trust_grade,
            color=color,
        )
        grade_path = model_dir / "grade.svg"
        grade_path.write_text(grade_svg)
        badges["grade"] = grade_path

        # Score-only badge
        score_svg = generate_badge_svg(
            label="Trust Score",
            value=str(trust_score),
            color=color,
        )
        score_path = model_dir / "score.svg"
        score_path.write_text(score_svg)
        badges["score"] = score_path

        # Compact badge (just grade + score, no label)
        compact_svg = generate_badge_svg(
            label="",
            value=f"{trust_grade} {trust_score}",
            color=color,
            style="compact",
        )
        compact_path = model_dir / "compact.svg"
        compact_path.write_text(compact_svg)
        badges["compact"] = compact_path

        return badges

    def generate_badge_json(
        self,
        model_id: str,
        trust_score: int,
        trust_grade: str,
    ) -> Path:
        """
        Generate JSON endpoint for shields.io dynamic badges.

        Shields.io endpoint format:
        https://img.shields.io/endpoint?url=https://hugginghugh.com/api/badges/{safe_id}.json

        Args:
            model_id: Model identifier
            trust_score: Trust score (0-100)
            trust_grade: Trust grade (A-F)

        Returns:
            Path to JSON file
        """
        safe_id = model_id.replace("/", "_")
        self.api_dir.mkdir(parents=True, exist_ok=True)

        color = GRADE_COLORS.get(trust_grade, GRADE_COLORS["F"])["bg"]

        # Shields.io endpoint schema
        # https://shields.io/endpoint
        badge_data = {
            "schemaVersion": 1,
            "label": "HuggingHugh",
            "message": f"{trust_grade} {trust_score}",
            "color": color.lstrip("#"),
            "labelColor": "555",
            "style": "flat",
            "namedLogo": "huggingface",
            "logoColor": "white",
        }

        json_path = self.api_dir / f"{safe_id}.json"
        json_path.write_text(json.dumps(badge_data, indent=2))

        return json_path

    def generate_all_badges(
        self,
        models_data: list[dict[str, Any]],
    ) -> int:
        """
        Generate badges for all models.

        Args:
            models_data: List of model data dictionaries

        Returns:
            Number of badges generated
        """
        count = 0

        for model in models_data:
            model_id = model.get("model_id", "")
            trust_score = model.get("trust_score", 0)
            trust_grade = model.get("trust_grade", "F")

            if not model_id:
                continue

            try:
                self.generate_model_badge(model_id, trust_score, trust_grade)
                self.generate_badge_json(model_id, trust_score, trust_grade)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to generate badge for {model_id}: {e}")

        logger.info(f"Generated badges for {count} models")
        return count

    def get_embed_code(
        self,
        model_id: str,
        style: str = "markdown",
        badge_type: str = "full",
    ) -> str:
        """
        Generate embed code for a badge.

        Args:
            model_id: Model identifier
            style: "markdown", "html", or "shields"
            badge_type: "full", "grade", "score", or "compact"

        Returns:
            Embed code string
        """
        safe_id = model_id.replace("/", "_")
        report_url = f"{self.site_url}/reports/{safe_id}/"

        if style == "shields":
            # Dynamic shields.io badge
            endpoint = f"{self.site_url}/api/badges/{safe_id}.json"
            badge_url = f"https://img.shields.io/endpoint?url={endpoint}"
        else:
            # Static SVG badge
            badge_url = f"{self.site_url}/badges/{safe_id}/{badge_type}.svg"

        if style == "markdown":
            return f"[![HuggingHugh Trust Score]({badge_url})]({report_url})"
        elif style == "html":
            return (
                f'<a href="{report_url}"><img src="{badge_url}" alt="HuggingHugh Trust Score"></a>'
            )
        elif style == "shields":
            return f"[![HuggingHugh Trust Score]({badge_url})]({report_url})"
        else:
            return badge_url
