# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: Python (FastAPI) + server-rendered Jinja2 + htmx, no separate frontend build and no Node.js in the Docker image. Chosen during architectural brainstorming for consistency with the user's existing Python tooling, FastAPI's native SSE support (needed for real-time log streaming), and because a dashboard of buttons/tables doesn't need a SPA. Go was considered and rejected to keep the codebase easy for the (non-professional-frontend) author to read and modify.

## Users

Self-hosted homelab operators running [cross-seed](https://www.cross-seed.org/), a torrent cross-seeding daemon that has no UI of its own. Primary user is the author (also cross-seed's admin on their own NAS/Docker host); secondary audience is the r/selfhosted community the project will be published to, who will have varied but always Docker-based setups.

Job: administer cross-seed day-to-day — keep its indexer list in sync with Prowlarr, trigger its maintenance/search jobs, watch its logs, and see what it has actually cross-seeded — without needing to touch cross-seed's raw config file or terminal by hand.

## Product Purpose

Cross-Seed Companion (CSC) is a self-hosted web companion that gives cross-seed the operational UI it lacks: sync its indexer list from Prowlarr, run its API jobs, tail its logs, and list what it added. Success = the user never needs to SSH into the box or hand-edit `config.js` for these routine tasks.

## Positioning

Unlike a generic homelab dashboard widget or a hand-rolled shell script, CSC talks to cross-seed and Prowlarr exclusively through their documented HTTP APIs and a read/write bind mount — never SSH, never the Docker socket, never shell/subprocess execution of user-supplied config. That constraint is deliberate and load-bearing: CSC is openly built with AI assistance, and this is how it earns trust from a self-hosted/open-source audience that is skeptical of vibe-coded software, especially around security.

## Operating Context

Runs as a single Docker image, on the **same host** as cross-seed (v1 has no multi-host support). cross-seed's `/config` directory (`config.js`, `logs/`) is bind-mounted into the CSC container — read/write for `config.js`, read-only for `logs/`. Prowlarr is reached over HTTP + API key and does not need to be co-located. The user opens CSC in a browser (LAN or reverse-proxied) to run a sync, fire an action, watch logs, or check recent additions. Config changes to cross-seed are never auto-applied — CSC never restarts cross-seed itself; it shows a manual-restart reminder and, optionally, a link to the user's own Docker manager (Portainer, Dockge, etc.).

## Capabilities and Constraints

Four features, shippable as independent phases of one product:

1. Sync Prowlarr's enabled indexers into cross-seed's `torznab` config array (with options to exclude public trackers and/or a tagged subset), with a diff preview before any write, a timestamped backup, and a hard abort-without-writing if the config block can't be located unambiguously.
2. Trigger cross-seed's HTTP API actions (search, full search, notify by infoHash, cleanup/rss/updateIndexerCaps, health ping), extensible via a declarative (non-shell) YAML action schema for custom actions.
3. Real-time cross-seed log viewing (SSE), tailing rotating/symlinked daily log files.
4. A list of torrents cross-seed has actually added, parsed from its logs — explicitly without requiring a qBittorrent connection.

Hard constraints: no SSH, no Docker socket access, no shell/subprocess execution from user config, ever. Entirely configured via environment variables (see the project spec for the full table). CSC keeps no database of its own — everything is recomputed live from Prowlarr, `config.js`, and cross-seed's logs.

Explicitly out of scope for v1: qBittorrent integration, automatic restart of cross-seed, multi-host support.

## Brand Commitments

Name: **Cross-Seed Companion (CSC)**. Open source, MIT-licensed, published to r/selfhosted with the AI-assisted build process disclosed openly rather than hidden — the design and code should read as deliberately crafted, not as visible "AI slop," since that credibility is part of the product's positioning.

Visual reference the user volunteered as inspiration (not yet a binding direction, to be resolved in surface design): [getqui.com](https://getqui.com/) — cross-seed has no UI of its own, so there is no incumbent visual world to preserve.

## Evidence on Hand

No existing screenshots, mockups, or UI assets — this is a greenfield surface. Real cross-seed log samples exist (in the project spec) and inform Feature 3/4 content and density, but carry no visual evidence.

## Product Principles

1. Earn trust through precision, not decoration — this is a security-conscious, openly AI-built tool; the UI must look deliberately made, not templated or generic, without resorting to needless visual noise.
2. Operate, don't persuade — this is an admin tool the user returns to for tasks, not a marketing surface. Scanability and control density outrank flourish.
3. Respect consequential actions — config writes, forced actions with side effects — with clear diffs/previews and explicit confirmation; never a silent or reversible-looking action that isn't.
4. Fit a self-hosted dashboard aesthetic: dense, competent, comfortable in dark mode, at home next to tools like Portainer/Sonarr/Prowlarr — not a SaaS landing page.

## Accessibility & Inclusion

No project-specific requirement established beyond standard web accessibility (keyboard operability, sufficient contrast) — this is a single-operator admin tool, not a public-facing surface.
