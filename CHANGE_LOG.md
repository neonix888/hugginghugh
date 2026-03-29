# CHANGE_LOG.md

Concise changelog for all project changes. Format: `[date] - [type] - [description]`

**Types:** `feat` (feature), `fix` (bug fix), `sec` (security), `docs` (documentation), `refactor`, `test`, `deploy`, `config`

---

## 2026-03-28

- `fix` - Fixed self-SBOM generation failing daily since Mar 12 (bare `syft`/`grype` not in cron PATH)
- `fix` - Self-SBOM now uses `SYFT_PATH`/`GRYPE_PATH` from config.settings with 300s subprocess timeout
- `fix` - Fixed thread-unsafe shared psycopg2 connection across 4 worker threads (race condition)
- `fix` - LeaderboardDB now uses per-thread connections with auto-reconnect on idle timeout
- `fix` - Added `sudo -n` to news digest deploy commands (matched main scan fix from Mar 12)
- `fix` - Added retry logic (3 attempts, exponential backoff) to HuggingFace model list fetch
- `fix` - Fixed HTTP connection leak: ModelFetcher now properly closed after scan completes
- `fix` - Added pre-scan `grype db update` to prevent 4 parallel 1.4GB DB downloads from worker threads

---

## 2026-03-12

- `fix` - Fixed nightly scan deployment failing since Mar 2 (sudo password prompt in cron)
- `fix` - Added `sudo -n` (non-interactive) flag to all deployment commands
- `fix` - `last_run.json` now always saved even on deploy failure (was silently stale for 10 days)
- `feat` - Added post-scan disk cleanup (scripts/cleanup.py) - log rotation, stale report/SBOM/cache pruning
- `feat` - Added pre-flight disk space check - scan aborts at 90%, warns at 85%
- `fix` - Stopped creating per-run log files in cron (was doubling logs: cron.log + scan_*.log)
- `fix` - Removed tokenizer.json from METADATA_FILES download list (30+ MB each, never used by SBOM generator)
- `fix` - Cleaned up 1.7 GB of accumulated waste: 121 old logs, 264 tokenizer.json files, 285 stale reports
- `config` - Added sudoers setup to setup_cron.sh for passwordless deployment commands
- `fix` - Added Grype temp DB cleanup to nightly process (orphaned downloads consumed 10+ GB)

---

## 2026-02-27

- `feat` - Complete site redesign: CRT terminal aesthetic with phosphor green (#00ff41) on black
- `style` - Full CSS rewrite: JetBrains Mono monospace, no gradients/shadows/animations
- `style` - All SVG icons replaced with ASCII text indicators ([PASS], [FAIL], [WARN])
- `style` - Nutrition label restyled as terminal panel with inverted header
- `style` - Leaderboard: removed podium/medals, plain ranked table
- `style` - Chart.js re-themed: green lines on dark background
- `style` - Header: prompt-style logo (hugginghugh>_) with bracket navigation
- `style` - CRT scanline overlay effect

---

## 2026-02-20

- `feat` - Added persistent PyPI version cache (data/cache/pypi_versions.json) with 24h TTL to sbom_generator.py
- `feat` - Added vulnerability scan dedup cache keyed by requirements hash to vuln_scanner.py
- `feat` - Added parallel Grype + OSV-Scanner execution via ThreadPoolExecutor on cache miss
- `fix` - Fixed broken cron: removed systemd-run wrapper (no D-Bus session in cron), added --workers 4
- `config` - Changed default --workers from 8 to 4 in run_daily_scan.py (prevents OOM on 8GB RAM)
- `config` - Updated cron schedule from 02:00 UTC to 23:00 UTC in setup_cron.sh
- `feat` - Added cache lifecycle to run_daily_scan.py (load/save PyPI cache, log dedup stats)
- `fix` - Updated "Data refreshed daily at 02:00 UTC" to 23:00 UTC in base.html, badges.html, settings.py

---

## 2026-01-10

- `feat` - Added client-side search to leaderboard page (real-time filtering by model name)

---

## 2025-12-30

- `fix` - Fixed cron job failing due to syft/grype not in PATH (broken since Dec 26)
- `config` - Added _find_executable() helper to auto-detect tool paths in cron environments
- `config` - Updated SYFT_PATH/GRYPE_PATH to check ~/.local/bin, /usr/local/bin, /usr/bin
- `deploy` - Manual scan deployed 533 models to hugginghugh.com and hugginghugh.etcbin.io
- `feat` - Added daily AI news digest system (src/news module)
- `feat` - Created NewsFetcher for RSS aggregation from 13 sources (HN, MIT Tech Review, VentureBeat, arXiv, etc.)
- `feat` - Created RelevanceScorer with keyword-based AI security topic scoring
- `feat` - Created DigestGenerator for automatic blog post creation
- `feat` - Added scripts/run_daily_news.py orchestrator with --dry-run and --deploy options
- `config` - Added config/news_sources.yaml for RSS feeds and keyword configuration
- `config` - Updated setup_cron.sh with news digest job at 06:00 UTC
- `docs` - Added 5 blog posts including today's AI news digest
- `deps` - Added feedparser>=6.0.0 to requirements.txt

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
- `docs` - Verified newsletter system complete (FastAPI backend, PostgreSQL storage, frontend form, nginx proxy)
- `docs` - Updated TASKS.md marking Phase 6 Lead Capture complete
- `feat` - Added /subscribers endpoint to newsletter API for full subscriber list
- `sec` - Added API key authentication to /stats and /subscribers endpoints (X-API-Key header)

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
