#!/bin/bash
#
# HuggingHugh Installation Script
# Sets up the entire project from scratch
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== HuggingHugh Installation ==="
echo "Project directory: $PROJECT_DIR"
echo ""

cd "$PROJECT_DIR"

# Step 1: Create virtual environment
echo "[1/5] Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  Virtual environment created"
else
    echo "  Virtual environment already exists"
fi

# Step 2: Install dependencies
echo "[2/5] Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
echo "  Dependencies installed"

# Step 3: Create necessary directories
echo "[3/5] Creating directories..."
mkdir -p data/{models,sboms,cache}
mkdir -p logs
mkdir -p output/{reports,api,static}
echo "  Directories created"

# Step 4: Verify external tools
echo "[4/5] Verifying external tools..."

if command -v syft &> /dev/null; then
    SYFT_VERSION=$(syft version 2>/dev/null | head -1)
    echo "  Syft: $SYFT_VERSION"
else
    echo "  WARNING: Syft not found. Install from: https://github.com/anchore/syft"
fi

if command -v grype &> /dev/null; then
    GRYPE_VERSION=$(grype version 2>/dev/null | head -1)
    echo "  Grype: $GRYPE_VERSION"
else
    echo "  WARNING: Grype not found. Install from: https://github.com/anchore/grype"
fi

# Step 5: Test imports
echo "[5/5] Testing imports..."
python3 -c "
from src.scanner import HuggingFaceClient, get_top_models, ModelFetcher
from src.generator import SBOMGenerator, VulnerabilityScanner, LicenseAnalyzer, TrustScorer
from src.reporter import HTMLReportGenerator, DashboardGenerator
print('  All imports successful')
"

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo ""
echo "1. Set HuggingFace token (optional, for higher rate limits):"
echo "   export HF_TOKEN=hf_xxx"
echo ""
echo "2. Run a test scan:"
echo "   source venv/bin/activate"
echo "   python scripts/run_daily_scan.py --dry-run --limit 5 --verbose"
echo ""
echo "3. Configure Nginx and SSL:"
echo "   sudo ./scripts/setup_nginx.sh"
echo ""
echo "4. Set up daily cron job:"
echo "   ./scripts/setup_cron.sh"
echo ""
