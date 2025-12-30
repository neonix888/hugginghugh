"""
HuggingHugh Configuration Settings
"""

import os
import shutil
from pathlib import Path


def _find_executable(name: str) -> str:
    """Find executable path, checking common locations if not in PATH."""
    # First check environment variable
    env_path = os.environ.get(f"{name.upper()}_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    # Check if in PATH (works in interactive shells)
    which_path = shutil.which(name)
    if which_path:
        return which_path

    # Check common installation locations (for cron environments)
    common_paths = [
        Path.home() / ".local" / "bin" / name,
        Path("/usr/local/bin") / name,
        Path("/usr/bin") / name,
    ]
    for path in common_paths:
        if path.exists():
            return str(path)

    # Fall back to just the command name (will fail if not in PATH)
    return name


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
    "mit",
    "apache-2.0",
    "bsd-2-clause",
    "bsd-3-clause",
    "isc",
    "unlicense",
    "cc0-1.0",
]

COPYLEFT_LICENSES = ["gpl-2.0", "gpl-3.0", "lgpl-2.1", "lgpl-3.0", "agpl-3.0"]

RESTRICTIVE_LICENSES = ["cc-by-nc-4.0", "cc-by-nc-sa-4.0", "llama2", "llama3", "gemma"]

# Logging
LOG_FILE = LOGS_DIR / "scanner.log"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# External tools (auto-detect paths for cron compatibility)
SYFT_PATH = _find_executable("syft")
GRYPE_PATH = _find_executable("grype")

# Site settings
SITE_NAME = "HuggingHugh"
SITE_TAGLINE = "Nutrition Labels for AI Models"
SITE_URL = "https://hugginghugh.etcbin.io"
BUYMEACOFFEE_URL = "https://buymeacoffee.com/hugginghugh"  # Update with real URL

# Refresh settings
SCAN_SCHEDULE_HOUR = 2  # 02:00 UTC
SCAN_SCHEDULE_MINUTE = 0
