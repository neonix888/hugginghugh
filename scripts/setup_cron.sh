#!/bin/bash
#
# HuggingHugh Cron Setup
# Sets up daily scanning at 02:00 UTC
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_DIR/venv/bin/python3"
SCAN_SCRIPT="$PROJECT_DIR/scripts/run_daily_scan.py"
LOG_FILE="$PROJECT_DIR/logs/cron.log"

echo "=== HuggingHugh Cron Setup ==="
echo "Project directory: $PROJECT_DIR"
echo "Python path: $VENV_PYTHON"
echo "Scan script: $SCAN_SCRIPT"

# Check if venv exists
if [ ! -f "$VENV_PYTHON" ]; then
    echo "ERROR: Virtual environment not found at $VENV_PYTHON"
    echo "Please run: python3 -m venv $PROJECT_DIR/venv && source $PROJECT_DIR/venv/bin/activate && pip install -r $PROJECT_DIR/requirements.txt"
    exit 1
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Make scan script executable
chmod +x "$SCAN_SCRIPT"

# Cron job entry (runs at 02:00 UTC daily)
# Scans 500 models and deploys to production
CRON_ENTRY="0 2 * * * $VENV_PYTHON $SCAN_SCRIPT --deploy --limit 500 >> $LOG_FILE 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "hugginghugh"; then
    echo "Cron job already exists. Updating..."
    # Remove existing hugginghugh entries
    crontab -l 2>/dev/null | grep -v "hugginghugh" | crontab -
fi

# Add new cron job
(crontab -l 2>/dev/null || echo "") | { cat; echo "# HuggingHugh daily scan"; echo "$CRON_ENTRY"; } | crontab -

echo ""
echo "Cron job installed:"
echo "$CRON_ENTRY"
echo ""
echo "Current crontab:"
crontab -l | grep -A1 "hugginghugh" || echo "(no hugginghugh entries)"
echo ""
echo "Logs will be written to: $LOG_FILE"
echo ""
echo "To run manually:"
echo "  $VENV_PYTHON $SCAN_SCRIPT --dry-run"
echo ""
echo "To check cron logs:"
echo "  tail -f $LOG_FILE"
