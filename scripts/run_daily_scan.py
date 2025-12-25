#!/usr/bin/env python3
"""
HuggingHugh Daily Scanner

Main orchestrator script that:
1. Fetches top 1000 models from HuggingFace
2. Downloads metadata for each model
3. Generates SBOMs
4. Scans for vulnerabilities
5. Analyzes licenses
6. Calculates trust scores
7. Generates HTML reports
8. Deploys to web directory (only with --deploy flag)

Usage:
    python scripts/run_daily_scan.py [--limit N] [--verbose]     # Scan only, no deploy
    python scripts/run_daily_scan.py --deploy                    # Scan and deploy to production
    python scripts/run_daily_scan.py --deploy --force            # Force re-scan and deploy

SAFEGUARDS:
    - Deployment requires explicit --deploy flag
    - Minimum 500 models required for deployment (use --min-models to override)
    - Pre-deploy verification checks model count
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scanner import HuggingFaceClient, get_top_models, ModelFetcher
from src.generator import SBOMGenerator, VulnerabilityScanner, LicenseAnalyzer, TrustScorer
from src.reporter import HTMLReportGenerator, DashboardGenerator


class Timer:
    """Simple timer for tracking execution times."""

    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger
        self.start_time = None
        self.elapsed = timedelta(0)

    def start(self):
        self.start_time = time.time()
        return self

    def stop(self):
        if self.start_time:
            self.elapsed = timedelta(seconds=time.time() - self.start_time)
            self.start_time = None
        return self.elapsed

    def log(self, message: str = None):
        elapsed = self.stop()
        msg = f"⏱️  {self.name}: {self._format_duration(elapsed)}"
        if message:
            msg = f"{msg} - {message}"
        if self.logger:
            self.logger.info(msg)
        else:
            print(msg)
        return elapsed

    @staticmethod
    def _format_duration(td: timedelta) -> str:
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        ms = int((td.total_seconds() - total_seconds) * 1000)

        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        elif seconds > 0:
            return f"{seconds}.{ms:03d}s"
        else:
            return f"{ms}ms"


class TimingStats:
    """Collect and report timing statistics."""

    def __init__(self):
        self.timings = {}
        self.model_times = []

    def record(self, name: str, elapsed: timedelta):
        self.timings[name] = elapsed

    def record_model(self, model_id: str, elapsed: timedelta):
        self.model_times.append((model_id, elapsed))

    def report(self, logger):
        logger.info("\n" + "=" * 60)
        logger.info("⏱️  TIMING REPORT")
        logger.info("=" * 60)

        # Phase timings
        for name, elapsed in self.timings.items():
            logger.info(f"  {name}: {Timer._format_duration(elapsed)}")

        # Model statistics
        if self.model_times:
            times = [t[1].total_seconds() for t in self.model_times]
            avg_time = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)

            logger.info(f"\n  Model Processing Stats ({len(self.model_times)} models):")
            logger.info(f"    Average: {avg_time:.2f}s per model")
            logger.info(f"    Fastest: {min_time:.2f}s")
            logger.info(f"    Slowest: {max_time:.2f}s")

            # Slowest models
            sorted_times = sorted(self.model_times, key=lambda x: x[1], reverse=True)[:3]
            logger.info(f"    Slowest models:")
            for model_id, elapsed in sorted_times:
                logger.info(f"      - {model_id}: {Timer._format_duration(elapsed)}")

        # Total time
        total = sum(self.timings.values(), timedelta(0))
        logger.info(f"\n  TOTAL TIME: {Timer._format_duration(total)}")
        logger.info("=" * 60)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(log_format))

    # File handler
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(
        log_dir / f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return logging.getLogger(__name__)


def verify_deployment_ready(output_dir: Path, min_models: int, logger) -> bool:
    """
    Verify that the output is ready for deployment.

    SAFEGUARD: Prevents deploying incomplete scans to production.

    Returns True if safe to deploy, False otherwise.
    """
    reports_dir = output_dir / "reports"

    if not reports_dir.exists():
        logger.error("DEPLOY BLOCKED: No reports directory found")
        return False

    report_count = len(list(reports_dir.glob("*")))

    if report_count < min_models:
        logger.error(f"DEPLOY BLOCKED: Only {report_count} reports found, minimum {min_models} required")
        logger.error(f"Use --min-models {report_count} to override (NOT RECOMMENDED)")
        return False

    # Check dashboard exists
    if not (output_dir / "index.html").exists():
        logger.error("DEPLOY BLOCKED: Dashboard index.html not found")
        return False

    # Check static assets exist
    if not (output_dir / "static" / "css" / "style.css").exists():
        logger.error("DEPLOY BLOCKED: Static CSS not found")
        return False

    logger.info(f"DEPLOY CHECK PASSED: {report_count} reports ready")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="HuggingHugh Daily Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Scan 1000 models, no deploy
  %(prog)s --limit 10           # Scan 10 models for testing, no deploy
  %(prog)s --deploy             # Scan 1000 models and deploy to production
  %(prog)s --deploy --force     # Force re-scan all and deploy

SAFEGUARDS:
  - Deployment requires explicit --deploy flag
  - Minimum 500 models required for deployment
  - Use --min-models to override (not recommended)
        """
    )
    parser.add_argument("--deploy", action="store_true",
                        help="Deploy to production after scan (requires min models)")
    parser.add_argument("--limit", type=int, default=1000,
                        help="Number of models to scan (default: 1000)")
    parser.add_argument("--min-models", type=int, default=500,
                        help="Minimum models required for deployment (default: 500)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose output")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Force re-scan all models")
    # Keep --dry-run for backwards compatibility but it's now the default
    parser.add_argument("--dry-run", action="store_true",
                        help="(Deprecated) No deployment is now the default behavior")
    args = parser.parse_args()

    # Warn about deprecated --dry-run
    if args.dry_run:
        print("WARNING: --dry-run is deprecated. No-deploy is now the default.")
        print("         Use --deploy to explicitly deploy to production.")

    logger = setup_logging(args.verbose)
    logger.info("=" * 60)
    logger.info("HuggingHugh Daily Scanner Starting")
    logger.info("=" * 60)

    # Initialize timing
    stats = TimingStats()
    total_timer = Timer("Total Execution", logger).start()
    phase_timer = Timer("Initialization", logger).start()

    start_time = datetime.now()

    # Configuration
    hf_token = os.environ.get("HF_TOKEN")
    output_dir = PROJECT_ROOT / "output"
    data_dir = PROJECT_ROOT / "data"
    templates_dir = PROJECT_ROOT / "templates"
    static_dir = PROJECT_ROOT / "static"
    web_root = Path("/var/www/hugginghugh.etcbin.io")

    # Create directories
    output_dir.mkdir(exist_ok=True)
    (data_dir / "models").mkdir(parents=True, exist_ok=True)
    (data_dir / "sboms").mkdir(parents=True, exist_ok=True)

    # Initialize components
    logger.info("Initializing components...")
    fetcher = ModelFetcher(cache_dir=data_dir / "models", token=hf_token)
    sbom_gen = SBOMGenerator(output_dir=data_dir / "sboms")
    vuln_scanner = VulnerabilityScanner(output_dir=data_dir / "sboms")
    license_analyzer = LicenseAnalyzer()
    trust_scorer = TrustScorer()
    html_gen = HTMLReportGenerator(
        templates_dir=templates_dir,
        output_dir=output_dir,
        static_dir=static_dir,
        base_url="",
    )
    dashboard_gen = DashboardGenerator(
        templates_dir=templates_dir,
        output_dir=output_dir,
        base_url="",
    )

    stats.record("1. Initialization", phase_timer.stop())

    # Step 1: Fetch top models
    phase_timer = Timer("Fetch Models", logger).start()
    logger.info(f"Fetching top {args.limit} models from HuggingFace...")
    models = get_top_models(limit=args.limit, token=hf_token)
    logger.info(f"Found {len(models)} models")
    stats.record("2. Fetch Model List", phase_timer.stop())

    # Step 2: Process each model
    phase_timer = Timer("Process Models", logger).start()
    all_results = []
    successful = 0
    failed = 0

    for i, model in enumerate(models, 1):
        model_timer = Timer(f"Model {i}", logger).start()
        logger.info(f"\n[{i}/{len(models)}] Processing: {model.model_id}")
        logger.info(f"  Downloads: {model.downloads:,}, Likes: {model.likes:,}")

        try:
            # Fetch metadata
            logger.info("  Fetching metadata...")
            metadata = fetcher.fetch_model_metadata(model, force=args.force)

            # Generate SBOM
            logger.info("  Generating SBOM...")
            sbom = sbom_gen.generate_sbom(metadata)

            # Get versioned requirements for OSV-Scanner
            requirements = sbom_gen._infer_requirements(metadata)

            # Scan vulnerabilities (Grype + OSV-Scanner)
            logger.info("  Scanning vulnerabilities...")
            vulns = vuln_scanner.scan_sbom(sbom, model.model_id, requirements=requirements)

            # Analyze license
            logger.info("  Analyzing license...")
            model_license = license_analyzer.analyze_model_license(metadata)
            sbom_licenses = license_analyzer.analyze_sbom_licenses(sbom)
            license_summary = license_analyzer.get_license_summary(model_license, sbom_licenses)

            # Calculate trust score
            logger.info("  Calculating trust score...")
            trust_score = trust_scorer.calculate_score(metadata, vulns, license_summary)

            logger.info(f"  Trust Score: {trust_score.total_score}/100 ({trust_score.grade})")
            logger.info(f"  Vulnerabilities: {vulns['summary']['total']} total, {vulns['summary']['critical']} critical")

            # Generate HTML report
            logger.info("  Generating HTML report...")
            html_gen.generate_model_report(
                model_metadata=metadata,
                sbom=sbom,
                vulnerabilities=vulns,
                trust_score=trust_score,
                license_analysis=license_summary,
            )

            # Collect results for dashboard
            all_results.append({
                "model_id": model.model_id,
                "model_name": model.model_name,
                "author": model.author,
                "downloads": model.downloads,
                "likes": model.likes,
                "trust_score": trust_score.total_score,
                "trust_grade": trust_score.grade,
                "vulnerabilities": vulns,
                "license": model.license,
                "has_safetensors": model.has_safetensors,
                "pipeline_tag": model.pipeline_tag,
                "library_name": model.library_name,
            })

            successful += 1
            stats.record_model(model.model_id, model_timer.stop())

        except Exception as e:
            logger.error(f"  ERROR: Failed to process {model.model_id}: {e}")
            failed += 1
            stats.record_model(model.model_id, model_timer.stop())
            continue

    stats.record("3. Process All Models", phase_timer.stop())

    # Step 3: Generate dashboard
    phase_timer = Timer("Generate Dashboard", logger).start()
    logger.info("\nGenerating dashboard...")
    html_gen.copy_static_assets()
    dashboard_gen.generate_dashboard(all_results)
    dashboard_gen.generate_api_json(all_results)
    dashboard_gen.generate_about_page()

    # Step 3.5: Generate self-SBOM (eat our own dog food!)
    logger.info("\nGenerating self-SBOM report...")
    try:
        from scripts.generate_self_sbom import generate_sbom, scan_vulnerabilities, generate_html_report, categorize_vulns
        sbom_data = generate_sbom()
        vulns_data = scan_vulnerabilities(PROJECT_ROOT / "data" / "self_sbom.json")
        html_content = generate_html_report(sbom_data, vulns_data)
        (output_dir / "sbom.html").write_text(html_content)
        summary = categorize_vulns(vulns_data)
        logger.info(f"  Self-SBOM: {len(sbom_data.get('components', []))} components, {summary['total']} vulnerabilities")
    except Exception as e:
        logger.warning(f"  Failed to generate self-SBOM: {e}")

    stats.record("4. Generate Dashboard", phase_timer.stop())

    # Step 3.6: Record to leaderboard database and compute rankings
    phase_timer = Timer("Update Leaderboard", logger).start()
    logger.info("\nUpdating leaderboard database...")
    leaderboard_data = None
    try:
        from src.database import LeaderboardDB
        from datetime import date as dt_date

        scan_date = dt_date.today()
        with LeaderboardDB() as db:
            # Record all scan results
            recorded = db.record_scan_results(scan_date, all_results)
            logger.info(f"  Recorded {recorded} models to score_history")

            # Compute rankings (only eligible models with 1M+ downloads)
            rankings = db.compute_rankings(scan_date)
            eligible_count = db.get_eligible_count(scan_date)
            logger.info(f"  Computed rankings for {eligible_count} eligible models (1M+ downloads)")

            # Get top 3 for display
            leaderboard_data = db.get_top_n(3)
            if leaderboard_data:
                logger.info("  Top 3 Leaderboard:")
                for r in leaderboard_data:
                    logger.info(f"    #{r['rank']} {r['model_id']} - Score: {r['trust_score']}")
    except Exception as e:
        logger.warning(f"  Failed to update leaderboard: {e}")

    # Step 3.7: Regenerate dashboard with leaderboard data and generate leaderboard page
    if leaderboard_data:
        logger.info("\nRegenerating dashboard with leaderboard...")
        dashboard_gen.generate_dashboard(all_results, leaderboard=leaderboard_data)

        # Generate full leaderboard page with all rankings
        try:
            with LeaderboardDB() as db:
                full_rankings = db.get_full_leaderboard()
                dashboard_gen.generate_leaderboard_page(full_rankings)
                logger.info(f"  Leaderboard page generated with {len(full_rankings)} eligible models")
        except Exception as e:
            logger.warning(f"  Failed to generate leaderboard page: {e}")

    stats.record("5. Update Leaderboard", phase_timer.stop())

    # Step 4: Deploy to production (only with --deploy flag)
    if args.deploy:
        phase_timer = Timer("Deploy to Production", logger).start()
        logger.info("\n" + "=" * 60)
        logger.info("DEPLOYMENT REQUESTED")
        logger.info("=" * 60)

        # SAFEGUARD 1: Check successful scan count FIRST (most important!)
        if successful < args.min_models:
            logger.error(f"DEPLOY BLOCKED: Only {successful} models scanned successfully")
            logger.error(f"Minimum required: {args.min_models}")
            logger.error(f"Use --min-models {successful} to override (NOT RECOMMENDED)")
            return 1

        # SAFEGUARD 2: Verify output directory has required files
        if not verify_deployment_ready(output_dir, args.min_models, logger):
            logger.error("DEPLOYMENT ABORTED: Pre-deployment checks failed")
            logger.error("Fix the issues above or use --min-models to override")
            return 1

        if not web_root.exists():
            logger.error(f"DEPLOYMENT ABORTED: Web root {web_root} does not exist")
            return 1

        logger.info(f"Deploying to {web_root}...")

        # Use sudo for all deployment operations (web root owned by www-data)
        try:
            logger.info("Removing old files...")
            # Use bash -c to properly expand the glob pattern
            subprocess.run(
                ["sudo", "bash", "-c", f"rm -rf {web_root}/*"],
                check=True
            )

            logger.info("Copying new files...")
            # Use sudo cp -r to copy files
            subprocess.run(
                ["sudo", "cp", "-r"] + [str(p) for p in output_dir.iterdir()] + [str(web_root) + "/"],
                check=True
            )

            logger.info("Setting permissions...")
            subprocess.run(
                ["sudo", "chown", "-R", "www-data:www-data", str(web_root)],
                check=True
            )
            subprocess.run(
                ["sudo", "chmod", "-R", "755", str(web_root)],
                check=True
            )

            logger.info("DEPLOYMENT COMPLETE!")
            stats.record("6. Deploy to Production", phase_timer.stop())

        except subprocess.CalledProcessError as e:
            logger.error(f"DEPLOYMENT FAILED: Command failed - {e}")
            logger.error("Check sudo permissions and try again")
            stats.record("6. Deploy to Production (FAILED)", phase_timer.stop())
            return 1

    else:
        logger.info("\n" + "-" * 60)
        logger.info("NO DEPLOYMENT (use --deploy to deploy to production)")
        logger.info(f"Output available at: {output_dir}")
        logger.info("-" * 60)

    # Stop total timer
    total_elapsed = total_timer.stop()

    # Summary
    elapsed = datetime.now() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("SCAN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total models processed: {len(models)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total time: {Timer._format_duration(total_elapsed)}")
    logger.info(f"Output directory: {output_dir}")
    if args.deploy:
        logger.info(f"Deployed to: {web_root}")
    else:
        logger.info("Deployment: SKIPPED (use --deploy flag)")
    logger.info("=" * 60)

    # Print detailed timing report
    stats.report(logger)

    # Save run summary
    summary_file = PROJECT_ROOT / "data" / "last_run.json"
    summary_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_models": len(models),
        "successful": successful,
        "failed": failed,
        "elapsed_seconds": elapsed.total_seconds(),
        "deployed": args.deploy,
    }, indent=2))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
