# Terminal Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the AI-looking site with a full CRT terminal aesthetic - black background, phosphor green monospace text, ASCII-art components.

**Architecture:** CSS full rewrite + template HTML modifications. No Python/backend changes. All Jinja2 templates updated to remove SVG icons and add terminal-style markup. Chart.js re-themed.

**Tech Stack:** Vanilla CSS, Jinja2 templates, JetBrains Mono (Google Fonts), Chart.js

---

### Task 1: Write Complete Terminal CSS

**Files:**
- Rewrite: `static/css/style.css` (full replacement - 2304 lines becomes ~800 lines)

**Step 1: Write the new style.css**

Write the entire file as one cohesive terminal theme. All CSS from the design doc:
- Variables, reset, base, scanline overlay
- Header with prompt logo, bracket nav
- Hero as terminal output block
- Summary stats as bordered cells
- Model cards with border-only design
- Leaderboard as plain table (no podium, no medals)
- Grade distribution as bordered row
- Nutrition label with inverted header (no circles)
- Vuln table, SBOM components, license info
- Report page layout
- History/charts section
- Support section, footer
- Blog styles
- Badges page overrides
- Responsive breakpoints
- Global SVG icon hiding

Color tokens:
- --bg: #0a0a0a, --surface: #111111, --border: #1a3a1a
- --text: #00ff41, --text-body: #88cc88, --text-muted: #4a6a4a
- --warn: #ffb000, --crit: #ff3333, --highlight: #003300
- Font: JetBrains Mono via Google Fonts @import
- Glow: 0 0 5px rgba(0, 255, 65, 0.3)

Key rules:
- Zero gradients (except scanline overlay)
- Zero box-shadows (only glow text-shadow)
- Zero border-radius (all square)
- Zero translateY hover animations
- All .icon svg { display: none }
- body::after scanline repeating-linear-gradient

**Step 2: Verify no old patterns remain**

Run: `grep -c "linear-gradient\|box-shadow\|border-radius\|backdrop-filter\|translateY" static/css/style.css`
Expected: Only 1 result (the scanline gradient)

**Step 3: Commit**

```bash
git add static/css/style.css
git commit -m "style: complete terminal CSS rewrite - phosphor green on black"
```

---

### Task 2: Update base.html Template

**Files:**
- Modify: `templates/base.html`

**Step 1: Update head section**

Line 58 - Add Google Fonts preconnect and bump CSS version:
```html
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link rel="stylesheet" href="{{ base_url }}/static/css/style.css?v=13">
```

**Step 2: Replace logo (lines 73-76)**
```html
                <a href="{{ base_url }}/" class="logo">
                    <span class="logo-text">hugginghugh</span>
                </a>
```

**Step 3: Replace nav (lines 77-86)**
```html
                <nav class="main-nav">
                    <a href="{{ base_url }}/">dashboard</a>
                    <a href="{{ base_url }}/leaderboard.html">leaderboard</a>
                    <a href="{{ base_url }}/blog/">blog</a>
                    <a href="{{ base_url }}/badges.html">badges</a>
                    <a href="{{ base_url }}/about.html">about</a>
                    <a href="https://buymeacoffee.com/hugginghugh" target="_blank" class="btn btn-coffee">support</a>
                </nav>
```

**Step 4: Replace support card CTA (line 119-121)**
```html
                    <a href="https://buymeacoffee.com/hugginghugh" target="_blank" class="btn btn-support">
                        $ support --keep-running
                    </a>
```

**Step 5: Replace footer coffee button (lines 185-187)**
```html
                    <a href="https://buymeacoffee.com/hugginghugh" target="_blank" class="btn-coffee-small">
                        [support the project]
                    </a>
```

**Step 6: Commit**

```bash
git add templates/base.html
git commit -m "tmpl: terminal base - prompt logo, bracket nav, no SVGs"
```

---

### Task 3: Update dashboard.html Template

**Files:**
- Modify: `templates/dashboard.html`

**Step 1: Replace hero section (lines 7-19)**

