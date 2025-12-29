# TASKS.md

Granular task checklist for ongoing development. Update this document as tasks progress.

## Active Sprint

**Sprint:** HuggingHugh Infrastructure & Growth
**Start Date:** 2025-12-26
**Status:** In Progress

### Phase 1: Domain Migration ✅
- [x] Scan ports (80, 443 already served by nginx)
- [x] Create nginx config for hugginghugh.com
- [x] Obtain SSL certificate via Let's Encrypt
- [x] Configure www → non-www redirect
- [x] Configure HTTP → HTTPS redirect
- [x] Symlink web root to existing content
- [x] Verify security headers (HSTS, X-Frame-Options, etc.)

### Phase 2: SEO Optimization ✅
- [x] Add Open Graph meta tags to templates
- [x] Add Twitter Card meta tags to templates
- [x] Add JSON-LD structured data (WebSite, Organization schemas)
- [x] Create robots.txt
- [x] Create sitemap.xml generator
- [x] Update site_url to hugginghugh.com
- [x] Add explicit nginx location blocks for SEO files

### Phase 3: Content Marketing
- [ ] Create blog infrastructure
- [ ] Write initial security content posts

### Phase 4: Viral Mechanics
- [ ] Create embeddable trust score badges for model READMEs
- [ ] Add badge API endpoints

### Phase 5: Social Presence
- [ ] Build Twitter bot for score announcements

### Phase 6: Lead Capture
- [ ] Add email newsletter signup form

---

## Previous Sprint (Complete)

**Sprint:** HuggingHugh MVP
**Start Date:** 2024-12-10
**Status:** Complete

---

## Current Tasks

### High Priority

- [x] Initialize git repository ✅
- [x] Add .gitignore ✅
- [x] Create Python virtual environment ✅
- [x] Create requirements.txt with base dependencies ✅
- [x] Set up src/ directory structure ✅
- [x] Create tests/ directory ✅
- [x] Build HuggingFace model scanner ✅
- [x] Build SBOM generator with Syft ✅
- [x] Build vulnerability scanner with Grype ✅
- [x] Build license analyzer ✅
- [x] Build trust score calculator ✅
- [x] Build HTML report generator ✅
- [x] Build dashboard generator ✅
- [x] Create Nginx setup script ✅
- [x] Create cron job setup script ✅
- [x] Fix NoneType bug in license_analyzer.py ✅
- [x] Fix CycloneDX 1.5+ tools format bug ✅

### Medium Priority

- [x] Configure pytest ✅
- [x] Configure black/isort ✅
- [x] Configure bandit for security scanning ✅
- [x] Set up pre-commit hooks ✅
- [x] Run full production scan with 50 models ✅
- [x] Deploy to hugginghugh.etcbin.io ✅
- [x] Fix trust score summary text (was confusing users) ✅
- [x] Add tooltip explanations for trust factors ✅
- [x] Add deployment safeguards (--deploy flag, min model checks) ✅
- [x] Generate self-SBOM report at /sbom.html ✅
- [x] Add grade distribution cards (A/B/C/D/F) on dashboard ✅
- [x] Increase models from 50 to 100 ✅
- [x] Add Load More pagination (20 at a time) ✅
- [x] Create individual grade pages (/grade/a.html, etc.) ✅
- [x] Implement PostgreSQL leaderboard database ✅
- [x] Create leaderboard podium on front page ✅
- [x] Create full leaderboard page (/leaderboard.html) ✅

### Low Priority

- [ ] Add unit tests for scanner modules
- [ ] Add unit tests for generator modules
- [ ] Add unit tests for reporter modules
- [ ] Performance optimization for large scans

---

## Completed Tasks

| Task | Completed | Notes |
|------|-----------|-------|
| Create CLAUDE.md | 2024-12-10 | DevSecOps practices documented |
| Create ROADMAP.md | 2024-12-10 | Milestone tracking set up |
| Create TASKS.md | 2024-12-10 | Task checklist created |
| Initialize git repo | 2024-12-10 | Commit: 0782e19 |
| Add .gitignore | 2024-12-10 | Python/ML exclusions |
| HuggingHugh MVP implementation | 2024-12-10 | Commit: 1471d18 |
| Fix NoneType and CycloneDX bugs | 2024-12-10 | Commit: b7ef9c5 |

---

## Backlog

Tasks to be prioritized in future sprints:

- [ ] Add more ML framework dependencies detection
- [ ] Improve trust score algorithm
- [ ] Add model card quality analysis
- [ ] Add SBOM comparison over time
- [ ] Add email alerts for new vulnerabilities
- [ ] Containerization (Dockerfile)
- [ ] Kubernetes deployment manifests

---

## Blockers

| Blocker | Impact | Resolution |
|---------|--------|------------|
| None currently | - | - |

---

## Session Log

Track what was done in each development session:

### Session: 2024-12-10 (Morning)
- Created project structure
- Set up CLAUDE.md with DevSecOps requirements
- Created ROADMAP.md for milestone tracking
- Created TASKS.md for task tracking
- Initialized git repository (commit: 0782e19)
- Added comprehensive .gitignore
- Created docs/HUGGINGFACE_DEEP_DIVE.md - comprehensive HF ecosystem guide

