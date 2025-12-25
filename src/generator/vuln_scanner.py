"""
Vulnerability Scanner

Scans SBOMs for vulnerabilities using Grype and OSV-Scanner.
OSV-Scanner provides better coverage for Python packages.
Also includes security recommendations based on known CVEs.
"""
import json
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional
from collections import defaultdict

from src.generator.sbom_generator import get_security_recommendations, KNOWN_MINIMUM_VERSIONS

logger = logging.getLogger(__name__)


class VulnerabilityScanner:
    """Scans SBOMs for vulnerabilities using Grype and OSV-Scanner."""

    def __init__(
        self,
        grype_path: str = "grype",
        osv_scanner_path: str = "osv-scanner",
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize vulnerability scanner.

        Args:
            grype_path: Path to grype executable
            osv_scanner_path: Path to osv-scanner executable
            output_dir: Directory for scan results
        """
        self.grype_path = grype_path
        self.osv_scanner_path = osv_scanner_path
        self.output_dir = Path(output_dir) if output_dir else Path(".")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Verify tools are available
        self._verify_grype()
        self._verify_osv_scanner()

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

    def _verify_osv_scanner(self):
        """Verify osv-scanner is installed and accessible."""
        try:
            result = subprocess.run(
                [self.osv_scanner_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.debug(f"OSV-Scanner version: {result.stdout.strip()}")
            else:
                logger.warning(f"OSV-Scanner warning: {result.stderr}")
        except FileNotFoundError:
            logger.warning(f"OSV-Scanner not found at {self.osv_scanner_path}, using Grype only")
            self.osv_scanner_path = None
        except subprocess.TimeoutExpired:
            logger.warning("OSV-Scanner version check timed out")
            self.osv_scanner_path = None

    def scan_sbom(
        self,
        sbom: dict,
        model_id: str,
        requirements: list[str] = None,
    ) -> dict:
        """
        Scan an SBOM for vulnerabilities using both Grype and OSV-Scanner.

        Args:
            sbom: SBOM dictionary
            model_id: Model identifier for naming output
            requirements: List of versioned requirements (e.g., ["torch==2.7.1"])

        Returns:
            Vulnerability scan results
        """
        logger.info(f"Scanning for vulnerabilities: {model_id}")

        # Write SBOM to temp file
        safe_name = model_id.replace("/", "_")
        sbom_file = self.output_dir / f"{safe_name}_sbom.json"
        sbom_file.write_text(json.dumps(sbom, indent=2))

        # Run Grype scan on SBOM
        grype_results = self._scan_with_grype(sbom_file)

        # Run OSV-Scanner on requirements if available
        osv_results = self._empty_result()
        if self.osv_scanner_path and requirements:
            osv_results = self._scan_with_osv(requirements, safe_name)

        # Merge results (OSV-Scanner typically finds more Python vulns)
        merged = self._merge_results(grype_results, osv_results)

        # Add security recommendations based on known minimum versions
        # Always include known minimum versions for common packages as guidance
        merged["minimum_safe_versions"] = {
            pkg: {
                "min_version": min_ver,
                "cve_id": cve_id,
                "severity": severity,
                "description": desc,
            }
            for pkg, (min_ver, cve_id, severity, desc) in KNOWN_MINIMUM_VERSIONS.items()
        }

        # Check if any current requirements are below safe versions
        recommendations = []
        if requirements:
            recommendations = get_security_recommendations(requirements)
            merged["security_recommendations"] = recommendations

            # Log recommendations
            if recommendations:
                logger.info(f"  Security recommendations: {len(recommendations)} packages need attention")
                for rec in recommendations:
                    logger.debug(f"    {rec['package']}: upgrade to >= {rec['minimum_safe_version']} ({rec['cve_id']})")

        # Save results
        vuln_file = self.output_dir / f"{safe_name}_vulns.json"
        vuln_file.write_text(json.dumps(merged, indent=2))

        logger.info(
            f"Found {merged['summary']['total']} vulnerabilities "
            f"({merged['summary']['critical']} critical, "
            f"{merged['summary']['high']} high)"
        )
        return merged

    def _scan_with_grype(self, sbom_file: Path) -> dict:
        """Run Grype scan on SBOM file."""
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
                return self._process_vulnerabilities(vulns)
            else:
                logger.debug(f"Grype returned no results: {result.stderr}")
                return self._empty_result()

        except subprocess.TimeoutExpired:
            logger.error("Grype scan timed out")
            return self._empty_result()
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse grype output: {e}")
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

    def _scan_with_osv(self, requirements: list[str], safe_name: str) -> dict:
        """
        Run OSV-Scanner on a requirements list.

        Args:
            requirements: List of versioned requirements (e.g., ["torch==2.7.1"])
            safe_name: Safe model name for temp files

        Returns:
            Processed vulnerability results
        """
        try:
            # Create temporary requirements.txt
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.txt',
                prefix=f'requirements_{safe_name}_',
                delete=False
            ) as f:
                f.write('\n'.join(requirements))
                req_file = Path(f.name)

            try:
                result = subprocess.run(
                    [
                        self.osv_scanner_path,
                        "--format", "json",
                        "-L", str(req_file),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )

                # OSV-Scanner returns exit code 1 when vulnerabilities are found
                if result.stdout:
                    osv_output = json.loads(result.stdout)
                    return self._process_osv_output(osv_output)
                else:
                    logger.debug(f"OSV-Scanner returned no output: {result.stderr}")
                    return self._empty_result()

            finally:
                # Clean up temp file
                req_file.unlink(missing_ok=True)

        except subprocess.TimeoutExpired:
            logger.error("OSV-Scanner timed out")
            return self._empty_result()
        except json.JSONDecodeError as e:
            logger.debug(f"Failed to parse OSV-Scanner output: {e}")
            return self._empty_result()
        except Exception as e:
            logger.debug(f"OSV-Scanner error: {e}")
            return self._empty_result()

    def _process_osv_output(self, osv_output: dict) -> dict:
        """
        Process raw OSV-Scanner output into structured format.

        Args:
            osv_output: Raw OSV-Scanner JSON output

        Returns:
            Processed vulnerability data
        """
        severity_counts = defaultdict(int)
        vulns_by_severity = defaultdict(list)

        results = osv_output.get("results", [])
        for result in results:
            packages = result.get("packages", [])
            for pkg in packages:
                pkg_info = pkg.get("package", {})
                pkg_name = pkg_info.get("name", "")
                pkg_version = pkg_info.get("version", "")

                for vuln in pkg.get("vulnerabilities", []):
                    # Determine severity from CVSS or severity field
                    severity = self._get_osv_severity(vuln)
                    severity_counts[severity] += 1

                    # Extract CVSS score
                    cvss_score = 0.0
                    for sev in vuln.get("severity", []):
                        if sev.get("type") == "CVSS_V3":
                            try:
                                cvss_score = float(sev.get("score", "0").split("/")[0])
                            except (ValueError, IndexError):
                                pass

                    vuln_record = {
                        "id": vuln.get("id", ""),
                        "severity": severity,
                        "description": vuln.get("summary", vuln.get("details", "")[:200]),
                        "package": pkg_name,
                        "installed_version": pkg_version,
                        "fixed_version": self._get_osv_fix_version(vuln, pkg_version),
                        "cvss": {"version": "3.0", "score": cvss_score, "vector": ""},
                        "urls": [ref.get("url", "") for ref in vuln.get("references", [])[:3]],
                        "data_source": "OSV",
                    }

                    vulns_by_severity[severity].append(vuln_record)

        # Sort vulnerabilities within each severity by CVSS score
        for severity in vulns_by_severity:
            vulns_by_severity[severity].sort(
                key=lambda x: x.get("cvss", {}).get("score", 0),
                reverse=True,
            )

        total = sum(severity_counts.values())
        return {
            "summary": {
                "total": total,
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

    def _get_osv_severity(self, vuln: dict) -> str:
        """Extract severity from OSV vulnerability data."""
        # Check database_specific for severity
        db_specific = vuln.get("database_specific", {})
        if "severity" in db_specific:
            return db_specific["severity"].lower()

        # Check CVSS score to determine severity
        for sev in vuln.get("severity", []):
            if sev.get("type") == "CVSS_V3":
                try:
                    score = float(sev.get("score", "0").split("/")[0])
                    if score >= 9.0:
                        return "critical"
                    elif score >= 7.0:
                        return "high"
                    elif score >= 4.0:
                        return "medium"
                    else:
                        return "low"
                except (ValueError, IndexError):
                    pass

        return "unknown"

    def _get_osv_fix_version(self, vuln: dict, current_version: str) -> Optional[str]:
        """Extract fix version from OSV vulnerability data."""
        for affected in vuln.get("affected", []):
            for r in affected.get("ranges", []):
                for event in r.get("events", []):
                    if "fixed" in event:
                        return event["fixed"]
        return None

    def _merge_results(self, grype_results: dict, osv_results: dict) -> dict:
        """
        Merge vulnerability results from multiple scanners.
        Deduplicates by vulnerability ID.

        Args:
            grype_results: Results from Grype
            osv_results: Results from OSV-Scanner

        Returns:
            Merged vulnerability results
        """
        # Use a dict to deduplicate by vuln ID
        seen_ids = set()
        merged_vulns = []

        # Add all vulnerabilities, preferring OSV data (more detailed for Python)
        for vuln in osv_results.get("all_vulnerabilities", []):
            vuln_id = vuln.get("id", "")
            if vuln_id and vuln_id not in seen_ids:
                seen_ids.add(vuln_id)
                merged_vulns.append(vuln)

        for vuln in grype_results.get("all_vulnerabilities", []):
            vuln_id = vuln.get("id", "")
            if vuln_id and vuln_id not in seen_ids:
                seen_ids.add(vuln_id)
                merged_vulns.append(vuln)

        # Recount by severity
        severity_counts = defaultdict(int)
        vulns_by_severity = defaultdict(list)

        for vuln in merged_vulns:
            severity = vuln.get("severity", "unknown")
            severity_counts[severity] += 1
            vulns_by_severity[severity].append(vuln)

        return {
            "summary": {
                "total": len(merged_vulns),
                "critical": severity_counts.get("critical", 0),
                "high": severity_counts.get("high", 0),
                "medium": severity_counts.get("medium", 0),
                "low": severity_counts.get("low", 0),
                "unknown": severity_counts.get("unknown", 0),
            },
            "by_severity": dict(vulns_by_severity),
            "all_vulnerabilities": merged_vulns,
        }
