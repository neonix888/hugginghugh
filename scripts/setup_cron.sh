#!/bin/bash
#
# HuggingHugh Cron Setup
# Sets up daily scanning at 23:00 UTC and news digest at 06:00 UTC
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
SCAN_SCRIPT="$PROJECT_DIR/scripts/run_daily_scan.py"
NEWS_SCRIPT="$PROJECT_DIR/scripts/run_daily_news.py"
SCAN_LOG="$PROJECT_DIR/logs/cron.log"
NEWS_LOG="$PROJECT_DIR/logs/news.log"

echo "=== HuggingHugh Cron Setup ==="
echo "Project directory: $PROJECT_DIR"
echo "Python path: $VENV_PYTHON"
echo "Scan script: $SCAN_SCRIPT"
echo "News script: $NEWS_SCRIPT"

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $VENV_PYTHON"
    echo "Please run: python3 -m venv $PROJECT_DIR/venv && source $PROJECT_DIR/venv/bin/activate && pip install -r $PROJECT_DIR/requirements.txt"
    exit 1
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Make scripts executable
chmod +x "$SCAN_SCRIPT"
chmod +x "$NEWS_SCRIPT"

# Cron job entries
# 1. Model scan: runs at 23:00 UTC daily (500 models, 4 workers, deploy to production)
#    NOTE: systemd-run --user --scope was removed -- it requires a D-Bus session
#    which is unavailable in cron.  Memory is managed via --workers 4 instead.
SCAN_CRON="0 23 * * * $VENV_PYTHON $SCAN_SCRIPT --deploy --limit 500 --workers 4 >> $SCAN_LOG 2>&1"

# 2. News digest: runs at 06:00 UTC daily (after scan completes)
NEWS_CRON="0 6 * * * $VENV_PYTHON $NEWS_SCRIPT >> $NEWS_LOG 2>&1"

# Remove existing hugginghugh entries
if crontab -l 2>/dev/null | grep -q "hugginghugh\|HuggingHugh"; then
    echo "Removing existing HuggingHugh cron jobs..."
    crontab -l 2>/dev/null | grep -v -E "hugginghugh|HuggingHugh|run_daily_scan|run_daily_news" | crontab -
fi

# Add new cron jobs
(crontab -l 2>/dev/null || echo "") | {
    cat
    echo "# HuggingHugh daily model scan (23:00 UTC)"
    echo "$SCAN_CRON"
    echo "# HuggingHugh daily news digest (06:00 UTC)"
    echo "$NEWS_CRON"
} | crontab -

echo ""
echo "Cron jobs installed:"
echo ""
echo "1. Model Scan (23:00 UTC):"
echo "   $SCAN_CRON"
echo ""
echo "2. News Digest (06:00 UTC):"
echo "   $NEWS_CRON"
echo ""
echo "Current crontab:"
crontab -l | grep -E "HuggingHugh|hugginghugh" -A1 || echo "(no HuggingHugh entries)"
echo ""
echo "Log files:"
echo "  Scan: $SCAN_LOG"
echo "  News: $NEWS_LOG"
echo ""
echo "To run manually:"
echo "  $VENV_PYTHON $SCAN_SCRIPT --limit 5 --verbose"
echo "  $VENV_PYTHON $NEWS_SCRIPT --dry-run"
echo ""
echo "To check logs:"
echo "  tail -f $SCAN_LOG"
echo "  tail -f $NEWS_LOG"
