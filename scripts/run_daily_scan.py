#!/usr/bin/env python3
"""
HuggingHugh Daily Scanner

Main orchestrator script that:
1. Fetches top 50 models from HuggingFace
2. Downloads metadata for each model
3. Generates SBOMs
4. Scans for vulnerabilities
5. Analyzes licenses
6. Calculates trust scores
7. Generates HTML reports
8. Deploys to web directory

Usage:
    python scripts/run_daily_scan.py [--dry-run] [--limit N] [--verbose]
"""
import argparse
import json
import logging
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.scanner import HuggingFaceClient, get_top_models, ModelFetcher
from src.generator import SBOMGenerator, VulnerabilityScanner, LicenseAnalyzer, TrustScorer
from src.reporter import HTMLReportGenerator, DashboardGenerator


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


def main():
    parser = argparse.ArgumentParser(description="HuggingHugh Daily Scanner")
    parser.add_argument("--dry-run", action="store_true", help="Don't deploy to production")
    parser.add_argument("--limit", type=int, default=50, help="Number of models to scan")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--force", "-f", action="store_true", help="Force re-scan all models")
    args = parser.parse_args()

    logger = setup_logging(args.verbose)
    logger.info("=" * 60)
    logger.info("HuggingHugh Daily Scanner Starting")
    logger.info("=" * 60)

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

    # Step 1: Fetch top models
    logger.info(f"Fetching top {args.limit} models from HuggingFace...")
    models = get_top_models(limit=args.limit, token=hf_token)
    logger.info(f"Found {len(models)} models")

    # Step 2: Process each model
    all_results = []
    successful = 0
    failed = 0

    for i, model in enumerate(models, 1):
        logger.info(f"\n[{i}/{len(models)}] Processing: {model.model_id}")
        logger.info(f"  Downloads: {model.downloads:,}, Likes: {model.likes:,}")

        try:
            # Fetch metadata
            logger.info("  Fetching metadata...")
            metadata = fetcher.fetch_model_metadata(model, force=args.force)

            # Generate SBOM
            logger.info("  Generating SBOM...")
            sbom = sbom_gen.generate_sbom(metadata)

            # Scan vulnerabilities
            logger.info("  Scanning vulnerabilities...")
            vulns = vuln_scanner.scan_sbom(sbom, model.model_id)

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

        except Exception as e:
            logger.error(f"  ERROR: Failed to process {model.model_id}: {e}")
            failed += 1
            continue

    # Step 3: Generate dashboard
    logger.info("\nGenerating dashboard...")
    html_gen.copy_static_assets()
    dashboard_gen.generate_dashboard(all_results)
    dashboard_gen.generate_api_json(all_results)
    dashboard_gen.generate_about_page()

    # Step 4: Deploy to production (unless dry-run)
    if not args.dry_run:
        logger.info("\nDeploying to production...")
        if web_root.exists():
            # Backup existing
            backup_dir = web_root.parent / f"hugginghugh_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Sync new files
            logger.info(f"Syncing to {web_root}...")
            if web_root.exists():
                shutil.rmtree(web_root)
            shutil.copytree(output_dir, web_root)

            # Set permissions
            logger.info("Setting permissions...")
            os.system(f"sudo chown -R www-data:www-data {web_root}")
            os.system(f"sudo chmod -R 755 {web_root}")

            logger.info("Deployment complete!")
        else:
            logger.warning(f"Web root {web_root} does not exist, skipping deployment")
    else:
        logger.info("\nDry run - skipping deployment")
        logger.info(f"Output available at: {output_dir}")

    # Summary
    elapsed = datetime.now() - start_time
    logger.info("\n" + "=" * 60)
    logger.info("SCAN SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total models processed: {len(models)}")
    logger.info(f"Successful: {successful}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total time: {elapsed}")
    logger.info(f"Output directory: {output_dir}")
    if not args.dry_run:
        logger.info(f"Deployed to: {web_root}")
    logger.info("=" * 60)

    # Save run summary
    summary_file = PROJECT_ROOT / "data" / "last_run.json"
    summary_file.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "total_models": len(models),
        "successful": successful,
        "failed": failed,
        "elapsed_seconds": elapsed.total_seconds(),
        "dry_run": args.dry_run,
    }, indent=2))

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
