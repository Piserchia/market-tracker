# CLAUDE.md — market-tracker

You are working in the market-tracker project. It is a multi-service Flask
application hosted at `market-tracker.chrispiserchia.com`.

## Before you act

1. Read `.context/CONTEXT.md` for architecture overview (3 dashboards, ports, APIs).
2. Read `.context/CHANGELOG.md` for recent changes.
3. This project has 3 independent Flask servers:
   - Mining (port 8787): `server.py`
   - Stocks (port 8788): `ai_sector/server.py`
   - Crypto (port 8789): `crypto/server.py`

## Before you finish

- Update `.context/CHANGELOG.md`.
- If you changed a server, restart it: `launchctl kickstart -k gui/$(id -u)/com.assistant.project.market-tracker[-stocks|-crypto]`
- Verify healthcheck: `curl http://localhost:<port>/health`
