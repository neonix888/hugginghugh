"""
HuggingHugh Configuration Settings
"""
import os
from pathlib import Path

# Base paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

# Data subdirectories
MODELS_DIR = DATA_DIR / "models"
SBOMS_DIR = DATA_DIR / "sboms"
CACHE_DIR = DATA_DIR / "cache"

# Output directory (web root)
WEB_ROOT = Path("/var/www/hugginghugh.etcbin.io")
REPORTS_OUTPUT_DIR = WEB_ROOT / "reports"
API_OUTPUT_DIR = WEB_ROOT / "api"

# HuggingFace API settings
HF_API_URL = "https://huggingface.co/api"
HF_TOKEN = os.environ.get("HF_TOKEN")  # Optional, for higher rate limits
TOP_MODELS_COUNT = 50

# Scanning settings
SCAN_TIMEOUT_SECONDS = 300  # 5 minutes per model
MAX_PARALLEL_SCANS = 4
SKIP_LARGE_FILES_MB = 100  # Skip files larger than this

# Files to download from each model
METADATA_FILES = [
    "config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "preprocessor_config.json",
    "generation_config.json",
    "README.md",
    "requirements.txt",
    "model_index.json",
]

# Trust score weights
TRUST_WEIGHTS = {
    "verified_org": 15,
    "safetensors_format": 15,
    "no_critical_cves": 20,
    "clear_license": 15,
    "model_card_quality": 10,
    "recent_updates": 10,
    "community_engagement": 5,
    "no_pickle_files": 10,
}

# Vulnerability severity mapping
SEVERITY_ORDER = ["critical", "high", "medium", "low", "unknown"]

# License classifications
PERMISSIVE_LICENSES = [
    "mit", "apache-2.0", "bsd-2-clause", "bsd-3-clause", "isc", "unlicense", "cc0-1.0"
]

COPYLEFT_LICENSES = [
    "gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0", "agpl-3.0"
]

RESTRICTIVE_LICENSES = [
    "cc-by-nc-4.0", "cc-by-nc-sa-4.0", "llama2", "llama3", "gemma"
]

# Logging
LOG_FILE = LOGS_DIR / "scanner.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# External tools
SYFT_PATH = os.environ.get("SYFT_PATH", "syft")
GRYPE_PATH = os.environ.get("GRYPE_PATH", "grype")

# Site settings
SITE_NAME = "HuggingHugh"
SITE_TAGLINE = "Nutrition Labels for AI Models"
SITE_URL = "https://hugginghugh.etcbin.io"
BUYMEACOFFEE_URL = "https://buymeacoffee.com/hugginghugh"  # Update with real URL

# Refresh settings
SCAN_SCHEDULE_HOUR = 2  # 02:00 UTC
SCAN_SCHEDULE_MINUTE = 0
