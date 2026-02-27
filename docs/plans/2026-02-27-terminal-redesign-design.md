# HuggingHugh Terminal Redesign

## Problem
The current site looks AI-generated: gradient overload, frosted glass effects, hover animations on everything, oversized SVG icons, and Tailwind-palette saturation. It undermines credibility for a security tool.

## Solution
Full CRT terminal aesthetic. Black background, phosphor green monospace text, ASCII-art components. The site should look like you're SSH'd into a security scanning server.

## Color System

| Token | Hex | Role |
|-------|-----|------|
| `--bg` | `#0a0a0a` | Page background |
| `--surface` | `#111111` | Cards, panels |
| `--border` | `#1a3a1a` | Green-tinted borders |
| `--text` | `#00ff41` | Headlines, links, active |
| `--text-body` | `#88cc88` | Body text (dimmed green) |
| `--text-muted` | `#4a6a4a` | Labels, secondary |
| `--warn` | `#ffb000` | Medium severity, caution |
| `--crit` | `#ff3333` | Critical, errors |
| `--highlight` | `#003300` | Hover/selected background |

## Typography
100% monospace: `'JetBrains Mono', 'Fira Code', 'SF Mono', 'Cascadia Code', Consolas, monospace`

JetBrains Mono loaded from Google Fonts (400, 700 weights only).

## Component Redesigns

### Header
- Prompt-style logo: `hugginghugh>` with blinking cursor
- Nav links in brackets: `[dashboard]` `[leaderboard]` `[about]`
- No SVG icons
- Thin green bottom border

### Hero (replaced)
Terminal output block:
```
$ hugginghugh --status
[SYSTEM] Security scanner active
[SCAN]   500 models monitored | 5 vulns detected | avg score: 59
[UPTIME] Last scan: 2026-02-27 08:00 UTC
```

### Summary Stats
Inline terminal output, not cards. Green text, no boxes.

### Model Table
ASCII-style table with `|` separators and `---` dividers. Colored grade badges as `[A]` `[B]` etc.

### Grade Badges
Single character in brackets: `[A]` green, `[B]` lime, `[C]` amber, `[D]` orange, `[F]` red.

### Nutrition Label (ASCII art)
```
+======================================+
|        SECURITY NUTRITION LABEL      |
+======================================+
| Trust Score          [########..] 82 |
|--------------------------------------|
| Format                    SafeTensors|
| Has SBOM                          YES|
| Pickle Files                       0 |
| Known Vulns                        0 |
+--------------------------------------+
```

### Leaderboard
Plain ranked table. No podium, no medals. Top 3 get `*` marker. ASCII progress bars for scores.

### Footer
One line: `hugginghugh.com | open source | [github] [about] [contact]`

### Newsletter/Support
Terminal prompt style: `$ subscribe --email [input field]`

### Charts (Chart.js)
Re-themed: green lines, dark background, no fills. Grid lines in `--border` color.

## CRT Effects (subtle)
- Faint scanline overlay via repeating-linear-gradient (CSS only, no images)
- Green text-shadow glow: `0 0 5px rgba(0, 255, 65, 0.3)`
- Blinking cursor animation on hero prompt
- No heavy effects that hurt readability

## Removals
- All gradients
- All box shadows
- All hover translateY animations
- All frosted glass / backdrop-blur
- All SVG icons (replaced with ASCII text)
- Yellow support section
- Purple leaderboard background
- Medal/podium visualization
- All border-radius (square corners)

## Preserved
- Nutrition label concept (re-skinned as ASCII)
- Chart.js for history (re-themed)
- Responsive layout
- Jinja2 template structure
- All data models and generation logic
- SEO meta tags and structured data

## Files Affected

### CSS (full rewrite)
- `static/css/style.css`

### Templates (modify all)
- `templates/base.html` - header, footer, font loading
- `templates/dashboard.html` - hero, summary, model cards
- `templates/model_report.html` - nutrition label, vuln display
- `templates/leaderboard.html` - podium removal, table restyle
- `templates/grade_page.html` - grade card styling
- `templates/about.html` - content styling
- `templates/badges.html` - badge display

### JS (minor changes)
- `static/js/charts.js` - color theme update

### No changes to
- `src/` Python code (generation logic stays the same)
- Data models
- Output file structure
- API endpoints
