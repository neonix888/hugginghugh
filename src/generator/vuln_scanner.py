"""
Vulnerability Scanner

Scans SBOMs for vulnerabilities using Grype.
"""
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class VulnerabilityScanner:
    """Scans SBOMs for vulnerabilities using Grype."""

    def __init__(
        self,
        grype_path: str = "grype",
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize vulnerability scanner.

        Args:
            grype_path: Path to grype executable
            output_dir: Directory for scan results
        """
        self.grype_path = grype_path
        self.output_dir = Path(output_dir) if output_dir else Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Verify grype is available
        self._verify_grype()

    def _verify_grype(self):
        """Verify grype is installed and accessible."""
        try:
            result = subprocess.run(
                [self.grype_path, "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.debug(f"Grype version: {result.stdout.strip()}")
            else:
                raise RuntimeError(f"Grype error: {result.stderr}")
        except FileNotFoundError:
            raise RuntimeError(f"Grype not found at {self.grype_path}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Grype version check timed out")

    def scan_sbom(
        self,
        sbom: dict,
        model_id: str,
    ) -> dict:
        """
        Scan an SBOM for vulnerabilities.

        Args:
            sbom: SBOM dictionary
            model_id: Model identifier for naming output

        Returns:
            Vulnerability scan results
        """
        logger.info(f"Scanning SBOM for vulnerabilities: {model_id}")

        # Write SBOM to temp file
        safe_name = model_id.replace("/", "_")
        sbom_file = self.output_dir / f"{safe_name}_sbom.json"
        sbom_file.write_text(json.dumps(sbom, indent=2))

        try:
            result = subprocess.run(
                [
                    self.grype_path,
                    f"sbom:{sbom_file}",
                    "-o", "json",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )

            if result.returncode == 0 or result.stdout:
                vulns = json.loads(result.stdout)
                processed = self._process_vulnerabilities(vulns)

                # Save results
                vuln_file = self.output_dir / f"{safe_name}_vulns.json"
                vuln_file.write_text(json.dumps(processed, indent=2))

                logger.info(
                    f"Found {processed['summary']['total']} vulnerabilities "
                    f"({processed['summary']['critical']} critical, "
                    f"{processed['summary']['high']} high)"
                )
                return processed

            else:
                logger.error(f"Grype error: {result.stderr}")
                return self._empty_result()

        except subprocess.TimeoutExpired:
            logger.error("Grype scan timed out")
            return self._empty_result()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse grype output: {e}")
            return self._empty_result()

    def _process_vulnerabilities(self, grype_output: dict) -> dict:
        """
        Process raw grype output into structured format.

        Args:
            grype_output: Raw grype JSON output

        Returns:
            Processed vulnerability data
        """
        matches = grype_output.get("matches", [])

        # Count by severity
        severity_counts = defaultdict(int)
        vulns_by_severity = defaultdict(list)

        for match in matches:
            vuln = match.get("vulnerability", {})
            artifact = match.get("artifact", {})

            severity = vuln.get("severity", "Unknown").lower()
            severity_counts[severity] += 1

            # Build vulnerability record
            vuln_record = {
                "id": vuln.get("id", ""),
                "severity": severity,
                "description": vuln.get("description", ""),
                "package": artifact.get("name", ""),
                "installed_version": artifact.get("version", ""),
                "fixed_version": self._get_fix_version(match),
                "cvss": self._get_cvss(vuln),
                "urls": vuln.get("urls", []),
                "data_source": vuln.get("dataSource", ""),
            }

            vulns_by_severity[severity].append(vuln_record)

        # Sort vulnerabilities within each severity
        for severity in vulns_by_severity:
            vulns_by_severity[severity].sort(
                key=lambda x: x.get("cvss", {}).get("score", 0),
                reverse=True,
            )

        return {
            "summary": {
                "total": len(matches),
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
                "unknown": severity_counts.get("unknown", 0),
            },
            "by_severity": dict(vulns_by_severity),
            "all_vulnerabilities": [
                v for vulns in vulns_by_severity.values() for v in vulns
            ],
        }

    def _get_fix_version(self, match: dict) -> Optional[str]:
        """Extract fix version from match data."""
        related = match.get("relatedVulnerabilities", [])
        for rel in related:
            fix = rel.get("fix", {})
            if fix.get("versions"):
                return fix["versions"][0]

        vuln = match.get("vulnerability", {})
        fix = vuln.get("fix", {})
        if fix.get("versions"):
            return fix["versions"][0]

        return None

    def _get_cvss(self, vuln: dict) -> dict:
        """Extract CVSS data from vulnerability."""
        cvss = vuln.get("cvss", [])
        if cvss:
            best = cvss[0]
            return {
                "version": best.get("version", ""),
                "score": best.get("metrics", {}).get("baseScore", 0),
                "vector": best.get("vector", ""),
            }
        return {"version": "", "score": 0, "vector": ""}

    def _empty_result(self) -> dict:
        """Return empty result structure."""
        return {
            "summary": {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "unknown": 0,
            },
            "by_severity": {},
            "all_vulnerabilities": [],
        }

    def get_top_vulnerabilities(
        self,
        vuln_results: dict,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get top vulnerabilities by severity and CVSS score.

        Args:
            vuln_results: Processed vulnerability results
            limit: Maximum number to return

        Returns:
            List of top vulnerabilities
        """
        all_vulns = vuln_results.get("all_vulnerabilities", [])

        # Sort by severity then CVSS score
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}

        sorted_vulns = sorted(
            all_vulns,
            key=lambda x: (
                severity_order.get(x.get("severity", "unknown"), 5),
                -x.get("cvss", {}).get("score", 0),
            ),
        )

        return sorted_vulns[:limit]