Remove all SVG icons from hero badges:
```html
    <div class="hero-section">
        <h1 class="hero-headline">The free security dashboard for AI models.</h1>
        <p class="hero-subtext">
            We scan the top HuggingFace models daily. Trust scores that penalize pickle files.
            SBOM reports that enterprise tools charge thousands for. Open methodology. Zero paywall.
        </p>
        <div class="hero-badges">
            <span class="hero-badge">Security-First Scoring</span>
            <span class="hero-badge">Free SBOM Reports</span>
            <span class="hero-badge">Updated Daily</span>
        </div>
    </div>
```

**Step 2: Replace leaderboard title (line 45)**

Remove trophy SVG:
```html
            <h3 class="leaderboard-title">Leaderboard</h3>
```

**Step 3: Simplify podium entries (lines 50-64)**

Replace entire podium entry inside the for-loop:
```html
            <a href="{{ base_url }}/reports/{{ entry.safe_id }}/index.html" class="podium-entry podium-{{ entry.rank }}">
                <div class="podium-rank">#{{ entry.rank }}</div>
                <div class="podium-model">{{ entry.model_name }}</div>
                <div class="podium-score">{{ entry.trust_score }}/100</div>
                {% if entry.streak_days > 1 %}
                <div class="podium-meta"><span class="podium-streak">*{{ entry.streak_days }}d</span></div>
                {% endif %}
            </a>
```

**Step 4: Fix SafeTensors tag in model cards (line 133)**

Replace SVG checkmark:
```html
                    <span class="tag" style="color: var(--score-excellent); border-color: var(--score-excellent);">[safe] SafeTensors</span>
```

**Step 5: Commit**

```bash
git add templates/dashboard.html
git commit -m "tmpl: terminal dashboard - no SVGs, simple leaderboard list"
```

---

### Task 4: Update model_report.html Template

**Files:**
- Modify: `templates/model_report.html`

**Step 1: Replace all SVG icons with text equivalents**

Changes needed:
- Line 23: Verified badge -> `[verified]`
- Lines 47-51: SafeTensors checkmark -> `[safe] SafeTensors`
- Line 198: No vulns icon -> `[OK]` text
- Lines 209-212: Environment checklist icon -> just text header
- Lines 259-262: Commercial use icons -> `[PASS] Allowed` / `[FAIL] Not Allowed`
- Lines 383-386: Rank badge -> `[eligible]` text
- Lines 397-400: No-history icon -> remove (CSS handles it)

**Step 2: Commit**

```bash
git add templates/model_report.html
git commit -m "tmpl: terminal report - text status icons replace all SVGs"
```

---

### Task 5: Update leaderboard.html Template

**Files:**
- Modify: `templates/leaderboard.html`

**Step 1: Remove all SVG icons**

- Line 10: Remove trophy SVG from h1
- Line 73: Remove document SVG from rules h3
- Lines 127-131: Replace medal SVGs with text ranks (`*1`, `*2`, `*3` for top 3)
- Line 160: Replace fire SVG with text streak (`*{{ entry.streak_days }}d`)
- Lines 20-68: Podium section kept in HTML but hidden via CSS (.leaderboard-podium-large { display: none })

**Step 2: Commit**

```bash
git add templates/leaderboard.html
git commit -m "tmpl: terminal leaderboard - text ranks, hidden podium"
```

---

### Task 6: Update about.html, grade_page.html, blog_index.html Templates

**Files:**
- Modify: `templates/about.html`
- Modify: `templates/grade_page.html`
- Modify: `templates/blog_index.html`

**Step 1: about.html - Replace support CTA (lines 119-130)**

Remove gradient background, replace coffee emoji with terminal command:
```html
    <div class="card">
        <div class="card-body" style="text-align: center; padding: var(--space-2xl);">
            <h2 style="margin-bottom: var(--space-md);">Support This Project</h2>
            <p style="color: var(--text-muted); margin-bottom: var(--space-lg); max-width: 500px; margin-left: auto; margin-right: auto;">
                HuggingHugh is a free community resource. Running daily scans and hosting costs money.
            </p>
            <a href="https://buymeacoffee.com/hugginghugh" target="_blank" class="btn btn-support">
                $ support --donate
            </a>
        </div>
    </div>
```

