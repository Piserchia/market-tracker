# Changelog: market-tracker

<!-- Newest entries at top. -->

## 2026-04-17 — ai-server integration (Phase 3)

**Task**: Register market-tracker as a hosted project in the ai-server.

**Files changed**:
- `server.py` — Added `/health` endpoint returning `{"status":"ok","service":"mining"}`
- `ai_sector/server.py` — Added `/health` endpoint returning `{"status":"ok","service":"stocks"}`
- `crypto/server.py` — Added `/health` endpoint returning `{"status":"ok","service":"crypto"}`
- `manifest.yml` (new) — Hosting manifest for ai-server's `register-project.sh`
- `.context/CONTEXT.md` (new) — Project documentation following ai-server standard
- `.context/CHANGELOG.md` (new) — This file

**Why**: The ai-server needs health endpoints to monitor project liveness and
a manifest to generate Caddy routing and launchd supervision configs.

**Side effects**: None — `/health` is a new route that doesn't interfere with
existing functionality.