### Session: 2024-12-10 (Afternoon)
- Built complete HuggingHugh MVP:
  - `src/scanner/`: hf_client.py, top_models.py, model_fetcher.py
  - `src/generator/`: sbom_generator.py, vuln_scanner.py, license_analyzer.py, trust_scorer.py
  - `src/reporter/`: html_generator.py, dashboard.py
  - `templates/`: base.html, dashboard.html, model_report.html, about.html
  - `static/css/style.css`: Vanilla CSS (no Tailwind per user request)
  - `scripts/`: run_daily_scan.py, setup_nginx.sh, setup_cron.sh, install.sh
- Commit: 1471d18

### Session: 2024-12-10 (Evening)
- Found and fixed two bugs during test scan:
  1. CycloneDX 1.5+ tools format (dict vs list) in sbom_generator.py
  2. NoneType error when license is None in license_analyzer.py
- Test scan with 3 models: 3/3 successful
- Commit: b7ef9c5

### Session: 2025-12-10
- Deployed to production at https://hugginghugh.etcbin.io
- SSL certificate from Let's Encrypt (expires March 10, 2026)
- Production scan with 50 top HuggingFace models
- Fixed trust score summary text - was saying "1 critical, 5 warnings" which confused users
  (these referred to trust FACTORS, not CVE vulnerabilities)
  - Changed to "X of 8 factors passed" for clarity
- Added tooltip explanations for all 8 trust factors:
  - Each factor now has a "?" icon with popup explaining the scoring formula
  - Tooltips show max points, criteria, and how the score is calculated
- Verified 16 unique trust scores across 50 models (36-78 range)
- Updated trust_scorer.py, html_generator.py, model_report.html, style.css
- Added deployment safeguards to run_daily_scan.py:
  - Requires explicit --deploy flag
  - Minimum 50 models check before deploying
  - Prevents accidental deployment of test scans
- Created self-SBOM generator (scripts/generate_self_sbom.py):
  - Generates SBOM of HuggingHugh project using Syft
  - Scans for vulnerabilities using Grype
  - Outputs HTML report at /sbom.html
  - Integrated into daily scan workflow

### Session: 2025-12-11 (Morning)
- Added grade distribution cards (A/B/C/D/F) on dashboard front page
- Increased models scanned from 50 to 100
- Added "Load More" pagination (20 models at a time) with vanilla JS
- Made grade cards clickable - link to individual grade pages
- Created grade pages (/grade/a.html, /grade/b.html, etc.) with same pagination
- Implemented PostgreSQL leaderboard system:
  - Created database `hugginghugh` with tables: score_history, current_rankings, hall_of_fame
  - Created src/database/leaderboard.py with LeaderboardDB class
  - Eligibility: 1M+ downloads minimum
  - Tie-breaker: 5-day grace period, then higher downloads wins
  - Streak tracking: days at current rank with same score
- Added leaderboard podium section on front page (top 3 models)
- Created full leaderboard page (/leaderboard.html):
  - Large podium display with gold/silver/bronze styling
  - Full rankings table with all 100 eligible models
  - Rank change indicators, streak badges, grade badges
  - Rules info card explaining eligibility and tie-breakers
- Added "Leaderboard" link to navigation
- CSS cache buster updated to v=5

### Session: 2025-12-11 (Afternoon/Evening)
- Fixed deployment permissions (sudo for www-data owned directories)
- Added global "Buy Me a Coffee" support card to base.html (appears on every page)
  - Vietnamese coffee reference: "cà phê sữa đá"
  - Removed redundant support cards from dashboard, model_report, about pages
- Added OSV-Scanner integration alongside Grype for vulnerability scanning
- Added timing tracking to daily scan script (Timer and TimingStats classes)
- Added Environment Checklist (minimum safe versions for common ML packages)
- Expanded ML framework dependency detection:
  - Added 40+ frameworks: JAX/Flax, TensorFlow, MLX, ONNX, vLLM, etc.
  - Added pipeline tag to dependencies mapping
  - Added architecture patterns to dependencies mapping
  - Added tag-based detection (GGUF, GPTQ, AWQ, quantization, etc.)
  - Added file extension based detection
  - Added quantization config parsing
- Improved trust score algorithm:
  - Recalibrated weights: security factors = 51% (safetensors 18%, no pickle 18%, CVEs 15%)
  - Expanded known trustworthy organizations list (50+ orgs)
  - Added GGUF and ONNX as safe serialization formats
  - Downloads as reputation proxy for unknown publishers
- Added methodology disclaimer to About page:
  - "How We Build These Reports" section
  - Explains dependency inference, vulnerability scanning, trust scores
  - Sets expectations: "starting point for security review, not replacement"
- Redesigned "Minimum Safe Versions" as "Environment Checklist":
  - Removed alarming severity badges
  - Cleaner card-based design
  - Better context: "model uses current versions, ensure YOUR environment meets minimums"
- Updated About page Trust Score Factors table with new weights
- CSS cache buster updated to v=7

