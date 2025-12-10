# HuggingHugh Architecture

**"Nutrition Labels for AI Models"** - SBOM Dashboard for Hugging Face Models

## Overview

HuggingHugh provides comprehensive Software Bill of Materials (SBOM) reports for the top 50 most downloaded models on Hugging Face Hub. Think of it as nutrition facts for AI models - know what you're consuming before you use it.

**URL:** https://hugginghugh.etcbin.io

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HUGGINGHUGH SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         DAILY CRON JOB                               │   │
│  │                    (runs at 02:00 UTC daily)                         │   │
│  └───────────────────────────────┬─────────────────────────────────────┘   │
│                                  │                                          │
│                                  ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      SCANNER PIPELINE                                │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │   │
│  │  │ 1. Fetch │  │2. Download│  │ 3. Scan  │  │4. Analyze│            │   │
│  │  │ Top 50   │─►│ Metadata │─►│   SBOM   │─►│  Vulns   │            │   │
│  │  │  Models  │  │ + Files  │  │  (Syft)  │  │ (Grype)  │            │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘            │   │
│  │                                                    │                 │   │
│  │                                                    ▼                 │   │
│  │                               ┌──────────┐  ┌──────────┐            │   │
│  │                               │5. License│  │ 6. Trust │            │   │
│  │                               │  Analyze │  │   Score  │            │   │
│  │                               └──────────┘  └──────────┘            │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      REPORT GENERATOR                                │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  Individual  │  │   Dashboard  │  │     JSON     │               │   │
│  │  │    Model     │  │    Index     │  │   API Data   │               │   │
│  │  │   Reports    │  │    Page      │  │    Files     │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      STATIC FILE SERVER                              │   │
│  │                  /var/www/hugginghugh.etcbin.io/                     │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │   │
│  │  │  index.html  │  │   reports/   │  │    api/      │               │   │
│  │  │  (Dashboard) │  │  (Per-model) │  │  (JSON data) │               │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘               │   │
│  └───────────────────────────────────┬─────────────────────────────────┘   │
│                                      │                                      │
│                                      ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         NGINX + SSL                                  │   │
│  │              hugginghugh.etcbin.io (Let's Encrypt)                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
/home/carloacutis/projects/huggingface/
├── CLAUDE.md                    # Development practices
├── ROADMAP.md                   # Project milestones
├── TASKS.md                     # Task tracking
├── docs/
│   ├── ARCHITECTURE.md          # This file
│   └── HUGGINGFACE_DEEP_DIVE.md # HF ecosystem reference
├── src/
│   ├── scanner/
│   │   ├── __init__.py
│   │   ├── hf_client.py         # HuggingFace Hub API client
│   │   ├── model_fetcher.py     # Download model metadata & files
│   │   └── top_models.py        # Get top 50 models by downloads
│   ├── generator/
│   │   ├── __init__.py
│   │   ├── sbom_generator.py    # Generate SBOM using Syft
│   │   ├── vuln_scanner.py      # Scan with Grype
│   │   ├── license_analyzer.py  # Analyze licenses
│   │   └── trust_scorer.py      # Calculate trust score
│   ├── reporter/
│   │   ├── __init__.py
│   │   ├── html_generator.py    # Generate HTML reports
│   │   ├── dashboard.py         # Generate dashboard index
│   │   └── templates.py         # Jinja2 template loader
│   └── api/
│       ├── __init__.py
│       └── json_export.py       # Export JSON API data
├── templates/
│   ├── base.html                # Base template
│   ├── dashboard.html           # Main dashboard
│   ├── model_report.html        # Individual model report
│   └── components/
│       ├── header.html
│       ├── footer.html
│       ├── nutrition_label.html # The "nutrition facts" component
│       └── vuln_table.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── dashboard.js
│   └── reports/                 # Generated reports (gitignored)
├── data/
│   ├── models/                  # Downloaded model metadata
│   ├── sboms/                   # Generated SBOMs (CycloneDX)
│   └── cache/                   # API response cache
├── config/
│   ├── settings.py              # Configuration
│   └── logging.yaml             # Logging config
├── scripts/
│   ├── run_daily_scan.py        # Main orchestrator
│   ├── setup_nginx.sh           # Nginx configuration
│   └── install.sh               # Installation script
├── tests/
│   └── test_*.py
├── logs/
│   └── scanner.log
├── requirements.txt
└── venv/
```

## Data Flow

### 1. Model Discovery (daily)
```
HuggingFace Hub API
       │
       ▼
GET /api/models?sort=downloads&limit=50
       │
       ▼
[List of top 50 models with metadata]
       │
       ▼
For each model:
  - model_id (e.g., "meta-llama/Llama-2-7b-hf")
  - downloads (e.g., 5,234,567)
  - likes (e.g., 12,345)
  - tags (e.g., ["text-generation", "pytorch"])
  - last_modified
  - library_name (e.g., "transformers")
```

### 2. Model Analysis
```
For each model:
       │
       ▼
Download metadata files (NO large model weights):
  - config.json
  - tokenizer.json
  - tokenizer_config.json
  - README.md (model card)
  - requirements.txt (if present)
       │
       ▼
Infer dependencies from:
  - library_name → transformers version
  - config.json → architecture requirements
  - Model card → stated dependencies
       │
       ▼
Create virtual requirements.txt
       │
       ▼
Run Syft on inferred dependencies
       │
       ▼
Run Grype on SBOM
       │
       ▼
Analyze licenses from model card
       │
       ▼
Calculate trust score
```

### 3. Trust Score Calculation

```
Trust Score (0-100) = weighted sum of:

┌────────────────────────────────────────────────────────┐
│ FACTOR                        │ WEIGHT │ MAX POINTS   │
├────────────────────────────────────────────────────────┤
│ Verified Organization         │  15%   │    15        │
│ SafeTensors Format            │  15%   │    15        │
│ No Critical CVEs              │  20%   │    20        │
│ Clear License                 │  15%   │    15        │
│ Model Card Quality            │  10%   │    10        │
│ Recent Updates (< 90 days)    │  10%   │    10        │
│ Community Engagement          │   5%   │     5        │
│ No Pickle Files               │  10%   │    10        │
├────────────────────────────────────────────────────────┤
│ TOTAL                         │ 100%   │   100        │
└────────────────────────────────────────────────────────┘
```

## Output Files

### Per-Model Report Structure
```
/var/www/hugginghugh.etcbin.io/
├── index.html                              # Dashboard
├── api/
│   ├── models.json                         # All models summary
│   └── models/
│       └── {org}_{model}.json              # Per-model JSON
├── reports/
│   └── {org}/
│       └── {model}/
│           ├── index.html                  # Model report
│           ├── sbom.cdx.json               # CycloneDX SBOM
│           └── vulnerabilities.json        # Grype results
└── static/
    ├── css/
    └── js/
```

## Technology Stack

| Component | Technology | Reason |
|-----------|------------|--------|
| Language | Python 3.11+ | Consistency with other projects |
| SBOM Generation | Syft | Already installed, proven |
| Vuln Scanning | Grype | Already installed, proven |
| Templating | Jinja2 | Simple, powerful |
| HTTP Client | httpx | Async support |
| Web Server | Nginx | Already running |
| SSL | Let's Encrypt | Free, automated |
| Scheduling | Cron | Simple, reliable |

## Security Considerations

1. **No Model Weights Downloaded** - Only metadata files to save space/bandwidth
2. **Sandboxed Scanning** - Run in isolated temp directories
3. **Rate Limiting** - Respect HF API limits (1000 req/hour authenticated)
4. **No User Input** - Static site, no attack surface
5. **Safetensors Detection** - Flag models using pickle format

## Scaling Considerations (Future)

- **Top 100/500**: Increase cron frequency or parallelize
- **On-Demand Scans**: Add FastAPI backend
- **User Accounts**: Integrate with sbomapp authentication
- **API Access**: Add rate-limited JSON API

## Integration with SBOM Ecosystem

```
HuggingHugh                    Existing Projects
───────────                    ─────────────────
HTML Report Style         ←    sbom/sbom_enhanced_html_generator.py
Trust Score Logic         ←    sbomapp/ (tier-based features)
AI Component Discovery    ←    ai_sbom/ (Claude integration - future)
```
