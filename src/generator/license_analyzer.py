"""
License Analyzer

Analyzes licenses from model metadata and SBOM components.
"""
import logging
import re
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# License classifications
PERMISSIVE_LICENSES = {
    "mit": "MIT",
    "apache-2.0": "Apache 2.0",
    "apache2": "Apache 2.0",
    "bsd-2-clause": "BSD 2-Clause",
    "bsd-3-clause": "BSD 3-Clause",
    "bsd": "BSD",
    "isc": "ISC",
    "unlicense": "Unlicense",
    "cc0-1.0": "CC0 1.0",
    "wtfpl": "WTFPL",
    "0bsd": "0BSD",
    "zlib": "Zlib",
}

COPYLEFT_LICENSES = {
    "gpl-2.0": "GPL 2.0",
    "gpl-3.0": "GPL 3.0",
    "gpl": "GPL",
    "lgpl-2.1": "LGPL 2.1",
    "lgpl-3.0": "LGPL 3.0",
    "lgpl": "LGPL",
    "agpl-3.0": "AGPL 3.0",
    "agpl": "AGPL",
    "mpl-2.0": "MPL 2.0",
}

# Model-specific licenses (often restrictive)
MODEL_LICENSES = {
    "llama2": {"name": "Llama 2 Community License", "commercial": True, "restrictions": ["Meta attribution required", "Usage limits for large deployments"]},
    "llama3": {"name": "Llama 3 Community License", "commercial": True, "restrictions": ["Meta attribution required"]},
    "llama3.1": {"name": "Llama 3.1 Community License", "commercial": True, "restrictions": ["Meta attribution required"]},
    "llama-3.2": {"name": "Llama 3.2 Community License", "commercial": True, "restrictions": ["Meta attribution required"]},
    "gemma": {"name": "Gemma Terms of Use", "commercial": True, "restrictions": ["Google terms apply"]},
    "mistral": {"name": "Apache 2.0", "commercial": True, "restrictions": []},
    "qwen": {"name": "Qianwen License", "commercial": True, "restrictions": ["Alibaba terms apply"]},
    "cc-by-nc-4.0": {"name": "CC BY-NC 4.0", "commercial": False, "restrictions": ["Non-commercial use only"]},
    "cc-by-nc-sa-4.0": {"name": "CC BY-NC-SA 4.0", "commercial": False, "restrictions": ["Non-commercial use only", "Share-alike required"]},
    "cc-by-4.0": {"name": "CC BY 4.0", "commercial": True, "restrictions": ["Attribution required"]},
    "openrail": {"name": "OpenRAIL", "commercial": True, "restrictions": ["Responsible AI use required"]},
    "openrail++": {"name": "OpenRAIL++", "commercial": True, "restrictions": ["Responsible AI use required"]},
    "bigscience-openrail-m": {"name": "BigScience OpenRAIL-M", "commercial": True, "restrictions": ["Responsible AI use required"]},
    "bigcode-openrail-m": {"name": "BigCode OpenRAIL-M", "commercial": True, "restrictions": ["Responsible AI use required"]},
    "creativeml-openrail-m": {"name": "CreativeML OpenRAIL-M", "commercial": True, "restrictions": ["Responsible AI use required"]},
}


@dataclass
class LicenseInfo:
    """Structured license information."""

    identifier: str
    name: str
    category: str  # permissive, copyleft, model-specific, proprietary, unknown
    commercial_use: bool
    restrictions: list[str] = field(default_factory=list)
    copyleft_risk: str = "none"  # none, weak, strong
    url: Optional[str] = None


