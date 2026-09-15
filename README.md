# Cross-Seed Companion (CSC)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-single%20image-2496ED?logo=docker&logoColor=white)](./Dockerfile)
[![Built with Claude](https://img.shields.io/badge/Built%20with-Claude-D97757?logo=claude&logoColor=white)](https://claude.com/claude-code)

A self-hosted web companion for [cross-seed](https://www.cross-seed.org/) — the tool has no UI of its own; CSC gives it one.

> **This project is openly AI-assisted ("vibe coded"), and that's disclosed on purpose.**
> The self-hosted/open-source community is right to be skeptical of AI-generated
> software, especially around security — so the design deliberately avoids anything
> with a large attack surface: **no SSH, no Docker socket access, no shell/subprocess
> execution from user config**, anywhere in the codebase. See [Security](#security)
> and [Architecture](#architecture) below.

## Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quickstart](#quickstart)
- [Configuration](#configuration)
- [Security](#security)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

## Features

**Phase 1, 2 & 3 (shipped):**

- **Indexer sync** — pulls your enabled indexers from Prowlarr and writes them into
  cross-seed's `torznab` config block, with a diff preview, explicit confirmation,
  and a timestamped backup before any write. Optionally exclude public trackers
  and/or indexers carrying a specific Prowlarr tag.
- **Declarative actions** — trigger cross-seed's job API (search, full search,
  cleanup, RSS, indexer-cap refresh, notify by infoHash) from a `/actions` page,
  plus a live cross-seed health badge. Extensible via an optional custom YAML
  file (`ACTIONS_CONFIG_PATH`, see
  [`examples/custom-actions.example.yml`](./examples/custom-actions.example.yml))
  using the same schema as the built-in actions — no code changes, and no
  `subprocess`/shell involved: every action is a plain HTTP call with
  whitelist-only variable substitution.
- **Real-time logs** — a `/logs` page streams cross-seed's `verbose.current.log`
  live over Server-Sent Events, with a short backfill on load and a client-side
  text filter. v1 shows only the current day's log (no browsing older rotated
  files yet — see Roadmap).

**Planned (not yet built — see [Roadmap](#roadmap)):** a list of recently
cross-seeded torrents.

## Architecture

CSC is a single Python (FastAPI + htmx) Docker image, server-rendered, no
build step, no Node.js in the image. It's designed to run on the **same
Docker host as cross-seed**, reading and writing cross-seed's config through a
bind mount — never over SSH, never through the Docker socket:

- cross-seed's `config.js` is mounted read-write (needed for the sync feature).
- cross-seed's `logs/` directory will be mounted read-only for a future phase.
- cross-seed's internal SQLite database (`cross-seed.db`) is never touched —
  its schema isn't a stable public contract, unlike the logs and config file.

CSC never restarts cross-seed itself (there's no reliable, sensitive-mechanism-free
way to do that). After a sync, it shows a manual-restart reminder and, if you set
`DOCKER_MANAGER_URL`, a direct link to your own Docker management UI (Portainer,
Dockge, etc.).

## Quickstart

```bash
git clone https://github.com/exoenjoi/cross-seed-companion.git
cd cross-seed-companion

cp .env.example .env            # fill in your Prowlarr/cross-seed values
cp docker-compose.example.yml docker-compose.yml
# edit docker-compose.yml: point the volume at your real cross-seed config dir

docker compose up -d --build
```

Then open `http://<host>:8000/sync` — review the diff, confirm, restart cross-seed.

## Configuration

Everything is configured through environment variables.

| Variable | Required | Purpose |
|---|---|---|
| `PROWLARR_URL` | yes | Prowlarr's base URL |
| `PROWLARR_API_KEY` | yes | Prowlarr API key |
| `CROSSSEED_URL` | yes | cross-seed daemon's base URL (used by Phase 2 declarative actions) |
| `CROSSSEED_API_KEY` | yes | cross-seed API key (used by Phase 2 declarative actions) |
| `CROSSSEED_CONFIG_PATH` | yes | Path (bind mount) to cross-seed's config directory |
| `SYNC_EXCLUDE_PUBLIC` | no | Exclude public-tracker indexers from the sync (default: `false`) |
| `SYNC_EXCLUDE_TAG` | no | Name of a Prowlarr tag; indexers carrying it are excluded from the sync |
| `SYNC_INTERVAL_MINUTES` | no | **Not implemented yet** — reserved for a future phase, currently has no effect |
| `DOCKER_MANAGER_URL` | no | Link shown after a sync to your Docker management tool |
| `ACTIONS_CONFIG_PATH` | no | Path to an optional custom actions YAML file (see `examples/custom-actions.example.yml`) |
| `CROSSSEED_LOGS_PATH` | no | Path to cross-seed's `logs/` directory, if mounted separately (defaults to `CROSSSEED_CONFIG_PATH/logs`) |

## Security

CSC has **no authentication and no CSRF protection built in**. `POST
/sync/apply` rewrites a real file on disk, and the diff view displays your
Prowlarr API key in plain text. **Never expose this port directly to the
internet** — put it behind your own reverse proxy's authentication, or
restrict it to a private network/VPN.

CSC's own hard design constraints (not just this feature's, the whole
project's): no SSH, no Docker socket access, no shell/subprocess execution
driven by user-supplied configuration.

## Roadmap

Phases 1 (indexer sync), 2 (declarative actions) and 3 (real-time logs) are
done. One more phase is planned:

4. A list of torrents cross-seed has actually cross-seeded, parsed from its
   logs, without requiring a qBittorrent connection.

Browsing older, already-rotated log files (beyond the current day shown by
Phase 3) is a plausible future addition — the log parser was deliberately
kept independent of the live-tailing code so it could be reused for that
without a rewrite.

## Contributing

- Tests run with `pytest -v` (install `requirements-dev.txt`).
- Any behavior change needs a test.
- Open an issue before a significant feature change, to discuss the approach
  first — see [`CONTRIBUTING.md`](./CONTRIBUTING.md).

This project's specs, implementation plans, and design-process artifacts were
produced with [Claude Code](https://claude.com/claude-code) and intentionally
kept out of version control (`.gitignore`) — they're development scaffolding,
not part of the shipped app.

## License

MIT — see [`LICENSE`](./LICENSE).
