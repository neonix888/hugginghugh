#!/usr/bin/env python3
"""
Disk cleanup module for HuggingHugh nightly scans.

Handles log rotation, stale cache pruning, and disk space checks.
Can be used standalone or imported by run_daily_scan.py.

Usage:
    python scripts/cleanup.py                # Dry-run (show what would be cleaned)
    python scripts/cleanup.py --execute      # Actually clean up
    python scripts/cleanup.py --disk-check   # Only check disk space
"""
import argparse
import logging
import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

logger = logging.getLogger(__name__)

# Retention defaults
LOG_RETENTION_DAYS = 7
MAX_LOG_SIZE_MB = 10
DISK_WARN_PERCENT = 85
DISK_ABORT_PERCENT = 90


def get_disk_usage_percent(path: str = "/") -> float:
    """Return disk usage percentage for the filesystem containing path."""
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bavail * stat.f_frsize
    used = total - free
    return (used / total) * 100 if total > 0 else 0.0


def check_disk_space(
    path: str = "/",
    warn_pct: float = DISK_WARN_PERCENT,
    abort_pct: float = DISK_ABORT_PERCENT,
) -> dict:
    """
    Check disk space and return status.

    Returns dict with keys: percent, free_gb, status ('ok', 'warning', 'critical')
    """
    stat = os.statvfs(path)
    total = stat.f_blocks * stat.f_frsize
    free = stat.f_bavail * stat.f_frsize
    used_pct = ((total - free) / total) * 100 if total > 0 else 0.0
    free_gb = free / (1024**3)

    if used_pct >= abort_pct:
        status = "critical"
    elif used_pct >= warn_pct:
        status = "warning"
    else:
        status = "ok"

    return {
        "percent": round(used_pct, 1),
        "free_gb": round(free_gb, 1),
        "status": status,
    }


def cleanup_old_logs(
    logs_dir: Path,
    retention_days: int = LOG_RETENTION_DAYS,
    dry_run: bool = True,
) -> int:
    """
    Delete scan log files older than retention_days.

    Returns bytes freed.
    """
    cutoff = datetime.now() - timedelta(days=retention_days)
    freed = 0

    for log_file in logs_dir.glob("scan_*.log"):
        if datetime.fromtimestamp(log_file.stat().st_mtime) < cutoff:
            size = log_file.stat().st_size
            if dry_run:
                logger.info(f"  [DRY RUN] Would delete {log_file.name} ({size // 1024}K)")
            else:
                log_file.unlink()
                logger.info(f"  Deleted {log_file.name} ({size // 1024}K)")
            freed += size

    return freed


def rotate_log_file(
    log_path: Path,
    max_size_mb: float = MAX_LOG_SIZE_MB,
    keep_lines: int = 500,
    dry_run: bool = True,
) -> int:
    """
    Truncate a log file if it exceeds max_size_mb, keeping the last keep_lines lines.

    Returns bytes freed.
    """
    if not log_path.exists():
        return 0

    size = log_path.stat().st_size
    max_bytes = max_size_mb * 1024 * 1024

    if size <= max_bytes:
        return 0

    if dry_run:
        logger.info(
            f"  [DRY RUN] Would truncate {log_path.name} "
            f"({size // (1024*1024)}M -> keep last {keep_lines} lines)"
        )
        return size  # approximate

    # Read last N lines and rewrite
    try:
        with open(log_path, "rb") as f:
            lines = f.readlines()
        tail = lines[-keep_lines:] if len(lines) > keep_lines else lines
        with open(log_path, "wb") as f:
            f.writelines(tail)
        new_size = log_path.stat().st_size
        freed = size - new_size
        logger.info(f"  Truncated {log_path.name}: {size // (1024*1024)}M -> {new_size // 1024}K")
        return freed
    except Exception as e:
        logger.warning(f"  Failed to rotate {log_path.name}: {e}")
        return 0