class LicenseAnalyzer:
    """Analyzes licenses for models and their dependencies."""

    def analyze_model_license(self, model_metadata: dict) -> LicenseInfo:
        """
        Analyze the license for a model.

        Args:
            model_metadata: Model metadata dictionary

        Returns:
            LicenseInfo object
        """
        license_id = model_metadata.get("license", "").lower().strip()

        if not license_id:
            # Try to extract from model card
            license_id = self._extract_from_card(model_metadata)

        if not license_id:
            return LicenseInfo(
                identifier="unknown",
                name="Unknown",
                category="unknown",
                commercial_use=False,  # Assume false if unknown
                restrictions=["License not specified - use with caution"],
                copyleft_risk="unknown",
            )

        return self._classify_license(license_id)

    def _extract_from_card(self, model_metadata: dict) -> str:
        """Try to extract license from card data."""
        card_data = model_metadata.get("card_data", {})
        if isinstance(card_data, dict):
            return card_data.get("license", "").lower().strip()
        return ""

    def _classify_license(self, license_id: str) -> LicenseInfo:
        """
        Classify a license identifier.

        Args:
            license_id: License identifier string

        Returns:
            LicenseInfo object
        """
        license_lower = license_id.lower().replace(" ", "-").replace("_", "-")

        # Check permissive licenses
        for key, name in PERMISSIVE_LICENSES.items():
            if key in license_lower:
                return LicenseInfo(
                    identifier=license_id,
                    name=name,
                    category="permissive",
                    commercial_use=True,
                    restrictions=[],
                    copyleft_risk="none",
                    url=f"https://spdx.org/licenses/{license_id}.html",
                )

        # Check copyleft licenses
        for key, name in COPYLEFT_LICENSES.items():
            if key in license_lower:
                risk = "strong" if "gpl" in key and "lgpl" not in key else "weak"
                return LicenseInfo(
                    identifier=license_id,
                    name=name,
                    category="copyleft",
                    commercial_use=True,
                    restrictions=["Derivative works must use same license"],
                    copyleft_risk=risk,
                    url=f"https://spdx.org/licenses/{license_id}.html",
                )

        # Check model-specific licenses
        for key, info in MODEL_LICENSES.items():
            if key in license_lower:
                return LicenseInfo(
                    identifier=license_id,
                    name=info["name"],
                    category="model-specific",
                    commercial_use=info["commercial"],
                    restrictions=info["restrictions"],
                    copyleft_risk="none",
                )

        # Unknown license
        return LicenseInfo(
            identifier=license_id,
            name=license_id.upper(),
            category="other",
            commercial_use=False,  # Assume false if unknown
            restrictions=["Review license terms before use"],
            copyleft_risk="unknown",
        )

    def analyze_sbom_licenses(self, sbom: dict) -> dict:
        """
        Analyze all licenses in an SBOM.

        Args:
            sbom: SBOM dictionary

        Returns:
            License analysis summary
        """
        components = sbom.get("components", [])
        licenses = []
        license_counts = {}
        copyleft_components = []
        unknown_components = []

        for component in components:
            comp_licenses = component.get("licenses", [])
            comp_name = component.get("name", "unknown")

            if not comp_licenses:
                unknown_components.append(comp_name)
                continue

            for lic in comp_licenses:
                if isinstance(lic, dict):
                    lic_info = lic.get("license", {})
                    lic_id = lic_info.get("id") or lic_info.get("name", "")
                else:
                    lic_id = str(lic)

                if lic_id:
                    licenses.append(lic_id)
                    license_counts[lic_id] = license_counts.get(lic_id, 0) + 1

                    # Check for copyleft
                    analyzed = self._classify_license(lic_id)
                    if analyzed.copyleft_risk in ["weak", "strong"]:
                        copyleft_components.append({
                            "component": comp_name,
                            "license": lic_id,
                            "risk": analyzed.copyleft_risk,
                        })

        return {
            "total_components": len(components),
            "components_with_license": len(components) - len(unknown_components),
            "components_without_license": len(unknown_components),
            "unique_licenses": len(set(licenses)),
            "license_distribution": license_counts,
            "copyleft_components": copyleft_components,
            "unknown_license_components": unknown_components,
            "copyleft_risk": "high" if any(
                c["risk"] == "strong" for c in copyleft_components
            ) else "medium" if copyleft_components else "low",
        }

    def get_license_summary(
        self,
        model_license: LicenseInfo,
        sbom_analysis: dict,
    ) -> dict:
        """
        Generate a combined license summary.

        Args:
            model_license: Model license info
            sbom_analysis: SBOM license analysis

        Returns:
            Combined summary dictionary
        """
        return {
            "model": {
                "license": model_license.identifier,
                "name": model_license.name,
                "category": model_license.category,
                "commercial_use": model_license.commercial_use,
                "restrictions": model_license.restrictions,
                "copyleft_risk": model_license.copyleft_risk,
            },
            "dependencies": {
                "total_components": sbom_analysis["total_components"],
                "with_license": sbom_analysis["components_with_license"],
                "without_license": sbom_analysis["components_without_license"],
                "unique_licenses": sbom_analysis["unique_licenses"],
                "copyleft_risk": sbom_analysis["copyleft_risk"],
                "copyleft_count": len(sbom_analysis["copyleft_components"]),
            },
            "overall_assessment": self._assess_overall(model_license, sbom_analysis),
        }

    def _assess_overall(
        self,
        model_license: LicenseInfo,
        sbom_analysis: dict,
    ) -> dict:
        """Generate overall license assessment."""
        issues = []
        risk_level = "low"

        # Model license issues
        if model_license.category == "unknown":
            issues.append("Model license not specified")
            risk_level = "high"
        elif not model_license.commercial_use:
            issues.append("Model not licensed for commercial use")
            risk_level = "medium"
        elif model_license.restrictions:
            issues.append(f"Model has restrictions: {', '.join(model_license.restrictions)}")

        # Dependency issues
        if sbom_analysis["copyleft_risk"] == "high":
            issues.append("Strong copyleft dependencies detected (GPL)")
            risk_level = "high"
        elif sbom_analysis["copyleft_risk"] == "medium":
            issues.append("Weak copyleft dependencies detected (LGPL/MPL)")
            if risk_level == "low":
                risk_level = "medium"

        if sbom_analysis["components_without_license"] > 5:
            issues.append(f"{sbom_analysis['components_without_license']} dependencies have unknown licenses")
            if risk_level == "low":
                risk_level = "medium"

        return {
            "risk_level": risk_level,
            "issues": issues,
            "commercial_safe": (
                model_license.commercial_use and
                sbom_analysis["copyleft_risk"] != "high"
            ),
        }
