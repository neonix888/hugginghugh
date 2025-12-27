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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scanner import HuggingFaceClient, get_top_models, ModelFetcher
from src.generator import SBOMGenerator, VulnerabilityScanner, LicenseAnalyzer, TrustScorer
from src.reporter import HTMLReportGenerator, DashboardGenerator, BlogGenerator, BadgeGenerator
from src.database import LeaderboardDB


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
  %(prog)s                      # Scan 1000 models with 8 workers, no deploy
  %(prog)s --limit 10           # Scan 10 models for testing, no deploy
  %(prog)s --deploy             # Scan 1000 models and deploy to production
  %(prog)s --deploy --force     # Force re-scan all and deploy
  %(prog)s -w 16                # Use 16 parallel workers (faster on multi-core)

SAFEGUARDS:
  - Deployment requires explicit --deploy flag
  - Minimum 500 models required for deployment
  - Use --min-models to override (not recommended)

PERFORMANCE:
  - Default 8 workers process ~8 models concurrently
  - Increase --workers for faster scans on multi-core systems
  - Decrease --workers if hitting rate limits or memory issues
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
    parser.add_argument("--tweet", action="store_true",
                        help="Post tweets about scan results (requires Twitter API credentials)")
    parser.add_argument("--tweet-dry-run", action="store_true",
                        help="Show what tweets would be posted without actually posting")
    parser.add_argument("--workers", "-w", type=int, default=8,
                        help="Number of parallel workers (default: 8)")
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
    content_dir = PROJECT_ROOT / "content"
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
    blog_gen = BlogGenerator(
        templates_dir=templates_dir,
        content_dir=content_dir,
        output_dir=output_dir,
        base_url="",
    )
    badge_gen = BadgeGenerator(
        output_dir=output_dir,
    )

    # Initialize database connection for history data
    # This is used for read-only queries to fetch historical data for reports
    try:
        history_db = LeaderboardDB()
        history_db.connect()
        logger.info("Connected to leaderboard database for history data")
    except Exception as e:
        logger.warning(f"Could not connect to database for history: {e}")
        history_db = None

    stats.record("1. Initialization", phase_timer.stop())

    # Step 1: Fetch top models
    phase_timer = Timer("Fetch Models", logger).start()
    logger.info(f"Fetching top {args.limit} models from HuggingFace...")
    models = get_top_models(limit=args.limit, token=hf_token)
    logger.info(f"Found {len(models)} models")
    stats.record("2. Fetch Model List", phase_timer.stop())

    # Step 2: Process models in parallel
    phase_timer = Timer("Process Models", logger).start()
    all_results = []
    successful = 0
    failed = 0
    results_lock = Lock()
    progress_lock = Lock()
    processed_count = [0]  # Use list for mutable counter in closure

    def process_single_model(model_with_index):
        """Process a single model - runs in thread pool."""
        i, model = model_with_index
        model_timer = Timer(f"Model {i}", None).start()

        try:
            # Fetch metadata
            metadata = fetcher.fetch_model_metadata(model, force=args.force)

            # Generate SBOM
            sbom = sbom_gen.generate_sbom(metadata)

            # Get versioned requirements for OSV-Scanner
            requirements = sbom_gen._infer_requirements(metadata)

            # Scan vulnerabilities (Grype + OSV-Scanner) - main bottleneck
            vulns = vuln_scanner.scan_sbom(sbom, model.model_id, requirements=requirements)

            # Analyze license
            model_license = license_analyzer.analyze_model_license(metadata)
            sbom_licenses = license_analyzer.analyze_sbom_licenses(sbom)
            license_summary = license_analyzer.get_license_summary(model_license, sbom_licenses)

            # Calculate trust score
            trust_score = trust_scorer.calculate_score(metadata, vulns, license_summary)

            # Generate HTML report (with history data if available)
            html_gen.generate_model_report(
                model_metadata=metadata,
                sbom=sbom,
                vulnerabilities=vulns,
                trust_score=trust_score,
                license_analysis=license_summary,
                db=history_db,
            )

            elapsed = model_timer.stop()

            # Return result
            return {
                "success": True,
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
                "elapsed": elapsed,
            }

        except Exception as e:
            elapsed = model_timer.stop()
            return {
                "success": False,
                "model_id": model.model_id,
                "error": str(e),
                "elapsed": elapsed,
            }

    # Process models in parallel
    num_workers = min(args.workers, len(models))
    logger.info(f"Processing {len(models)} models with {num_workers} parallel workers...")

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        # Submit all tasks
        future_to_model = {
            executor.submit(process_single_model, (i, model)): model
            for i, model in enumerate(models, 1)
        }

        # Process results as they complete
        for future in as_completed(future_to_model):
            result = future.result()
            with progress_lock:
                processed_count[0] += 1
                count = processed_count[0]

            if result["success"]:
                with results_lock:
                    all_results.append(result)
                    successful += 1
                elapsed_str = Timer._format_duration(result["elapsed"])
                logger.info(f"[{count}/{len(models)}] {result['model_id']} - Score: {result['trust_score']} ({result['trust_grade']}) - {elapsed_str}")
                stats.record_model(result["model_id"], result["elapsed"])
            else:
                with results_lock:
                    failed += 1
                logger.error(f"[{count}/{len(models)}] FAILED: {result['model_id']} - {result['error']}")
                stats.record_model(result["model_id"], result["elapsed"])

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

    # Step 5.5: Generate blog pages
    blog_posts = []
    logger.info("\nGenerating blog pages...")
    try:
        blog_posts = blog_gen.load_posts()
        if blog_posts:
            blog_gen.generate_all()
            logger.info(f"  Blog generated: {len(blog_posts)} posts")
        else:
            logger.info("  No blog posts found")
    except Exception as e:
        logger.warning(f"  Failed to generate blog: {e}")

    # Step 5.6: Generate badges
    logger.info("\nGenerating badges...")
    try:
        badge_count = badge_gen.generate_all_badges(all_results)
        logger.info(f"  Badges generated: {badge_count} models")

        # Generate badges page
        badges_template = templates_dir / "badges.html"
        if badges_template.exists():
            from jinja2 import Environment, FileSystemLoader
            env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
            template = env.get_template("badges.html")
            html_content = template.render(
                base_url="",
                site_url="https://hugginghugh.com",
                last_updated=datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
            )
            (output_dir / "badges.html").write_text(html_content)
            logger.info("  Badges page generated")
    except Exception as e:
        logger.warning(f"  Failed to generate badges: {e}")

    # Step 5.7: Generate SEO files (sitemap.xml, robots.txt)
    logger.info("\nGenerating SEO files...")
    try:
        dashboard_gen.generate_sitemap(all_results, blog_posts=blog_posts)
        dashboard_gen.generate_robots_txt()
        logger.info("  SEO files generated successfully")
    except Exception as e:
        logger.warning(f"  Failed to generate SEO files: {e}")

    # Step 5.8: Post to Twitter (only with --tweet or --tweet-dry-run flag)
    if args.tweet or args.tweet_dry_run:
        logger.info("\nRunning Twitter bot...")
        try:
            from src.social.twitter_bot import TwitterBot

            bot = TwitterBot(dry_run=args.tweet_dry_run)

            if not bot.is_configured() and not args.tweet_dry_run:
                logger.warning("  Twitter API credentials not configured")
                logger.info("  Set TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET")
            else:
                tweets_posted = bot.run_daily_tweets(
                    models_data=all_results,
                    leaderboard_data=leaderboard_data,
                )
                if args.tweet_dry_run:
                    logger.info(f"  [DRY RUN] Would post {tweets_posted} tweets")
                else:
                    logger.info(f"  Posted {tweets_posted} tweets")
        except Exception as e:
            logger.warning(f"  Failed to run Twitter bot: {e}")

    # Step 6: Deploy to production (only with --deploy flag)
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

    # Cleanup: Close history database connection
    if history_db:
        try:
            history_db.close()
            logger.debug("Closed history database connection")
        except Exception:
            pass

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