def cleanup_stale_reports(
    reports_dir: Path,
    current_models: set,
    dry_run: bool = True,
) -> int:
    """
    Remove report directories for models no longer in the scan list.

    Returns bytes freed.
    """
    if not reports_dir.exists():
        return 0

    freed = 0
    for report_dir in reports_dir.iterdir():
        if report_dir.is_dir() and report_dir.name not in current_models:
            size = sum(f.stat().st_size for f in report_dir.rglob("*") if f.is_file())
            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would delete stale report: {report_dir.name} ({size // 1024}K)"
                )
            else:
                shutil.rmtree(report_dir)
                logger.info(f"  Deleted stale report: {report_dir.name} ({size // 1024}K)")
            freed += size

    return freed


def cleanup_stale_sboms(
    sboms_dir: Path,
    current_models: set,
    dry_run: bool = True,
) -> int:
    """
    Remove SBOM/vuln files for models no longer in the scan list.

    Returns bytes freed.
    """
    if not sboms_dir.exists():
        return 0

    freed = 0
    # SBOM files are named like: Author_ModelName_sbom.json, Author_ModelName_vulns.json
    for sbom_file in sboms_dir.glob("*_sbom.json"):
        model_key = sbom_file.name.replace("_sbom.json", "")
        if model_key not in current_models:
            size = sbom_file.stat().st_size
            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would delete stale SBOM: {sbom_file.name} ({size // 1024}K)"
                )
            else:
                sbom_file.unlink()
                logger.info(f"  Deleted stale SBOM: {sbom_file.name}")
            freed += size
            # Also remove matching vulns file
            vulns_file = sboms_dir / sbom_file.name.replace("_sbom.json", "_vulns.json")
            if vulns_file.exists():
                vsize = vulns_file.stat().st_size
                if not dry_run:
                    vulns_file.unlink()
                freed += vsize

    return freed


def cleanup_stale_model_cache(
    models_dir: Path,
    current_models: set,
    dry_run: bool = True,
) -> int:
    """
    Remove cached model directories for models no longer in the scan list.

    Returns bytes freed.
    """
    if not models_dir.exists():
        return 0

    freed = 0
    for model_dir in models_dir.iterdir():
        if model_dir.is_dir() and model_dir.name not in current_models:
            size = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
            if dry_run:
                logger.info(
                    f"  [DRY RUN] Would delete stale cache: {model_dir.name} ({size // 1024}K)"
                )
            else:
                shutil.rmtree(model_dir)
                logger.info(f"  Deleted stale cache: {model_dir.name} ({size // 1024}K)")
            freed += size

    return freed


def run_full_cleanup(
    project_root: Path = PROJECT_ROOT,
    current_model_dirs: set = None,
    dry_run: bool = True,
) -> dict:
    """
    Run all cleanup tasks.

    Args:
        project_root: Project root directory
        current_model_dirs: Set of current model directory names (safe_filename format).
                           If None, skips model-based pruning.
        dry_run: If True, only report what would be done.

    Returns:
        Dict with cleanup stats.
    """
    mode = "DRY RUN" if dry_run else "EXECUTING"
    logger.info(f"=== Cleanup ({mode}) ===")

    stats = {"logs_freed": 0, "reports_freed": 0, "sboms_freed": 0, "cache_freed": 0}

    logs_dir = project_root / "logs"
    data_dir = project_root / "data"
    output_dir = project_root / "output"

    # 1. Old scan logs
    logger.info("Cleaning old scan logs...")
    stats["logs_freed"] += cleanup_old_logs(logs_dir, dry_run=dry_run)

    # 2. Rotate cron.log and news.log
    logger.info("Checking log rotation...")
    stats["logs_freed"] += rotate_log_file(logs_dir / "cron.log", dry_run=dry_run)
    stats["logs_freed"] += rotate_log_file(logs_dir / "news.log", dry_run=dry_run)

    # 3. Model-based pruning (only if we know the current set)
    if current_model_dirs:
        logger.info(f"Pruning stale data (current set: {len(current_model_dirs)} models)...")
        stats["reports_freed"] = cleanup_stale_reports(
            output_dir / "reports", current_model_dirs, dry_run=dry_run
        )
        stats["sboms_freed"] = cleanup_stale_sboms(
            data_dir / "sboms", current_model_dirs, dry_run=dry_run
        )
        stats["cache_freed"] = cleanup_stale_model_cache(
            data_dir / "models", current_model_dirs, dry_run=dry_run
        )

    total = sum(stats.values())
    logger.info(
        f"Cleanup {'would free' if dry_run else 'freed'}: "
        f"{total / (1024*1024):.1f} MB total "
        f"(logs: {stats['logs_freed']/(1024*1024):.1f}M, "
        f"reports: {stats['reports_freed']/(1024*1024):.1f}M, "
        f"sboms: {stats['sboms_freed']/(1024*1024):.1f}M, "
        f"cache: {stats['cache_freed']/(1024*1024):.1f}M)"
    )

    return stats


def main():
    parser = argparse.ArgumentParser(description="HuggingHugh Disk Cleanup")
    parser.add_argument(
        "--execute", action="store_true", help="Actually perform cleanup (default is dry-run)"
    )
    parser.add_argument("--disk-check", action="store_true", help="Only check disk space")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Disk check
    disk = check_disk_space("/")
    logger.info(f"Disk usage: {disk['percent']}% ({disk['free_gb']} GB free) - {disk['status']}")

    if args.disk_check:
        return 0 if disk["status"] != "critical" else 1

    # Get current model list from data/models/
    models_dir = PROJECT_ROOT / "data" / "models"
    current_models = set()
    if models_dir.exists():
        current_models = {d.name for d in models_dir.iterdir() if d.is_dir()}

    dry_run = not args.execute
    run_full_cleanup(
        project_root=PROJECT_ROOT,
        current_model_dirs=current_models if current_models else None,
        dry_run=dry_run,
    )

    # Final disk check
    disk_after = check_disk_space("/")
    logger.info(f"Disk after: {disk_after['percent']}% ({disk_after['free_gb']} GB free)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
