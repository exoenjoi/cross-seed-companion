---
version: 1
slug: "app-templates-base-html"
primary_target: "app/templates/base.html"
related_targets: ["app/templates/sync.html"]
---

## Direction contract

THESIS: This is an operator console for a background daemon, not a dashboard pretending to be a SaaS product. It owns "terminal for a service you trust and occasionally intervene on," and refuses the generic Bootstrap-card/pastel-icon-tile look most self-hosted admin UIs default to.

OWN-WORLD: Dark-first, near-black ground (~#0b0c0e), a single sparing accent (amber/signal, in the register of torrent-tooling UIs like qui) reserved for primary actions and live status, never decoration. Monospace for anything that is data — hashes, log lines, URLs, diffs; a plain system sans for UI labels, nav, and prose. Structure via 1px hairlines, not card shadows/elevation. Section labels are tracked uppercase tags (`01 SYNC`, `02 ACTIONS`, `03 LOGS`, `04 ADDED`), not icon tiles.

STORY: The operator opens CSC to answer one of: "is cross-seed healthy," "sync my indexers and let me see the diff before it touches config.js," "fire this job," "watch what's happening right now," "what did it actually add." Every screen answers exactly one of these; nothing is decorative.

FIRST VIEWPORT: Slim top bar — product name, left; live health badge (from `/api/ping`), right. Below it, a tab rail across the four features. Default view (Sync): a diff table (torznab entries added in one color, removed in another, monospace URLs) above two distinct buttons — "Preview" (safe, just recomputes the diff) and "Apply" (the write, requires confirmation) — never merged into one action.

FORM: User-pinned reference — getqui.com (a dark, technical, self-hosted torrent-client console: near-black ground, amber accent, numbered feature blocks, monospace data, moderate density, "serious tool for a serious library" register). Adopted directly rather than run through `concept-seed`'s dice roll: no image generation is available in this harness/session, and a user-pinned reference already fixes the direction — the skill's own rule is that a pinned direction beats the roll. Build path: code-led (no image generation available); ambition is carried in this contract's FIRST VIEWPORT block and audited at the finish review rather than against a generated comp.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
