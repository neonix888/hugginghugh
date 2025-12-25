"""
Trust Score Calculator

Calculates a trust score (0-100) for ML models based on various factors.
Weights are calibrated based on real-world security incidents and best practices.
"""
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Trust score weights (must sum to 100)
# Calibrated for security-first assessment:
# - Security factors: 50 points (format safety, CVEs, pickle)
# - Provenance factors: 25 points (verified org, license)
# - Quality factors: 25 points (docs, recency, community)
WEIGHTS = {
    "verified_org": 12,          # Provenance: known publisher
    "safetensors_format": 18,    # Security: safe serialization (high weight due to CVE-2025-32434)
    "no_critical_cves": 15,      # Security: vulnerability-free dependencies
    "clear_license": 13,         # Provenance: usage rights
    "model_card_quality": 10,    # Quality: documentation
    "recent_updates": 8,         # Quality: maintenance status
    "community_engagement": 6,   # Quality: adoption signals
    "no_pickle_files": 18,       # Security: no arbitrary code execution risk
}

# Known well-maintained organizations (partial credit if not officially verified)
KNOWN_TRUSTWORTHY_ORGS = [
    # Major AI labs
    "meta-llama", "meta", "facebook", "openai", "google", "deepmind",
    "microsoft", "nvidia", "amazon", "alibaba", "baidu", "tencent",
    # HuggingFace ecosystem
    "huggingface", "bigscience", "bigcode", "sentence-transformers",
    # AI research orgs
    "stabilityai", "stability-ai", "runwayml", "compvis", "laion",
    "eleutherai", "togethercomputer", "together", "mistralai", "mistral-ai",
    # Model-specific well-known publishers
    "qwen", "deepseek-ai", "thudm", "internlm", "baichuan-inc",
    "01-ai", "cohere", "anthropic", "allenai", "berkeley-nest",
    "lmsys", "teknium", "openchat", "nousresearch", "cognitivecomputations",
    # Vision/Multimodal specialists
    "timm", "openclip", "salesforce", "clip-benchmark",
    # Audio specialists
    "openai-whisper", "pyannote", "speechbrain", "coqui",
    # RL/Robotics
    "cleanrl", "stable-baselines", "huggingface-rl",
]


@dataclass
class TrustFactor:
    """Individual trust factor assessment."""

    name: str
    weight: int
    score: float  # 0.0 to 1.0
    points: float  # score * weight
    reason: str
    status: str  # "pass", "warn", "fail"
    tooltip: str = ""  # Explanation of how this factor is calculated


@dataclass
class TrustScore:
    """Overall trust score with breakdown."""

    total_score: int  # 0 to 100
    grade: str  # A, B, C, D, F
    factors: list[TrustFactor]
    summary: str

    @property
    def color(self) -> str:
        """Get color for the score."""
        if self.total_score >= 80:
            return "#22c55e"  # green
        elif self.total_score >= 60:
            return "#eab308"  # yellow
        elif self.total_score >= 40:
            return "#f97316"  # orange
        else:
            return "#ef4444"  # red


