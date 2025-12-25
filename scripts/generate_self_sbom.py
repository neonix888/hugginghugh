#!/usr/bin/env python3
"""
Generate SBOM report for HuggingHugh itself.

This script scans our own project dependencies and generates an HTML report
at output/sbom.html - eating our own dog food!

Usage:
    python scripts/generate_self_sbom.py
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"


def run_command(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def sanitize_sbom(sbom: dict) -> dict:
    """Remove local file paths from SBOM to avoid exposing server structure."""
    project_path = str(PROJECT_ROOT)

    # Filter out components that are local project files
    if "components" in sbom:
        filtered_components = []
        for comp in sbom["components"]:
            # Skip components that reference local project path
            name = comp.get("name", "")
            purl = comp.get("purl", "")

            # Skip if it's a local file path reference
            if project_path in name or project_path in purl:
                continue
            if name.startswith("/home/") or name.startswith("/var/"):
                continue

            # Clean up any path references in the component
            if "properties" in comp:
                comp["properties"] = [
                    p for p in comp["properties"]
                    if project_path not in str(p.get("value", ""))
                    and "/home/" not in str(p.get("value", ""))
                ]

            filtered_components.append(comp)

        sbom["components"] = filtered_components

    return sbom


def generate_sbom() -> dict:
    """Generate SBOM using Syft."""
    print("Generating SBOM with Syft...")
    sbom_file = DATA_DIR / "self_sbom.json"

    code, stdout, stderr = run_command([
        "syft", str(PROJECT_ROOT), "-o", "cyclonedx-json"
    ])

    if code != 0:
        print(f"Error generating SBOM: {stderr}")
        sys.exit(1)

    sbom = json.loads(stdout)

    # Sanitize to remove local paths
    sbom = sanitize_sbom(sbom)

    sbom_file.write_text(json.dumps(sbom, indent=2))
    print(f"  SBOM saved to {sbom_file}")
    print(f"  Components: {len(sbom.get('components', []))}")

    return sbom


def scan_vulnerabilities(sbom_file: Path) -> dict:
    """Scan SBOM for vulnerabilities using Grype."""
    print("Scanning for vulnerabilities with Grype...")
    vulns_file = DATA_DIR / "self_vulns.json"

    code, stdout, stderr = run_command([
        "grype", f"sbom:{sbom_file}", "-o", "json"
    ])

    if code != 0 and "no vulnerabilities found" not in stderr.lower():
        print(f"Warning: Grype returned non-zero: {stderr}")

    vulns = json.loads(stdout) if stdout.strip() else {"matches": []}
    vulns_file.write_text(json.dumps(vulns, indent=2))

    matches = vulns.get("matches", [])
    print(f"  Vulnerabilities found: {len(matches)}")

    return vulns


def categorize_vulns(vulns: dict) -> dict:
    """Categorize vulnerabilities by severity."""
    matches = vulns.get("matches", [])
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}

    for match in matches:
        severity = match.get("vulnerability", {}).get("severity", "Unknown").lower()
        if severity in summary:
            summary[severity] += 1
        else:
            summary["unknown"] += 1

    summary["total"] = len(matches)
    return summary


def generate_html_report(sbom: dict, vulns: dict) -> str:
    """Generate HTML SBOM report."""
    components = sbom.get("components", [])
    matches = vulns.get("matches", [])
    summary = categorize_vulns(vulns)

    # Group components by type
    by_type = {}
    for comp in components:
        comp_type = comp.get("type", "unknown")
        if comp_type not in by_type:
            by_type[comp_type] = []
        by_type[comp_type].append(comp)

    # Calculate score (simple: 100 - penalties)
    score = 100
    score -= summary["critical"] * 25
    score -= summary["high"] * 10
    score -= summary["medium"] * 3
    score -= summary["low"] * 1
    score = max(0, min(100, score))

    if score >= 90:
        grade, grade_color = "A", "#22c55e"
    elif score >= 80:
        grade, grade_color = "B", "#84cc16"
    elif score >= 70:
        grade, grade_color = "C", "#eab308"
    elif score >= 60:
        grade, grade_color = "D", "#f97316"
    else:
        grade, grade_color = "F", "#ef4444"

    # Build vulnerability rows
    vuln_rows = ""
    for match in sorted(matches, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(
            x.get("vulnerability", {}).get("severity", "").lower(), 4)):
        vuln = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        severity = vuln.get("severity", "Unknown")
        sev_class = severity.lower()

        vuln_rows += f"""
        <tr class="vuln-{sev_class}">
            <td><a href="https://nvd.nist.gov/vuln/detail/{vuln.get('id', '')}" target="_blank">{vuln.get('id', 'N/A')}</a></td>
            <td><span class="severity-badge {sev_class}">{severity}</span></td>
            <td>{artifact.get('name', 'N/A')}</td>
            <td>{artifact.get('version', 'N/A')}</td>
            <td>{vuln.get('fix', {}).get('versions', ['No fix'])[0] if vuln.get('fix', {}).get('versions') else 'No fix available'}</td>
        </tr>
        """

    if not vuln_rows:
        vuln_rows = '<tr><td colspan="5" style="text-align: center; padding: 2rem; color: #22c55e;">No vulnerabilities found!</td></tr>'

    # Build component rows
    comp_rows = ""
    for comp_type, comps in sorted(by_type.items()):
        for comp in sorted(comps, key=lambda x: x.get("name", "")):
            licenses = comp.get("licenses", [])
            license_str = ", ".join([
                lic.get("license", {}).get("id", "") or lic.get("license", {}).get("name", "Unknown")
                for lic in licenses
            ]) or "Unknown"

            comp_rows += f"""
            <tr>
                <td>{comp.get('name', 'N/A')}</td>
                <td>{comp.get('version', 'N/A')}</td>
                <td><span class="type-badge">{comp_type}</span></td>
                <td>{license_str}</td>
            </tr>
            """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HuggingHugh SBOM Report</title>
    <link rel="stylesheet" href="/static/css/style.css">
    <style>
        .sbom-header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: var(--space-xl);
            border-radius: var(--radius-lg);
            margin-bottom: var(--space-xl);
        }}
        .sbom-header h1 {{
            margin: 0 0 var(--space-sm) 0;
            font-size: 2rem;
        }}
        .sbom-header p {{
            margin: 0;
            opacity: 0.9;
        }}
        .score-circle {{
            width: 120px;
            height: 120px;
            border-radius: 50%;
            background: {grade_color};
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 700;
            box-shadow: var(--shadow-lg);
        }}
        .score-circle .score {{
            font-size: 2.5rem;
            line-height: 1;
        }}
        .score-circle .grade {{
            font-size: 1.5rem;
            opacity: 0.9;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: var(--space-md);
            margin-bottom: var(--space-xl);
        }}
        .summary-card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: var(--space-lg);
            text-align: center;
        }}
        .summary-card .number {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text);
        }}
        .summary-card .label {{
            color: var(--text-muted);
            font-size: 0.875rem;
        }}
        .summary-card.critical .number {{ color: #ef4444; }}
        .summary-card.high .number {{ color: #f97316; }}
        .summary-card.medium .number {{ color: #eab308; }}
        .summary-card.low .number {{ color: #22c55e; }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: var(--space-xl);
        }}
        th, td {{
            padding: var(--space-sm) var(--space-md);
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: var(--background);
            font-weight: 600;
            position: sticky;
            top: 0;
        }}
        tr:hover {{
            background: var(--background);
        }}
        .severity-badge {{
            padding: 0.25rem 0.75rem;
            border-radius: var(--radius-full);
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .severity-badge.critical {{ background: #fef2f2; color: #dc2626; }}
        .severity-badge.high {{ background: #fff7ed; color: #ea580c; }}
        .severity-badge.medium {{ background: #fefce8; color: #ca8a04; }}
        .severity-badge.low {{ background: #f0fdf4; color: #16a34a; }}
        .severity-badge.unknown {{ background: #f3f4f6; color: #6b7280; }}

        .type-badge {{
            padding: 0.25rem 0.5rem;
            border-radius: var(--radius-sm);
            font-size: 0.75rem;
            background: var(--background);
            color: var(--text-muted);
        }}

        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: var(--space-lg);
            margin-bottom: var(--space-xl);
        }}
        .section h2 {{
            margin: 0 0 var(--space-md) 0;
            padding-bottom: var(--space-sm);
            border-bottom: 2px solid var(--border);
        }}

        .meta-info {{
            display: flex;
            gap: var(--space-xl);
            flex-wrap: wrap;
            margin-top: var(--space-md);
            padding-top: var(--space-md);
            border-top: 1px solid rgba(255,255,255,0.2);
            font-size: 0.875rem;
        }}
        .meta-info span {{
            display: flex;
            align-items: center;
            gap: var(--space-xs);
        }}

        .header-flex {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: var(--space-lg);
        }}

        .table-container {{
            max-height: 500px;
            overflow-y: auto;
        }}

        a {{
            color: var(--primary);
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="container">
            <div class="header-content">
                <a href="/" class="logo">
                    <span class="logo-icon">🤗</span>
                    <span class="logo-text">HuggingHugh</span>
                </a>
                <nav class="main-nav">
                    <a href="/">Dashboard</a>
                    <a href="/about.html">About</a>
                    <a href="/sbom.html" class="active">Our SBOM</a>
                </nav>
            </div>
        </div>
    </header>

    <main class="main-content">
        <div class="container">
            <div class="sbom-header">
                <div class="header-flex">
                    <div>
                        <h1>HuggingHugh SBOM Report</h1>
                        <p>Software Bill of Materials for this project - eating our own dog food!</p>
                        <div class="meta-info">
                            <span>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
                            <span>Components: {len(components)}</span>
                            <span>Vulnerabilities: {summary['total']}</span>
                        </div>
                    </div>
                    <div class="score-circle">
                        <span class="score">{score}</span>
                        <span class="grade">{grade}</span>
                    </div>
                </div>
            </div>

            <div class="summary-grid">
                <div class="summary-card critical">
                    <div class="number">{summary['critical']}</div>
                    <div class="label">Critical</div>
                </div>
                <div class="summary-card high">
                    <div class="number">{summary['high']}</div>
                    <div class="label">High</div>
                </div>
                <div class="summary-card medium">
                    <div class="number">{summary['medium']}</div>
                    <div class="label">Medium</div>
                </div>
                <div class="summary-card low">
                    <div class="number">{summary['low']}</div>
                    <div class="label">Low</div>
                </div>
                <div class="summary-card">
                    <div class="number">{len(components)}</div>
                    <div class="label">Components</div>
                </div>
            </div>

            <div class="section">
                <h2>Vulnerabilities</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>CVE ID</th>
                                <th>Severity</th>
                                <th>Package</th>
                                <th>Version</th>
                                <th>Fix</th>
                            </tr>
                        </thead>
                        <tbody>
                            {vuln_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="section">
                <h2>Components ({len(components)})</h2>
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Version</th>
                                <th>Type</th>
                                <th>License</th>
                            </tr>
                        </thead>
                        <tbody>
                            {comp_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </main>

    <footer class="site-footer">
        <div class="container">
            <p>HuggingHugh - Nutrition Labels for AI Models</p>
            <p>SBOM generated with <a href="https://github.com/anchore/syft" target="_blank">Syft</a>,
               scanned with <a href="https://github.com/anchore/grype" target="_blank">Grype</a></p>
        </div>
    </footer>
</body>
</html>
"""
    return html


def main():
    print("=" * 60)
    print("HuggingHugh Self-SBOM Generator")
    print("=" * 60)

    # Ensure directories exist
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Generate SBOM
    sbom = generate_sbom()

    # Scan for vulnerabilities
    vulns = scan_vulnerabilities(DATA_DIR / "self_sbom.json")

    # Generate HTML report
    print("Generating HTML report...")
    html = generate_html_report(sbom, vulns)

    output_file = OUTPUT_DIR / "sbom.html"
    output_file.write_text(html)
    print(f"  Report saved to {output_file}")

    # Summary
    summary = categorize_vulns(vulns)
    print("\n" + "=" * 60)
    print("SBOM SUMMARY")
    print("=" * 60)
    print(f"Components: {len(sbom.get('components', []))}")
    print(f"Vulnerabilities: {summary['total']}")
    print(f"  Critical: {summary['critical']}")
    print(f"  High: {summary['high']}")
    print(f"  Medium: {summary['medium']}")
    print(f"  Low: {summary['low']}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
