# FIX_LOG.md

Bug fix log with root cause analysis. Format: `[date] - [severity] - [description]`

**Severity:** `critical` (service down), `high` (data loss/corruption), `medium` (degraded), `low` (cosmetic/minor)

---

## 2026-03-28 — Nightly Scan Reliability (7 fixes)

- `high` - **Self-SBOM generation failing daily since Mar 12.** `generate_self_sbom.py` called bare `syft`/`grype` commands — not found in cron's PATH. Fix: import `SYFT_PATH`/`GRYPE_PATH` from `config.settings`. Also added 300s subprocess timeout to prevent indefinite hangs.

- `high` - **Thread-unsafe shared DB connection.** `LeaderboardDB` used a single `psycopg2` connection across 4 worker threads. psycopg2 connections are not thread-safe — causes intermittent `InterfaceError`/`OperationalError`. Fix: replaced with `threading.local()` per-thread connections.

- `medium` - **DB connection dies during long scans.** The `connect()` method only checked `conn.closed` (explicit close), not server-side drops (idle timeout). Scans run ~25 minutes. Fix: added `SELECT 1` health check in `_get_conn()` with auto-reconnect on `OperationalError`/`InterfaceError`.

- `medium` - **News deploy hangs in cron.** `run_daily_news.py` used `sudo` without `-n` flag. When sudo credential cache expires, cron hangs waiting for password prompt. Same bug was fixed in `run_daily_scan.py` on Mar 12 but this script was missed. Fix: added `-n` flag to all sudo calls.

- `medium` - **No retry on model list fetch.** `hf_client.get_models()` fetches 1000 models in a single HTTP request with only 30s timeout and zero retry logic. Any transient failure kills the entire scan. Fix: added 3-retry loop with exponential backoff (2s, 4s, 8s).

- `medium` - **HTTP connection leak.** `ModelFetcher` was created at scan start but `close()` was never called. The internal `httpx.Client` leaked connections across all 500 model fetches. Fix: added `fetcher.close()` in the cleanup section of `run_daily_scan.py`.

- `medium` - **Parallel Grype DB downloads.** 4 worker threads each independently triggered Grype vulnerability DB downloads (~1.4GB each). Could exhaust disk mid-scan and cause lock contention. Fix: added a single `grype db update` call before worker threads start.

---

## 2026-03-12 — Nightly Scan Deploy Failure (silent for 10 days)

- `critical` - **Deploy failing since Mar 2.** `sudo` in cron prompted for password (no terminal). `last_run.json` wasn't saved on deploy failure, so monitoring showed stale data for 10 days. Fix: added `sudo -n` to all deploy commands, always save `last_run.json`.

- `medium` - **Disk waste accumulating.** Per-run log files, tokenizer.json downloads (30+ MB each), stale reports. Cleaned 1.7 GB. Fix: added `scripts/cleanup.py` for post-scan cleanup.

- `medium` - **Grype temp DB orphans.** Parallel workers left behind orphaned DB downloads consuming 10+ GB. Fix: added Grype temp cleanup to nightly process.

---

## 2025-12-30 — Cron PATH failure

- `critical` - **Cron job failing since Dec 26.** `syft`/`grype` not in cron's minimal PATH. Fix: added `_find_executable()` helper to `config/settings.py` that checks `~/.local/bin`, `/usr/local/bin`, `/usr/bin`.

---

## 2025-12-10 — Initial bugs

- `low` - **CycloneDX 1.5+ tools format.** SBOM generator produced invalid CycloneDX (dict vs list for tools field). Fix: updated `sbom_generator.py`.

- `low` - **NoneType on null license.** License analyzer crashed when model had no license. Fix: added None check in `license_analyzer.py`.