### Session: 2025-12-13
- Updated Hero section with new messaging (B+D hybrid):
  - New headline: "The free security dashboard for AI models."
  - New subtext emphasizing: pickle file risks, free SBOM reports, open methodology, zero paywall
  - Added hero badges: "Security-First Scoring", "Free SBOM Reports", "Updated Daily"
- Expanded model scanning from 100 to 1,000 models:
  - Updated default --limit from 100 to 1000
  - Updated minimum deployment threshold from 100 to 500
  - Updated documentation and help text
- CSS cache buster updated to v=8
- Rationale: Position HuggingHugh as the free alternative to enterprise AI security tools
  - Emphasize what makes us different: security-first scoring, pickle file penalties
  - Scale to 1,000 models for credibility and coverage
  - Clear messaging: "enterprise tools charge thousands, we're free"

### Session: 2025-12-25
- Replaced all emoji icons with professional inline SVG icons:
  - Added SVG icon CSS framework to style.css
  - Updated base.html (logo shield, coffee cup buttons)
  - Updated dashboard.html (hero badges, leaderboard trophy, medals, streaks)
  - Updated leaderboard.html (trophy, medals, crown, streaks, rules icon)
  - Updated model_report.html (checkmarks, warnings, X marks, success icons)
- CSS cache buster updated to v=9
- Deployed with 501 models

### Session: 2025-12-26
- **Phase 1: Domain Migration - hugginghugh.com**
  - User acquired hugginghugh.com domain
  - Port scan: 80/443 served by nginx (available for new vhost)
  - Created nginx config: /etc/nginx/sites-available/hugginghugh.com
  - SSL certificate from Let's Encrypt (expires March 26, 2026)
  - Configured www → non-www redirect (301)
  - Configured HTTP → HTTPS redirect (301)
  - Symlinked /var/www/hugginghugh.com → /var/www/hugginghugh.etcbin.io
  - Security headers verified: HSTS, X-Frame-Options, X-Content-Type-Options, X-XSS-Protection, Referrer-Policy
  - **Site live at https://hugginghugh.com**

- **Phase 2: SEO Optimization**
  - Updated templates/base.html with comprehensive SEO meta tags:
    - Open Graph tags (og:type, og:url, og:title, og:description, og:image, og:site_name)
    - Twitter Card tags (twitter:card, twitter:url, twitter:title, twitter:description, twitter:image)
    - JSON-LD structured data (WebSite, Organization schemas)
    - Canonical URL tag
    - Favicon and apple-touch-icon support
  - Added site_url parameter to DashboardGenerator and HTMLReportGenerator
  - Created sitemap.xml generator with all pages + model reports
  - Created robots.txt generator with sitemap reference
  - Updated nginx config with explicit location blocks for /robots.txt and /sitemap.xml
  - Created static/images/favicon.svg (shield with checkmark)
  - CSS cache buster updated to v=10

---

## Code Changes Registry

Track significant code changes to maintain awareness:

| Date | File(s) | Change Description | Tests Added |
|------|---------|-------------------|-------------|
| 2024-12-10 | CLAUDE.md | Initial creation with DevSecOps practices | N/A |
| 2024-12-10 | ROADMAP.md | Initial creation with milestones | N/A |
| 2024-12-10 | TASKS.md | Initial creation with checklist | N/A |
| 2024-12-10 | .gitignore | Python/ML exclusions | N/A |
| 2024-12-10 | docs/HUGGINGFACE_DEEP_DIVE.md | Comprehensive HF ecosystem guide | N/A |
| 2024-12-10 | src/scanner/* | HuggingFace API client, model fetcher | No |
| 2024-12-10 | src/generator/* | SBOM generator, vuln scanner, license analyzer, trust scorer | No |
| 2024-12-10 | src/reporter/* | HTML report generator, dashboard generator | No |
| 2024-12-10 | templates/* | Jinja2 templates for reports | N/A |
| 2024-12-10 | static/css/style.css | Vanilla CSS styling | N/A |
| 2024-12-10 | scripts/* | Daily scan orchestrator, setup scripts | No |
| 2024-12-10 | src/generator/sbom_generator.py | Fix CycloneDX 1.5+ tools format handling | No |
| 2024-12-10 | src/generator/license_analyzer.py | Fix NoneType error on null license | No |
| 2025-12-10 | src/generator/trust_scorer.py | Added tooltip field, fixed summary text | No |
| 2025-12-10 | src/reporter/html_generator.py | Pass tooltip to template context | No |
| 2025-12-10 | templates/model_report.html | Added tooltip markup for trust factors | N/A |
| 2025-12-10 | static/css/style.css | Added tooltip CSS styling | N/A |

---

## DevSecOps Checklist (Per Commit)

Use this checklist before every commit:

```
Pre-Commit Checklist:
[ ] Code reviewed for security issues
[ ] bandit scan passed
[ ] safety check passed (Python deps)
[ ] All tests pass
[ ] Code formatted (black, isort)
[ ] No secrets in code
[ ] TASKS.md updated
[ ] ROADMAP.md updated (if milestone)
```