**Step 2: grade_page.html - Fix SafeTensors tag (line 50)**
```html
                    <span class="tag" style="color: var(--score-excellent); border-color: var(--score-excellent);">[safe] SafeTensors</span>
```

**Step 3: blog_index.html - Remove book SVG from h1 (line 17)**
```html
        <h1>Blog</h1>
```

**Step 4: Commit**

```bash
git add templates/about.html templates/grade_page.html templates/blog_index.html
git commit -m "tmpl: terminal about, grade, blog pages - no SVGs or gradients"
```

---

### Task 7: Update charts.js for Terminal Theme

**Files:**
- Modify: `static/js/charts.js`

**Step 1: Replace COLORS palette (lines 8-23)**

```javascript
const COLORS = {
    primary: '#00ff41',
    primaryLight: 'rgba(0, 255, 65, 0.15)',
    success: '#00ff41',
    successLight: 'rgba(0, 255, 65, 0.15)',
    warning: '#ffb000',
    warningLight: 'rgba(255, 176, 0, 0.15)',
    danger: '#ff3333',
    dangerLight: 'rgba(255, 51, 51, 0.15)',
    medium: '#ff8800',
    mediumLight: 'rgba(255, 136, 0, 0.15)',
    text: '#88cc88',
    textMuted: '#4a6a4a',
    border: '#1a3a1a',
    background: '#111111',
};
```

**Step 2: Update tooltip and font styling in commonOptions (lines 37-48)**

```javascript
        tooltip: {
            backgroundColor: 'rgba(10, 10, 10, 0.95)',
            titleColor: '#00ff41',
            bodyColor: '#88cc88',
            borderColor: '#1a3a1a',
            borderWidth: 1,
            cornerRadius: 0,
            padding: 12,
            titleFont: { family: "'JetBrains Mono', monospace", weight: 'bold' },
            bodyFont: { family: "'JetBrains Mono', monospace" },
        },
```

**Step 3: Update tick fonts in scales**

Add `font: { family: "'JetBrains Mono', monospace", size: 10 }` to both x and y tick configs.

**Step 4: Update gradients and hover colors**

- initScoreChart gradient: `rgba(0, 255, 65, 0.2)` -> `rgba(0, 255, 65, 0)`
- initRankChart gradient: same
- All pointHoverBorderColor: `'#fff'` -> `'#0a0a0a'`

**Step 5: Commit**

```bash
git add static/js/charts.js
git commit -m "style: terminal chart theme - green on dark, monospace fonts"
```

---

### Task 8: Regenerate Site and Verify

**Step 1: Find and run the site generation command**

Check existing generation commands:
```bash
grep -r "html_generator\|generate" src/reporter/ --include="*.py" -l
```

Run the generator to rebuild output/ with new templates.

**Step 2: Spot-check generated HTML**

Verify:
- `output/index.html` has no SVG icons
- `output/leaderboard.html` has no podium/medal markup
- CSS version is v=13
- No old gradient/shadow styles in CSS

**Step 3: Commit generated output**

```bash
git add output/ static/ templates/
git commit -m "build: regenerate site with terminal redesign"
```

---

### Task 9: Update CHANGE_LOG.md

**Files:**
- Modify: `CHANGE_LOG.md`

**Step 1: Add changelog entry at top**

```markdown
## 2026-02-27

- `feat` - Complete site redesign: CRT terminal aesthetic with phosphor green (#00ff41) on black
- `style` - Full CSS rewrite: JetBrains Mono monospace, no gradients/shadows/animations
- `style` - All SVG icons replaced with ASCII text indicators ([PASS], [FAIL], [WARN])
- `style` - Nutrition label restyled as terminal panel with inverted header
- `style` - Leaderboard: removed podium/medals, plain ranked table
- `style` - Chart.js re-themed: green lines on dark background
- `style` - Header: prompt-style logo (hugginghugh>_) with bracket navigation
- `style` - CRT scanline overlay effect
```

**Step 2: Commit**

```bash
git add CHANGE_LOG.md
git commit -m "docs: add terminal redesign to changelog"
```
