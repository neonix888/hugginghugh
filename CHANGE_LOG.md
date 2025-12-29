# CHANGE_LOG.md

Concise changelog for all project changes. Format: `[date] - [type] - [description]`

**Types:** `feat` (feature), `fix` (bug fix), `sec` (security), `docs` (documentation), `refactor`, `test`, `deploy`, `config`

---

## 2025-12-29

- `docs` - Updated CLAUDE.md with comprehensive operating rules (no hardcoding, approval gates, output format, API safety)
- `config` - Set up pre-commit hooks with 10 automated checks
- `config` - Created .pre-commit-config.yaml (black, isort, bandit, flake8, detect-secrets, etc.)
- `config` - Created pyproject.toml (consolidated tool configuration)
- `config` - Created .flake8 (linting configuration)
- `config` - Created .secrets.baseline (secrets detection baseline)
- `config` - Updated requirements.txt with pre-commit, flake8, detect-secrets
- `style` - Auto-formatted 27 Python files with black
- `style` - Auto-sorted imports in 3 files with isort
- `docs` - Verified blog infrastructure complete (BlogGenerator, templates, CSS, 3 posts)
- `docs` - Updated TASKS.md marking Phase 3 Content Marketing complete
- `docs` - Verified badge infrastructure complete (BadgeGenerator, 4 SVG styles, shields.io JSON endpoints)
- `docs` - Updated TASKS.md marking Phase 4 Viral Mechanics complete
- `docs` - Verified Twitter bot complete (TwitterBot, 7 tweet types, CLI script, daily scan integration)
- `docs` - Updated TASKS.md marking Phase 5 Social Presence complete

---

## 2025-12-26

- `deploy` - Migrated to hugginghugh.com domain with SSL (Let's Encrypt, expires March 2026)
- `config` - Created nginx config for hugginghugh.com with www/HTTP redirects
- `sec` - Added security headers (HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- `feat` - Added Open Graph meta tags to all templates
- `feat` - Added Twitter Card meta tags to all templates
- `feat` - Added JSON-LD structured data (WebSite, Organization schemas)
- `feat` - Created sitemap.xml generator with all pages + model reports
- `feat` - Created robots.txt generator
- `feat` - Created favicon.svg (shield with checkmark)
- `config` - Added site_url parameter to DashboardGenerator and HTMLReportGenerator
- `config` - Updated nginx with explicit location blocks for /robots.txt and /sitemap.xml

---

## 2025-12-25

- `refactor` - Replaced all emoji icons with professional inline SVG icons
- `feat` - Added SVG icon CSS framework to style.css
- `deploy` - Production deployment with 501 models

---

## 2025-12-13

- `feat` - Updated Hero section with new messaging (security-first, free, no paywall)
- `feat` - Added hero badges (Security-First Scoring, Free SBOM Reports, Updated Daily)
- `feat` - Expanded model scanning from 100 to 1,000 models
- `config` - Updated minimum deployment threshold from 100 to 500

---

## 2025-12-11

- `feat` - Added grade distribution cards (A/B/C/D/F) on dashboard
- `feat` - Increased models scanned from 50 to 100
- `feat` - Added "Load More" pagination (20 models at a time)
- `feat` - Created individual grade pages (/grade/a.html, /grade/b.html, etc.)
- `feat` - Implemented PostgreSQL leaderboard system (score_history, current_rankings, hall_of_fame)
- `feat` - Created leaderboard podium on front page (top 3 models)
- `feat` - Created full leaderboard page (/leaderboard.html)
- `fix` - Fixed deployment permissions (sudo for www-data owned directories)
- `feat` - Added global "Buy Me a Coffee" support card to base.html
- `feat` - Added OSV-Scanner integration alongside Grype
- `feat` - Added timing tracking to daily scan script (Timer, TimingStats classes)
- `feat` - Added Environment Checklist (minimum safe versions for ML packages)
- `feat` - Expanded ML framework dependency detection (40+ frameworks)
- `feat` - Improved trust score algorithm (security factors = 51%)
- `docs` - Added methodology disclaimer to About page
- `sec` - Security audit with bandit - fixed HIGH/MEDIUM issues
- `sec` - Fixed os.system() shell injection - replaced with subprocess.run()
- `sec` - Added revision pinning to HuggingFace downloads
- `sec` - Dependency scan with safety - 0 vulnerabilities
- `test` - Unit tests for trust_scorer (94%), license_analyzer (85%), dashboard (62%)

---

## 2025-12-10

- `deploy` - Deployed to production at https://hugginghugh.etcbin.io
- `deploy` - SSL certificate from Let's Encrypt (expires March 10, 2026)
- `deploy` - Production scan with 50 top HuggingFace models
- `fix` - Fixed trust score summary text (changed to "X of 8 factors passed")
- `feat` - Added tooltip explanations for all 8 trust factors
- `feat` - Added deployment safeguards (--deploy flag, min 50 models check)
- `feat` - Created self-SBOM generator (scripts/generate_self_sbom.py)
- `feat` - Generated self-SBOM report at /sbom.html

---

## 2024-12-10

- `docs` - Created CLAUDE.md with DevSecOps practices
- `docs` - Created ROADMAP.md for milestone tracking
- `docs` - Created TASKS.md for task checklist
- `docs` - Created docs/HUGGINGFACE_DEEP_DIVE.md (comprehensive HF ecosystem guide)
- `config` - Initialized git repository (commit: 0782e19)
- `config` - Added comprehensive .gitignore (Python/ML exclusions)
- `feat` - Built HuggingFace API client (src/scanner/hf_client.py)
- `feat` - Built top models fetcher (src/scanner/top_models.py)
- `feat` - Built model metadata fetcher (src/scanner/model_fetcher.py)
- `feat` - Built SBOM generator with ML dependency inference
- `feat` - Built vulnerability scanner integration (Grype)
- `feat` - Built license analyzer
- `feat` - Built trust score calculator
- `feat` - Built HTML report generator (Nutrition Label style)
- `feat` - Built dashboard generator
- `feat` - Created daily scan orchestrator script
- `feat` - Created Nginx setup script
- `feat` - Created cron job setup script
- `fix` - Fixed CycloneDX 1.5+ tools format (dict vs list) in sbom_generator.py
- `fix` - Fixed NoneType error when license is None in license_analyzer.py

---

## Template

```
## YYYY-MM-DD

- `type` - Description of change
```