class TrustScorer:
    """Calculates trust scores for ML models."""

    def __init__(self, weights: Optional[dict] = None):
        """
        Initialize trust scorer.

        Args:
            weights: Custom weights dictionary (must sum to 100)
        """
        self.weights = weights or WEIGHTS

        # Validate weights sum to 100
        total = sum(self.weights.values())
        if total != 100:
            logger.warning(f"Trust weights sum to {total}, normalizing...")
            factor = 100 / total
            self.weights = {k: v * factor for k, v in self.weights.items()}

    def calculate_score(
        self,
        model_metadata: dict,
        vuln_results: dict,
        license_analysis: dict,
    ) -> TrustScore:
        """
        Calculate trust score for a model.

        Args:
            model_metadata: Model metadata from fetcher
            vuln_results: Vulnerability scan results
            license_analysis: License analysis results

        Returns:
            TrustScore object with breakdown
        """
        factors = []

        # 1. Verified Organization (15 points)
        factors.append(self._score_verified_org(model_metadata))

        # 2. SafeTensors Format (15 points)
        factors.append(self._score_safetensors(model_metadata))

        # 3. No Critical CVEs (20 points)
        factors.append(self._score_vulnerabilities(vuln_results))

        # 4. Clear License (15 points)
        factors.append(self._score_license(license_analysis))

        # 5. Model Card Quality (10 points)
        factors.append(self._score_model_card(model_metadata))

        # 6. Recent Updates (10 points)
        factors.append(self._score_recency(model_metadata))

        # 7. Community Engagement (5 points)
        factors.append(self._score_community(model_metadata))

        # 8. No Pickle Files (10 points)
        factors.append(self._score_no_pickle(model_metadata))

        # Calculate total
        total_points = sum(f.points for f in factors)
        total_score = min(100, max(0, round(total_points)))

        # Determine grade
        grade = self._get_grade(total_score)

        # Generate summary
        summary = self._generate_summary(factors, total_score)

        return TrustScore(
            total_score=total_score,
            grade=grade,
            factors=factors,
            summary=summary,
        )

    def _score_verified_org(self, metadata: dict) -> TrustFactor:
        """Score based on organization verification and reputation."""
        weight = self.weights["verified_org"]
        is_verified = metadata.get("is_verified_org", False)
        author = metadata.get("author", "")
        author_lower = author.lower()

        tooltip = (
            f"Max {weight} points. Verified orgs on HuggingFace have been vetted "
            "and display a verification badge. Full points for verified orgs, "
            "85% for well-known AI labs/publishers, 40% for unknown publishers."
        )

        # Check if verified by HuggingFace
        if is_verified:
            return TrustFactor(
                name="Verified Organization",
                weight=weight,
                score=1.0,
                points=weight,
                reason=f"Published by verified org: {author}",
                status="pass",
                tooltip=tooltip,
            )

        # Check against our expanded list of known trustworthy orgs
        is_known = any(
            known_org in author_lower or author_lower in known_org
            for known_org in KNOWN_TRUSTWORTHY_ORGS
        )

        if is_known:
            return TrustFactor(
                name="Verified Organization",
                weight=weight,
                score=0.85,
                points=weight * 0.85,
                reason=f"Well-known AI publisher: {author}",
                status="pass",
                tooltip=tooltip,
            )

        # Check downloads as a proxy for reputation (>1M suggests established publisher)
        downloads = metadata.get("downloads", 0)
        if downloads >= 1_000_000:
            return TrustFactor(
                name="Verified Organization",
                weight=weight,
                score=0.6,
                points=weight * 0.6,
                reason=f"Publisher {author} has high-download models",
                status="warn",
                tooltip=tooltip,
            )

        # Unknown publisher
        return TrustFactor(
            name="Verified Organization",
            weight=weight,
            score=0.4,
            points=weight * 0.4,
            reason=f"Publisher not verified: {author}",
            status="warn",
            tooltip=tooltip,
        )

    def _score_safetensors(self, metadata: dict) -> TrustFactor:
        """Score based on safe serialization format usage."""
        weight = self.weights["safetensors_format"]
        has_safetensors = metadata.get("has_safetensors", False)
        has_pickle = metadata.get("has_pickle", False)

        # Check for other safe formats from file list
        siblings = metadata.get("siblings", [])
        file_names = [s.get("rfilename", "") for s in siblings if isinstance(s, dict)]
        has_gguf = any(f.endswith(".gguf") for f in file_names)
        has_onnx = any(f.endswith(".onnx") for f in file_names)

        # GGUF and ONNX are also safe formats (no arbitrary code execution)
        has_safe_format = has_safetensors or has_gguf or has_onnx

        tooltip = (
            f"Max {weight} points. Safe formats (safetensors, GGUF, ONNX) prevent "
            "arbitrary code execution. Full points for safe formats only, "
            "70% if both safe and unsafe formats exist, 0% if only pickle/bin files."
        )

        if has_safe_format and not has_pickle:
            format_name = "safetensors" if has_safetensors else ("GGUF" if has_gguf else "ONNX")
            return TrustFactor(
                name="Safe Serialization",
                weight=weight,
                score=1.0,
                points=weight,
                reason=f"Uses secure {format_name} format exclusively",
                status="pass",
                tooltip=tooltip,
            )
        elif has_safe_format and has_pickle:
            return TrustFactor(
                name="Safe Serialization",
                weight=weight,
                score=0.7,
                points=weight * 0.7,
                reason="Has safe format but also contains pickle files",
                status="warn",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="Safe Serialization",
                weight=weight,
                score=0.0,
                points=0,
                reason="Uses pickle-based format only (code execution risk)",
                status="fail",
                tooltip=tooltip,
            )

    def _score_vulnerabilities(self, vuln_results: dict) -> TrustFactor:
        """Score based on vulnerability count."""
        weight = self.weights["no_critical_cves"]
        summary = vuln_results.get("summary", {})

        critical = summary.get("critical", 0)
        high = summary.get("high", 0)
        medium = summary.get("medium", 0)
        tooltip = (
            f"Max {weight} points. Based on CVE vulnerabilities in dependencies. "
            "Full points if no critical/high CVEs, 70% if 1-2 high, "
            "40% if 1-2 critical, 0% if 3+ critical vulnerabilities."
        )

        if critical == 0 and high == 0:
            return TrustFactor(
                name="No Critical/High CVEs",
                weight=weight,
                score=1.0,
                points=weight,
                reason="No critical or high severity vulnerabilities",
                status="pass",
                tooltip=tooltip,
            )
        elif critical == 0 and high <= 2:
            return TrustFactor(
                name="No Critical/High CVEs",
                weight=weight,
                score=0.7,
                points=weight * 0.7,
                reason=f"{high} high severity vulnerabilities found",
                status="warn",
                tooltip=tooltip,
            )
        elif critical <= 2:
            return TrustFactor(
                name="No Critical/High CVEs",
                weight=weight,
                score=0.4,
                points=weight * 0.4,
                reason=f"{critical} critical, {high} high severity vulnerabilities",
                status="warn",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="No Critical/High CVEs",
                weight=weight,
                score=0.0,
                points=0,
                reason=f"{critical} critical vulnerabilities found!",
                status="fail",
                tooltip=tooltip,
            )

    def _score_license(self, license_analysis: dict) -> TrustFactor:
        """Score based on license clarity."""
        weight = self.weights["clear_license"]
        model_license = license_analysis.get("model", {})

        category = model_license.get("category", "unknown")
        commercial = model_license.get("commercial_use", False)
        tooltip = (
            f"Max {weight} points. Evaluates license clarity and usage rights. "
            "Full points for permissive licenses (MIT, Apache), 80% for commercial-friendly, "
            "40% for restrictive, 0% if no license specified."
        )

        if category == "unknown":
            return TrustFactor(
                name="Clear License",
                weight=weight,
                score=0.0,
                points=0,
                reason="License not specified",
                status="fail",
                tooltip=tooltip,
            )
        elif category == "permissive":
            return TrustFactor(
                name="Clear License",
                weight=weight,
                score=1.0,
                points=weight,
                reason=f"Permissive license: {model_license.get('name', 'Unknown')}",
                status="pass",
                tooltip=tooltip,
            )
        elif commercial:
            return TrustFactor(
                name="Clear License",
                weight=weight,
                score=0.8,
                points=weight * 0.8,
                reason=f"Commercial use allowed: {model_license.get('name', 'Unknown')}",
                status="pass",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="Clear License",
                weight=weight,
                score=0.4,
                points=weight * 0.4,
                reason=f"Restrictive license: {model_license.get('name', 'Unknown')}",
                status="warn",
                tooltip=tooltip,
            )

    def _score_model_card(self, metadata: dict) -> TrustFactor:
        """Score based on model card quality."""
        weight = self.weights["model_card_quality"]
        downloaded_files = metadata.get("downloaded_files", [])

        has_readme = "README.md" in downloaded_files
        has_config = "config.json" in downloaded_files
        card_data = metadata.get("card_data", {})

        # Check for important model card sections
        has_description = bool(card_data.get("description") or card_data.get("summary"))
        has_tags = len(metadata.get("tags", [])) > 2

        quality_score = sum([
            0.3 if has_readme else 0,
            0.2 if has_config else 0,
            0.3 if has_description else 0,
            0.2 if has_tags else 0,
        ])
        tooltip = (
            f"Max {weight} points. Checks for README (30%), config.json (20%), "
            "description (30%), and tags (20%). Full points if score >= 80%, "
            "60% if >= 50%, otherwise 20%."
        )

        if quality_score >= 0.8:
            return TrustFactor(
                name="Model Card Quality",
                weight=weight,
                score=1.0,
                points=weight,
                reason="Comprehensive documentation",
                status="pass",
                tooltip=tooltip,
            )
        elif quality_score >= 0.5:
            return TrustFactor(
                name="Model Card Quality",
                weight=weight,
                score=0.6,
                points=weight * 0.6,
                reason="Basic documentation present",
                status="warn",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="Model Card Quality",
                weight=weight,
                score=0.2,
                points=weight * 0.2,
                reason="Missing or minimal documentation",
                status="fail",
                tooltip=tooltip,
            )

    def _score_recency(self, metadata: dict) -> TrustFactor:
        """Score based on last update time."""
        weight = self.weights["recent_updates"]
        last_modified = metadata.get("last_modified")
        tooltip = (
            f"Max {weight} points. Based on last update date. "
            "Full points if updated within 30 days, 70% within 90 days, "
            "50% within 180 days, 20% if older."
        )

        if not last_modified:
            return TrustFactor(
                name="Recent Updates",
                weight=weight,
                score=0.5,
                points=weight * 0.5,
                reason="Update date unknown",
                status="warn",
                tooltip=tooltip,
            )

        # Parse date
        if isinstance(last_modified, str):
            try:
                last_modified = datetime.fromisoformat(last_modified.replace("Z", "+00:00"))
            except ValueError:
                return TrustFactor(
                    name="Recent Updates",
                    weight=weight,
                    score=0.5,
                    points=weight * 0.5,
                    reason="Update date format unknown",
                    status="warn",
                    tooltip=tooltip,
                )

        now = datetime.now(timezone.utc)
        age_days = (now - last_modified).days

        if age_days <= 30:
            return TrustFactor(
                name="Recent Updates",
                weight=weight,
                score=1.0,
                points=weight,
                reason=f"Updated {age_days} days ago",
                status="pass",
                tooltip=tooltip,
            )
        elif age_days <= 90:
            return TrustFactor(
                name="Recent Updates",
                weight=weight,
                score=0.7,
                points=weight * 0.7,
                reason=f"Updated {age_days} days ago",
                status="pass",
                tooltip=tooltip,
            )
        elif age_days <= 180:
            return TrustFactor(
                name="Recent Updates",
                weight=weight,
                score=0.5,
                points=weight * 0.5,
                reason=f"Updated {age_days} days ago",
                status="warn",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="Recent Updates",
                weight=weight,
                score=0.2,
                points=weight * 0.2,
                reason=f"Not updated in {age_days} days",
                status="warn",
                tooltip=tooltip,
            )

    def _score_community(self, metadata: dict) -> TrustFactor:
        """Score based on community engagement."""
        weight = self.weights["community_engagement"]
        downloads = metadata.get("downloads", 0)
        likes = metadata.get("likes", 0)

        # Normalize scores (log scale for downloads)
        import math
        download_score = min(1.0, math.log10(max(1, downloads)) / 7)  # 10M = 1.0
        like_score = min(1.0, likes / 1000)  # 1000 likes = 1.0

        combined = (download_score * 0.7) + (like_score * 0.3)
        tooltip = (
            f"Max {weight} points. Combined score: 70% downloads (log scale, 10M=100%) "
            "+ 30% likes (1000=100%). Full points if combined >= 80%, "
            "70% if >= 50%, otherwise proportional."
        )

        if combined >= 0.8:
            return TrustFactor(
                name="Community Engagement",
                weight=weight,
                score=1.0,
                points=weight,
                reason=f"{downloads:,} downloads, {likes:,} likes",
                status="pass",
                tooltip=tooltip,
            )
        elif combined >= 0.5:
            return TrustFactor(
                name="Community Engagement",
                weight=weight,
                score=0.7,
                points=weight * 0.7,
                reason=f"{downloads:,} downloads, {likes:,} likes",
                status="pass",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="Community Engagement",
                weight=weight,
                score=combined,
                points=weight * combined,
                reason=f"{downloads:,} downloads, {likes:,} likes",
                status="warn",
                tooltip=tooltip,
            )

    def _score_no_pickle(self, metadata: dict) -> TrustFactor:
        """Score based on absence of pickle/unsafe serialization files."""
        weight = self.weights["no_pickle_files"]
        has_pickle = metadata.get("has_pickle", False)
        has_safetensors = metadata.get("has_safetensors", False)

        # Check for safe alternatives
        siblings = metadata.get("siblings", [])
        file_names = [s.get("rfilename", "") for s in siblings if isinstance(s, dict)]
        has_gguf = any(f.endswith(".gguf") for f in file_names)
        has_onnx = any(f.endswith(".onnx") for f in file_names)
        has_safe_alternative = has_safetensors or has_gguf or has_onnx

        tooltip = (
            f"Max {weight} points. Pickle files (.bin, .pt, .pkl) can contain "
            "arbitrary code. Full points if no pickle files, 50% if a safe "
            "alternative (safetensors/GGUF/ONNX) exists, 0% if only pickle."
        )

        if not has_pickle:
            return TrustFactor(
                name="No Pickle Files",
                weight=weight,
                score=1.0,
                points=weight,
                reason="No pickle-based files detected",
                status="pass",
                tooltip=tooltip,
            )
        elif has_safe_alternative:
            return TrustFactor(
                name="No Pickle Files",
                weight=weight,
                score=0.5,
                points=weight * 0.5,
                reason="Pickle files present (safe alternative available)",
                status="warn",
                tooltip=tooltip,
            )
        else:
            return TrustFactor(
                name="No Pickle Files",
                weight=weight,
                score=0.0,
                points=0,
                reason="Contains only pickle files (code execution risk)",
                status="fail",
                tooltip=tooltip,
            )

    def _get_grade(self, score: int) -> str:
        """Convert score to letter grade."""
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

    def _generate_summary(self, factors: list[TrustFactor], score: int) -> str:
        """Generate a human-readable summary."""
        failed = [f for f in factors if f.status == "fail"]
        warnings = [f for f in factors if f.status == "warn"]
        passed = [f for f in factors if f.status == "pass"]

        if score >= 80:
            base = "This model has a high trust score."
        elif score >= 60:
            base = "This model has a moderate trust score."
        elif score >= 40:
            base = "This model has a low trust score."
        else:
            base = "This model has significant trust concerns."

        # Show factor breakdown instead of confusing "critical/warning" language
        base += f" {len(passed)} of {len(factors)} factors passed."

        return base
