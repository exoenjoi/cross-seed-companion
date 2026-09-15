# Cross-Seed Companion — Phase 1 : Socle + Synchronisation des indexers

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Livrer une image Docker fonctionnelle de Cross-Seed Companion avec le socle applicatif (FastAPI + htmx) et la fonctionnalité 1 complète : synchronisation des indexers Prowlarr → `config.js` de cross-seed, avec diff, confirmation, backup, et sans redémarrage automatique.

**Architecture:** Application Python/FastAPI monolithique, rendu serveur avec Jinja2 + htmx (pas de build frontend). Modules purs et testables (client Prowlarr, filtrage d'indexers, lecture/écriture de `config.js`) séparés des routes HTTP, pour permettre des tests unitaires sans dépendance réseau ni fichiers réels.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Jinja2, pydantic-settings, httpx, pytest. htmx (vendorisé, pas de CDN).

**Spec:** `docs/superpowers/specs/2026-09-15-cross-seed-companion-design.md`

## Global Constraints

- Une seule image Docker ; aucune dépendance runtime à Node.js.
- Pas de SSH, pas d'accès au socket Docker, pas d'exécution de commande shell depuis une config utilisateur.
- CSC et cross-seed tournent sur le même hôte Docker ; toute donnée cross-seed passe par bind mount, jamais par le réseau/SSH.
- `cross-seed.db` (SQLite interne de cross-seed) n'est jamais lu ni modifié — seuls `config.js` et `logs/` sont utilisés (logs hors scope de ce plan, phase ultérieure).
- Configuration exclusivement par variables d'environnement (voir table ci-dessous).
- Pas de redémarrage automatique de cross-seed après une sync — message manuel + lien `DOCKER_MANAGER_URL` optionnel.
- Licence MIT.

**Variables d'environnement (phase 1) :**

| Variable | Type | Défaut |
|---|---|---|
| `PROWLARR_URL` | str, requis | — |
| `PROWLARR_API_KEY` | str, requis | — |
| `CROSSSEED_URL` | str, requis | — |
| `CROSSSEED_API_KEY` | str, requis | — |
| `CROSSSEED_CONFIG_PATH` | path, requis | — |
| `SYNC_EXCLUDE_PUBLIC` | bool | `false` |
| `SYNC_EXCLUDE_TAG` | str \| None | `None` |
| `SYNC_INTERVAL_MINUTES` | int \| None | `None` (pas de sync auto) |
| `DOCKER_MANAGER_URL` | str \| None | `None` |

`CROSSSEED_URL`/`CROSSSEED_API_KEY` sont déjà lus par les settings dans cette phase (le module d'actions API qui les utilisera est une phase ultérieure) — inclus ici pour que le schéma de config soit stable dès le départ.

---

## File Structure

```
cross-seed-companion/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, lifespan, routes de santé, montage static/router
│   ├── config.py                # Settings (pydantic-settings)
│   ├── prowlarr.py              # ProwlarrClient, Indexer, Tag
│   ├── indexer_sync.py          # filtrage indexers, construction URLs torznab, diff
│   ├── crossseed_config.py      # localisation/remplacement du bloc torznab dans config.js
│   ├── sync_service.py          # orchestration: preview / apply
│   ├── scheduler.py             # boucle de sync périodique optionnelle
│   ├── routers/
│   │   ├── __init__.py
│   │   └── sync.py              # GET /sync, POST /sync/apply
│   ├── templates/
│   │   ├── base.html
│   │   ├── sync.html
│   │   ├── _sync_result.html
│   │   └── _error.html
│   └── static/
│       └── vendor/
│           └── htmx.min.js      # vendorisé, version pinnée
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   ├── test_config.py
│   ├── test_prowlarr.py
│   ├── test_indexer_sync.py
│   ├── test_crossseed_config.py
│   ├── test_sync_service.py
│   ├── test_sync_routes.py
│   └── test_scheduler.py
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
├── docker-compose.example.yml
├── .env.example
├── .gitignore
├── .dockerignore
├── LICENSE
├── README.md
└── CONTRIBUTING.md
```

---

### Task 1: Socle du projet et health check

**Files:**
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Create: `.gitignore`
- Create: `.dockerignore`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Test: `tests/__init__.py`
- Test: `tests/test_main.py`

**Interfaces:**
- Produces: module `app.main` exposant `app` (instance `fastapi.FastAPI`), route `GET /healthz` → `{"status": "ok"}`.

- [ ] **Step 1: Créer les fichiers de dépendances et les ignore-files**

`requirements.txt`:
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
jinja2==3.1.4
pydantic-settings==2.6.0
httpx==0.27.2
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest==8.3.3
```

`.gitignore`:
```
__pycache__/
*.pyc
.venv/
.env
```

`.dockerignore`:
```
.git
.venv
tests
docs
*.md
__pycache__
*.pyc
```

- [ ] **Step 2: Installer les dépendances**

Run: `python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt`

- [ ] **Step 3: Écrire le test qui échoue**

`tests/__init__.py` (vide).

`tests/test_main.py`:
```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_returns_ok():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 4: Lancer le test, vérifier qu'il échoue**

Run: `pytest tests/test_main.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app'` (ou `'app.main'`, `app/__init__.py` n'existe pas encore).

- [ ] **Step 5: Implémenter le minimum**

`app/__init__.py` (vide).

`app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Cross-Seed Companion")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Lancer le test, vérifier qu'il passe**

Run: `pytest tests/test_main.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add requirements.txt requirements-dev.txt .gitignore .dockerignore app/__init__.py app/main.py tests/__init__.py tests/test_main.py
git commit -m "feat: bootstrap FastAPI skeleton with health check"
```

---

### Task 2: Settings (variables d'environnement)

**Files:**
- Create: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: rien (module indépendant).
- Produces: `class Settings(BaseSettings)` avec les champs `prowlarr_url: str`, `prowlarr_api_key: str`, `crossseed_url: str`, `crossseed_api_key: str`, `crossseed_config_path: Path`, `sync_exclude_public: bool = False`, `sync_exclude_tag: str | None = None`, `sync_interval_minutes: int | None = None`, `docker_manager_url: str | None = None`. Fonction `get_settings() -> Settings` (cachée via `lru_cache`).

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_config.py`:
```python
from app.config import Settings


REQUIRED_ENV = {
    "PROWLARR_URL": "http://prowlarr:9696",
    "PROWLARR_API_KEY": "prowlarr-key",
    "CROSSSEED_URL": "http://cross-seed:2468",
    "CROSSSEED_API_KEY": "crossseed-key",
    "CROSSSEED_CONFIG_PATH": "/config",
}


def test_settings_reads_required_fields_from_env(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.prowlarr_url == "http://prowlarr:9696"
    assert settings.prowlarr_api_key == "prowlarr-key"
    assert settings.crossseed_url == "http://cross-seed:2468"
    assert settings.crossseed_api_key == "crossseed-key"
    assert str(settings.crossseed_config_path) == "/config"


def test_settings_optional_fields_default_to_none_or_false(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.sync_exclude_public is False
    assert settings.sync_exclude_tag is None
    assert settings.sync_interval_minutes is None
    assert settings.docker_manager_url is None


def test_settings_parses_optional_fields_from_env(monkeypatch):
    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("SYNC_EXCLUDE_PUBLIC", "true")
    monkeypatch.setenv("SYNC_EXCLUDE_TAG", "no-cross-seed")
    monkeypatch.setenv("SYNC_INTERVAL_MINUTES", "60")
    monkeypatch.setenv("DOCKER_MANAGER_URL", "https://portainer.example.com")

    settings = Settings(_env_file=None)

    assert settings.sync_exclude_public is True
    assert settings.sync_exclude_tag == "no-cross-seed"
    assert settings.sync_interval_minutes == 60
    assert settings.docker_manager_url == "https://portainer.example.com"
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.config'`

- [ ] **Step 3: Implémenter**

`app/config.py`:
```python
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    prowlarr_url: str
    prowlarr_api_key: str
    crossseed_url: str
    crossseed_api_key: str
    crossseed_config_path: Path
    sync_exclude_public: bool = False
    sync_exclude_tag: str | None = None
    sync_interval_minutes: int | None = None
    docker_manager_url: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: add environment-variable settings module"
```

---

### Task 3: Client Prowlarr

**Files:**
- Create: `app/prowlarr.py`
- Test: `tests/test_prowlarr.py`

**Interfaces:**
- Consumes: rien (module indépendant ; construit avec `base_url: str`, `api_key: str`).
- Produces: `@dataclass Indexer(id: int, name: str, enable: bool, privacy: str, tags: list[int])`, `@dataclass Tag(id: int, label: str)`, `class ProwlarrClient` avec `__init__(self, base_url: str, api_key: str, transport: httpx.BaseTransport | None = None)`, `.get_indexers(self) -> list[Indexer]`, `.get_tags(self) -> list[Tag]`, `.close(self) -> None`.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_prowlarr.py`:
```python
import httpx

from app.prowlarr import ProwlarrClient


INDEXERS_JSON = [
    {"id": 1, "name": "The Old School", "enable": True, "privacy": "private", "tags": []},
    {"id": 2, "name": "PublicTracker", "enable": True, "privacy": "public", "tags": []},
    {"id": 3, "name": "Disabled", "enable": False, "privacy": "private", "tags": []},
]

TAGS_JSON = [
    {"id": 10, "label": "no-cross-seed"},
    {"id": 11, "label": "anime"},
]


def _make_client(handler) -> ProwlarrClient:
    return ProwlarrClient(
        base_url="http://prowlarr:9696",
        api_key="test-key",
        transport=httpx.MockTransport(handler),
    )


def test_get_indexers_parses_response_and_sends_api_key_header():
    seen_requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_requests.append(request)
        assert request.url.path == "/api/v1/indexer"
        assert request.headers["X-Api-Key"] == "test-key"
        return httpx.Response(200, json=INDEXERS_JSON)

    client = _make_client(handler)
    indexers = client.get_indexers()

    assert len(seen_requests) == 1
    assert [i.id for i in indexers] == [1, 2, 3]
    assert indexers[0].privacy == "private"
    assert indexers[1].privacy == "public"
    assert indexers[2].enable is False


def test_get_tags_parses_response():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/tag"
        return httpx.Response(200, json=TAGS_JSON)

    client = _make_client(handler)
    tags = client.get_tags()

    assert [(t.id, t.label) for t in tags] == [(10, "no-cross-seed"), (11, "anime")]


def test_get_indexers_raises_on_http_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    client = _make_client(handler)
    try:
        client.get_indexers()
        assert False, "expected httpx.HTTPStatusError"
    except httpx.HTTPStatusError:
        pass
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_prowlarr.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.prowlarr'`

- [ ] **Step 3: Implémenter**

`app/prowlarr.py`:
```python
from dataclasses import dataclass

import httpx


@dataclass
class Indexer:
    id: int
    name: str
    enable: bool
    privacy: str
    tags: list[int]


@dataclass
class Tag:
    id: int
    label: str


class ProwlarrClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"X-Api-Key": api_key},
            transport=transport,
            timeout=15.0,
        )

    def get_indexers(self) -> list[Indexer]:
        response = self._client.get("/api/v1/indexer")
        response.raise_for_status()
        return [
            Indexer(
                id=item["id"],
                name=item["name"],
                enable=item["enable"],
                privacy=item["privacy"],
                tags=item.get("tags", []),
            )
            for item in response.json()
        ]

    def get_tags(self) -> list[Tag]:
        response = self._client.get("/api/v1/tag")
        response.raise_for_status()
        return [Tag(id=item["id"], label=item["label"]) for item in response.json()]

    def close(self) -> None:
        self._client.close()
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_prowlarr.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/prowlarr.py tests/test_prowlarr.py
git commit -m "feat: add Prowlarr API client"
```

---

### Task 4: Filtrage des indexers et construction des URLs torznab

**Files:**
- Create: `app/indexer_sync.py`
- Test: `tests/test_indexer_sync.py`

**Interfaces:**
- Consumes: `Indexer`, `Tag` de `app.prowlarr` (Task 3).
- Produces: `resolve_excluded_tag_id(tags: list[Tag], tag_name: str | None) -> int | None`, `filter_indexers(indexers: list[Indexer], exclude_public: bool, excluded_tag_id: int | None) -> list[Indexer]`, `build_torznab_urls(prowlarr_url: str, prowlarr_api_key: str, indexer_ids: list[int]) -> list[str]`, `compute_diff(old_urls: list[str], new_urls: list[str]) -> tuple[list[str], list[str]]` (retourne `(added, removed)`, chacun trié).

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_indexer_sync.py`:
```python
from app.indexer_sync import (
    build_torznab_urls,
    compute_diff,
    filter_indexers,
    resolve_excluded_tag_id,
)
from app.prowlarr import Indexer, Tag


def test_resolve_excluded_tag_id_finds_matching_label():
    tags = [Tag(id=10, label="no-cross-seed"), Tag(id=11, label="anime")]
    assert resolve_excluded_tag_id(tags, "no-cross-seed") == 10


def test_resolve_excluded_tag_id_returns_none_when_not_configured():
    tags = [Tag(id=10, label="no-cross-seed")]
    assert resolve_excluded_tag_id(tags, None) is None


def test_resolve_excluded_tag_id_returns_none_when_label_unknown():
    tags = [Tag(id=10, label="no-cross-seed")]
    assert resolve_excluded_tag_id(tags, "does-not-exist") is None


def test_filter_indexers_excludes_disabled_public_and_tagged():
    indexers = [
        Indexer(id=1, name="Private", enable=True, privacy="private", tags=[]),
        Indexer(id=2, name="Public", enable=True, privacy="public", tags=[]),
        Indexer(id=3, name="Disabled", enable=False, privacy="private", tags=[]),
        Indexer(id=4, name="Tagged", enable=True, privacy="private", tags=[10]),
    ]

    result = filter_indexers(indexers, exclude_public=True, excluded_tag_id=10)

    assert [i.id for i in result] == [1]


def test_filter_indexers_keeps_public_when_not_excluded():
    indexers = [Indexer(id=1, name="Public", enable=True, privacy="public", tags=[])]

    result = filter_indexers(indexers, exclude_public=False, excluded_tag_id=None)

    assert [i.id for i in result] == [1]


def test_build_torznab_urls_formats_official_crossseed_pattern():
    urls = build_torznab_urls("http://prowlarr:9696/", "prowlarr-key", [1, 6, 22])

    assert urls == [
        "http://prowlarr:9696/1/api?apikey=prowlarr-key",
        "http://prowlarr:9696/6/api?apikey=prowlarr-key",
        "http://prowlarr:9696/22/api?apikey=prowlarr-key",
    ]


def test_compute_diff_returns_added_and_removed():
    old = ["http://a/1/api?apikey=k", "http://a/2/api?apikey=k"]
    new = ["http://a/2/api?apikey=k", "http://a/3/api?apikey=k"]

    added, removed = compute_diff(old, new)

    assert added == ["http://a/3/api?apikey=k"]
    assert removed == ["http://a/1/api?apikey=k"]
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_indexer_sync.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.indexer_sync'`

- [ ] **Step 3: Implémenter**

`app/indexer_sync.py`:
```python
from app.prowlarr import Indexer, Tag


def resolve_excluded_tag_id(tags: list[Tag], tag_name: str | None) -> int | None:
    if tag_name is None:
        return None
    for tag in tags:
        if tag.label == tag_name:
            return tag.id
    return None


def filter_indexers(
    indexers: list[Indexer],
    exclude_public: bool,
    excluded_tag_id: int | None,
) -> list[Indexer]:
    result = []
    for indexer in indexers:
        if not indexer.enable:
            continue
        if exclude_public and indexer.privacy == "public":
            continue
        if excluded_tag_id is not None and excluded_tag_id in indexer.tags:
            continue
        result.append(indexer)
    return result


def build_torznab_urls(
    prowlarr_url: str,
    prowlarr_api_key: str,
    indexer_ids: list[int],
) -> list[str]:
    base = prowlarr_url.rstrip("/")
    return [f"{base}/{indexer_id}/api?apikey={prowlarr_api_key}" for indexer_id in indexer_ids]


def compute_diff(old_urls: list[str], new_urls: list[str]) -> tuple[list[str], list[str]]:
    old_set = set(old_urls)
    new_set = set(new_urls)
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    return added, removed
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_indexer_sync.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/indexer_sync.py tests/test_indexer_sync.py
git commit -m "feat: add indexer filtering and torznab URL generation"
```

---

### Task 5: Localisation et remplacement du bloc torznab dans config.js

**Files:**
- Create: `app/crossseed_config.py`
- Test: `tests/test_crossseed_config.py`

**Interfaces:**
- Consumes: rien (module indépendant, travaille sur du texte et des `pathlib.Path`).
- Produces: `class TorznabBlockError(Exception)`, `find_torznab_block(config_text: str) -> tuple[int, int]`, `extract_current_urls(config_text: str) -> list[str]`, `replace_torznab_block(config_text: str, urls: list[str]) -> str`, `read_config(path: Path) -> str`, `backup_config(path: Path) -> Path`, `write_config(path: Path, new_text: str) -> None`.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_crossseed_config.py`:
```python
import pytest

from app.crossseed_config import (
    TorznabBlockError,
    backup_config,
    extract_current_urls,
    find_torznab_block,
    read_config,
    replace_torznab_block,
    write_config,
)


FLAT_ARRAY_CONFIG = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old",
    "http://prowlarr:9696/2/api?apikey=old"
  ],
  delay: 30,
};
"""

MAP_STYLE_CONFIG = """module.exports = {
  torznab: [1, 2, 6].map(
    (id) => `http://prowlarr:9696/${id}/api?apikey=old`
  ),
  delay: 30,
};
"""


def test_find_torznab_block_locates_flat_array():
    start, end = find_torznab_block(FLAT_ARRAY_CONFIG)
    assert FLAT_ARRAY_CONFIG[start:end].strip().startswith("[")
    assert FLAT_ARRAY_CONFIG[start:end].strip().endswith("]")


def test_find_torznab_block_locates_map_style_including_call():
    start, end = find_torznab_block(MAP_STYLE_CONFIG)
    snippet = MAP_STYLE_CONFIG[start:end]
    assert snippet.strip().startswith("[1, 2, 6]")
    assert snippet.rstrip().endswith(")")


def test_find_torznab_block_raises_when_key_missing():
    with pytest.raises(TorznabBlockError):
        find_torznab_block("module.exports = { delay: 30 };")


def test_find_torznab_block_raises_when_key_appears_twice():
    text = "torznab: [],\ntorznab: []"
    with pytest.raises(TorznabBlockError):
        find_torznab_block(text)


def test_extract_current_urls_reads_flat_array():
    urls = extract_current_urls(FLAT_ARRAY_CONFIG)
    assert urls == [
        "http://prowlarr:9696/1/api?apikey=old",
        "http://prowlarr:9696/2/api?apikey=old",
    ]


def test_replace_torznab_block_normalizes_flat_array():
    result = replace_torznab_block(
        FLAT_ARRAY_CONFIG,
        ["http://prowlarr:9696/1/api?apikey=new"],
    )

    assert '"http://prowlarr:9696/1/api?apikey=new"' in result
    assert "old" not in result
    assert "delay: 30" in result  # le reste du fichier est préservé


def test_replace_torznab_block_normalizes_map_style():
    result = replace_torznab_block(
        MAP_STYLE_CONFIG,
        ["http://prowlarr:9696/1/api?apikey=new"],
    )

    assert '"http://prowlarr:9696/1/api?apikey=new"' in result
    assert ".map(" not in result
    assert "delay: 30" in result


def test_backup_config_creates_timestamped_copy(tmp_path):
    config_path = tmp_path / "config.js"
    config_path.write_text(FLAT_ARRAY_CONFIG)

    backup_path = backup_config(config_path)

    assert backup_path.exists()
    assert backup_path.name.startswith("config.js.bak.")
    assert backup_path.read_text() == FLAT_ARRAY_CONFIG


def test_read_and_write_config_roundtrip(tmp_path):
    config_path = tmp_path / "config.js"
    config_path.write_text(FLAT_ARRAY_CONFIG)

    text = read_config(config_path)
    write_config(config_path, text.replace("old", "new"))

    assert "new" in config_path.read_text()
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_crossseed_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.crossseed_config'`

- [ ] **Step 3: Implémenter**

`app/crossseed_config.py`:
```python
import re
from datetime import datetime
from pathlib import Path

_QUOTE_CHARS = "\"'`"
_TORZNAB_KEY_RE = re.compile(r"\btorznab\s*:\s*")
_MAP_CALL_RE = re.compile(r"\s*\.map\s*\(")


class TorznabBlockError(Exception):
    """Levée quand le bloc 'torznab:' de config.js ne peut pas être repéré sans ambiguïté."""


def _skip_string(text: str, pos: int) -> int:
    quote = text[pos]
    i = pos + 1
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == quote:
            return i + 1
        i += 1
    raise TorznabBlockError("Chaîne de caractères non terminée dans config.js.")


def _find_matching(text: str, open_pos: int, open_ch: str, close_ch: str) -> int:
    depth = 0
    i = open_pos
    while i < len(text):
        ch = text[i]
        if ch in _QUOTE_CHARS:
            i = _skip_string(text, i)
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise TorznabBlockError(f"'{open_ch}' non refermé dans config.js.")


def find_torznab_block(config_text: str) -> tuple[int, int]:
    matches = list(_TORZNAB_KEY_RE.finditer(config_text))
    if len(matches) != 1:
        raise TorznabBlockError(
            f"'torznab:' doit apparaître exactement une fois dans config.js "
            f"(trouvé {len(matches)} fois). Abandon sans rien écrire."
        )
    array_start = matches[0].end()
    if array_start >= len(config_text) or config_text[array_start] != "[":
        raise TorznabBlockError("'torznab:' doit être suivi d'un tableau '['.")

    array_end = _find_matching(config_text, array_start, "[", "]")
    end = array_end

    map_match = _MAP_CALL_RE.match(config_text, array_end)
    if map_match:
        call_open = map_match.end() - 1  # index du '(' d'ouverture
        end = _find_matching(config_text, call_open, "(", ")")

    return array_start, end


def extract_current_urls(config_text: str) -> list[str]:
    start, end = find_torznab_block(config_text)
    block = config_text[start:end]
    return re.findall(r'"([^"]*)"', block)


def replace_torznab_block(config_text: str, urls: list[str]) -> str:
    start, end = find_torznab_block(config_text)
    lines = "".join(f'    "{url}",\n' for url in urls)
    array_literal = f"[\n{lines}  ]"
    return config_text[:start] + array_literal + config_text[end:]


def read_config(path: Path) -> str:
    return path.read_text()


def backup_config(path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    backup_path = path.with_name(f"{path.name}.bak.{timestamp}")
    backup_path.write_text(path.read_text())
    return backup_path


def write_config(path: Path, new_text: str) -> None:
    path.write_text(new_text)
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_crossseed_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/crossseed_config.py tests/test_crossseed_config.py
git commit -m "feat: locate and rewrite the torznab block in cross-seed's config.js"
```

---

### Task 6: Orchestration de la synchronisation (preview / apply)

**Files:**
- Create: `app/sync_service.py`
- Test: `tests/test_sync_service.py`

**Interfaces:**
- Consumes: `ProwlarrClient`, `Indexer`, `Tag` (Task 3) ; `resolve_excluded_tag_id`, `filter_indexers`, `build_torznab_urls`, `compute_diff` (Task 4) ; `read_config`, `backup_config`, `write_config`, `extract_current_urls`, `replace_torznab_block` (Task 5) ; `Settings` (Task 2).
- Produces: `@dataclass SyncPreview(current_urls: list[str], new_urls: list[str], added: list[str], removed: list[str])`, `compute_sync_preview(prowlarr: ProwlarrClient, settings: Settings) -> SyncPreview`, `apply_sync(prowlarr: ProwlarrClient, settings: Settings) -> SyncPreview`.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_sync_service.py`:
```python
from dataclasses import dataclass, field

from app.config import Settings
from app.prowlarr import Indexer, Tag
from app.sync_service import apply_sync, compute_sync_preview


CONFIG_TEMPLATE = """module.exports = {{
  torznab: [
{urls}
  ],
  delay: 30,
}};
"""


class FakeProwlarr:
    def __init__(self, indexers: list[Indexer], tags: list[Tag]):
        self._indexers = indexers
        self._tags = tags

    def get_indexers(self) -> list[Indexer]:
        return self._indexers

    def get_tags(self) -> list[Tag]:
        return self._tags


def _settings(config_path, **overrides) -> Settings:
    values = {
        "PROWLARR_URL": "http://prowlarr:9696",
        "PROWLARR_API_KEY": "new-key",
        "CROSSSEED_URL": "http://cross-seed:2468",
        "CROSSSEED_API_KEY": "cs-key",
        "CROSSSEED_CONFIG_PATH": str(config_path.parent),
    }
    return Settings(_env_file=None, **{k.lower(): v for k, v in values.items()}, **overrides)


def _write_config(tmp_path, existing_ids):
    urls = "\n".join(
        f'    "http://prowlarr:9696/{i}/api?apikey=old",' for i in existing_ids
    )
    config_path = tmp_path / "config.js"
    config_path.write_text(CONFIG_TEMPLATE.format(urls=urls))
    return config_path


def test_compute_sync_preview_reports_added_and_removed(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[1, 2])
    prowlarr = FakeProwlarr(
        indexers=[
            Indexer(id=1, name="A", enable=True, privacy="private", tags=[]),
            Indexer(id=3, name="B", enable=True, privacy="private", tags=[]),
        ],
        tags=[],
    )
    settings = _settings(config_path)

    preview = compute_sync_preview(prowlarr, settings)

    assert preview.added == ["http://prowlarr:9696/3/api?apikey=new-key"]
    assert preview.removed == ["http://prowlarr:9696/2/api?apikey=old"]
    # config.js reste inchangé après un simple preview
    assert "old" in config_path.read_text()


def test_apply_sync_writes_backup_and_new_config(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[1, 2])
    prowlarr = FakeProwlarr(
        indexers=[Indexer(id=3, name="B", enable=True, privacy="private", tags=[])],
        tags=[],
    )
    settings = _settings(config_path)

    preview = apply_sync(prowlarr, settings)

    assert preview.new_urls == ["http://prowlarr:9696/3/api?apikey=new-key"]
    new_text = config_path.read_text()
    assert "http://prowlarr:9696/3/api?apikey=new-key" in new_text
    assert "old" not in new_text

    backups = list(tmp_path.glob("config.js.bak.*"))
    assert len(backups) == 1
    assert "old" in backups[0].read_text()


def test_apply_sync_excludes_public_and_tagged_indexers(tmp_path):
    config_path = _write_config(tmp_path, existing_ids=[])
    prowlarr = FakeProwlarr(
        indexers=[
            Indexer(id=1, name="Private", enable=True, privacy="private", tags=[]),
            Indexer(id=2, name="Public", enable=True, privacy="public", tags=[]),
            Indexer(id=3, name="Tagged", enable=True, privacy="private", tags=[10]),
        ],
        tags=[Tag(id=10, label="no-cross-seed")],
    )
    settings = _settings(
        config_path,
        sync_exclude_public=True,
        sync_exclude_tag="no-cross-seed",
    )

    preview = apply_sync(prowlarr, settings)

    assert preview.new_urls == ["http://prowlarr:9696/1/api?apikey=new-key"]
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_sync_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.sync_service'`

- [ ] **Step 3: Implémenter**

`app/sync_service.py`:
```python
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.crossseed_config import (
    backup_config,
    extract_current_urls,
    read_config,
    replace_torznab_block,
    write_config,
)
from app.indexer_sync import (
    build_torznab_urls,
    compute_diff,
    filter_indexers,
    resolve_excluded_tag_id,
)
from app.prowlarr import ProwlarrClient


@dataclass
class SyncPreview:
    current_urls: list[str]
    new_urls: list[str]
    added: list[str]
    removed: list[str]


def _config_path(settings: Settings) -> Path:
    return Path(settings.crossseed_config_path) / "config.js"


def _build_new_urls(prowlarr: ProwlarrClient, settings: Settings) -> list[str]:
    indexers = prowlarr.get_indexers()
    tags = prowlarr.get_tags()
    excluded_tag_id = resolve_excluded_tag_id(tags, settings.sync_exclude_tag)
    kept = filter_indexers(
        indexers,
        exclude_public=settings.sync_exclude_public,
        excluded_tag_id=excluded_tag_id,
    )
    return build_torznab_urls(
        settings.prowlarr_url,
        settings.prowlarr_api_key,
        [indexer.id for indexer in kept],
    )


def compute_sync_preview(prowlarr: ProwlarrClient, settings: Settings) -> SyncPreview:
    config_text = read_config(_config_path(settings))
    current_urls = extract_current_urls(config_text)
    new_urls = _build_new_urls(prowlarr, settings)
    added, removed = compute_diff(current_urls, new_urls)
    return SyncPreview(current_urls=current_urls, new_urls=new_urls, added=added, removed=removed)


def apply_sync(prowlarr: ProwlarrClient, settings: Settings) -> SyncPreview:
    config_path = _config_path(settings)
    config_text = read_config(config_path)
    current_urls = extract_current_urls(config_text)
    new_urls = _build_new_urls(prowlarr, settings)
    added, removed = compute_diff(current_urls, new_urls)

    backup_config(config_path)
    write_config(config_path, replace_torznab_block(config_text, new_urls))

    return SyncPreview(current_urls=current_urls, new_urls=new_urls, added=added, removed=removed)
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_sync_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/sync_service.py tests/test_sync_service.py
git commit -m "feat: orchestrate sync preview and apply against config.js"
```

---

### Task 7: Page web de synchronisation (routes + templates htmx)

**Files:**
- Create: `app/routers/__init__.py`
- Create: `app/routers/sync.py`
- Create: `app/templates/base.html`
- Create: `app/templates/sync.html`
- Create: `app/templates/_sync_result.html`
- Create: `app/templates/_error.html`
- Create: `app/static/vendor/htmx.min.js`
- Modify: `app/main.py`
- Test: `tests/test_sync_routes.py`

**Interfaces:**
- Consumes: `Settings` (Task 2), `ProwlarrClient` (Task 3), `SyncPreview`, `compute_sync_preview`, `apply_sync` (Task 6).
- Produces: `router: fastapi.APIRouter` dans `app.routers.sync` avec `GET /sync` et `POST /sync/apply` ; `app.main.app` monte ce router et sert `/static`.

- [ ] **Step 1: Récupérer htmx vendorisé**

Run: `curl -fsSL -o app/static/vendor/htmx.min.js https://unpkg.com/htmx.org@1.9.12/dist/htmx.min.js`

(Si l'environnement d'exécution n'a pas d'accès réseau sortant, télécharger ce fichier manuellement depuis un poste qui y a accès et le copier à cet emplacement — c'est un fichier statique versionné, pas une dépendance récupérée au build.)

- [ ] **Step 2: Écrire le test qui échoue**

`tests/test_sync_routes.py`:
```python
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.prowlarr import Indexer, Tag
from app.routers import sync as sync_router


CONFIG_TEXT = """module.exports = {
  torznab: [
    "http://prowlarr:9696/1/api?apikey=old"
  ],
  delay: 30,
};
"""


class FakeProwlarr:
    def __init__(self, indexers, tags):
        self._indexers = indexers
        self._tags = tags

    def get_indexers(self):
        return self._indexers

    def get_tags(self):
        return self._tags


def _client(tmp_path, indexers, tags=None) -> TestClient:
    config_path = tmp_path / "config.js"
    config_path.write_text(CONFIG_TEXT)

    app = FastAPI()
    app.include_router(sync_router.router)
    app.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="new-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path=str(tmp_path),
    )
    app.state.prowlarr_client = FakeProwlarr(indexers, tags or [])
    return TestClient(app)


def test_get_sync_shows_diff_preview(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="B", enable=True, privacy="private", tags=[])],
    )

    response = client.get("/sync")

    assert response.status_code == 200
    assert "http://prowlarr:9696/2/api?apikey=new-key" in response.text
    assert "Confirmer et appliquer" in response.text


def test_post_sync_apply_writes_config_and_confirms(tmp_path):
    client = _client(
        tmp_path,
        indexers=[Indexer(id=2, name="B", enable=True, privacy="private", tags=[])],
    )

    response = client.post("/sync/apply")

    assert response.status_code == 200
    assert "appliquée" in response.text
    assert (tmp_path / "config.js").read_text().count("http://prowlarr:9696/2/api?apikey=new-key") == 1


def test_get_sync_shows_error_when_torznab_block_missing(tmp_path):
    (tmp_path / "config.js").write_text("module.exports = { delay: 30 };")
    client = FastAPI()
    client.include_router(sync_router.router)
    client.state.settings = Settings(
        _env_file=None,
        prowlarr_url="http://prowlarr:9696",
        prowlarr_api_key="new-key",
        crossseed_url="http://cross-seed:2468",
        crossseed_api_key="cs-key",
        crossseed_config_path=str(tmp_path),
    )
    client.state.prowlarr_client = FakeProwlarr(indexers=[], tags=[])

    response = TestClient(client).get("/sync")

    assert response.status_code == 200
    assert "Erreur" in response.text
```

- [ ] **Step 3: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_sync_routes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.routers'`

- [ ] **Step 4: Implémenter les templates**

Direction visuelle : voir le contrat de direction dans
`.impeccable/surfaces/app-templates-base-html.md` (console d'opérateur sombre,
accent ambre unique, données en monospace, hairlines plutôt que des cards à
ombre — inspiré de getqui.com, choisi avec l'utilisateur). Tout template ou
CSS ajouté dans les tâches futures (Features 2-4) doit suivre ce même
contrat plutôt que réinventer un style.

`app/templates/base.html`:
```html
<!doctype html>
<html lang="fr" data-theme="dark">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <title>Cross-Seed Companion</title>
  <script src="/static/vendor/htmx.min.js"></script>
  <style>
    :root {
      --bg: #0b0c0e;
      --bg-raised: #14161a;
      --fg: #e8e6e1;
      --fg-dim: #83807a;
      --accent: #f5a623;
      --accent-dim: #7a5518;
      --danger: #e5484d;
      --border: #23262b;
      --mono: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace;
      --sans: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--fg);
      font-family: var(--sans);
      font-size: 14px;
      line-height: 1.5;
    }
    header.topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.9rem 1.5rem;
      border-bottom: 1px solid var(--border);
    }
    header.topbar .brand {
      font-size: 0.8rem;
      font-weight: 600;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    main {
      max-width: 860px;
      margin: 0 auto;
      padding: 2rem 1.5rem 4rem;
    }
    .section-tag {
      display: inline-block;
      font-family: var(--mono);
      font-size: 0.72rem;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 0.6rem;
    }
    h1.page-title {
      font-size: 1.3rem;
      font-weight: 600;
      margin: 0 0 1.75rem;
    }
    table.diff {
      width: 100%;
      border-collapse: collapse;
      font-family: var(--mono);
      font-size: 0.82rem;
    }
    table.diff td {
      padding: 0.45rem 0.6rem;
      border-bottom: 1px solid var(--border);
      word-break: break-all;
    }
    td.added { color: var(--accent); }
    td.removed { color: var(--fg-dim); text-decoration: line-through; }
    .meta {
      color: var(--fg-dim);
      font-family: var(--mono);
      font-size: 0.78rem;
      margin-bottom: 1.25rem;
    }
    .actions { margin-top: 1.5rem; }
    button, .btn {
      font-family: var(--sans);
      font-size: 0.82rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      background: transparent;
      color: var(--accent);
      border: 1px solid var(--accent-dim);
      padding: 0.55rem 1.1rem;
      cursor: pointer;
      border-radius: 3px;
    }
    button:hover, .btn:hover {
      background: var(--accent);
      color: #14100a;
      border-color: var(--accent);
    }
    .notice {
      border: 1px solid var(--border);
      background: var(--bg-raised);
      padding: 0.9rem 1rem;
      font-size: 0.85rem;
    }
    .notice a { color: var(--accent); }
    .error-box {
      border: 1px solid var(--danger);
      color: var(--danger);
      padding: 0.9rem 1rem;
      font-family: var(--mono);
      font-size: 0.82rem;
    }
    .error-tag {
      display: block;
      font-size: 0.7rem;
      letter-spacing: 0.15em;
      margin-bottom: 0.4rem;
    }
  </style>
</head>
<body>
  <header class="topbar">
    <span class="brand">Cross-Seed Companion</span>
  </header>
  <main>
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

`app/templates/sync.html`:
```html
{% extends "base.html" %}
{% block content %}
<span class="section-tag">01 · Sync</span>
<h1 class="page-title">Indexers Prowlarr → cross-seed</h1>
<div id="sync-result">
  {% include "_sync_result.html" %}
</div>
{% endblock %}
```

`app/templates/_sync_result.html`:
```html
<p class="meta">
  {{ preview.current_urls | length }} indexer(s) actuellement — {{ preview.new_urls | length }} après synchronisation
</p>
{% if preview.added or preview.removed %}
<table class="diff">
  {% for url in preview.added %}<tr><td class="added">+ {{ url }}</td></tr>{% endfor %}
  {% for url in preview.removed %}<tr><td class="removed">- {{ url }}</td></tr>{% endfor %}
</table>
{% endif %}
{% if not preview.added and not preview.removed %}
  <p class="notice">Déjà synchronisé, rien à faire.</p>
{% elif applied %}
  <p class="notice">
    Synchronisation appliquée. Redémarre cross-seed pour appliquer les changements.
    {% if settings.docker_manager_url %}
      <br><a href="{{ settings.docker_manager_url }}" target="_blank" rel="noopener">Ouvrir le gestionnaire Docker →</a>
    {% endif %}
  </p>
{% else %}
  <div class="actions">
    <form hx-post="/sync/apply" hx-target="#sync-result" hx-confirm="Confirmer la synchronisation ?">
      <button type="submit">Confirmer et appliquer</button>
    </form>
  </div>
{% endif %}
```

`app/templates/_error.html`:
```html
<div class="error-box">
  <span class="error-tag">Erreur</span>
  {{ message }}
</div>
```

- [ ] **Step 5: Implémenter les routes**

`app/routers/__init__.py` (vide).

`app/routers/sync.py`:
```python
from pathlib import Path

import httpx
from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from app.crossseed_config import TorznabBlockError
from app.sync_service import apply_sync, compute_sync_preview

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/sync")
def sync_page(request: Request):
    settings = request.app.state.settings
    prowlarr = request.app.state.prowlarr_client
    try:
        preview = compute_sync_preview(prowlarr, settings)
    except (TorznabBlockError, OSError, httpx.HTTPError) as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    return templates.TemplateResponse(
        request, "sync.html", {"preview": preview, "applied": False, "settings": settings}
    )


@router.post("/sync/apply")
def sync_apply(request: Request):
    settings = request.app.state.settings
    prowlarr = request.app.state.prowlarr_client
    try:
        preview = apply_sync(prowlarr, settings)
    except (TorznabBlockError, OSError, httpx.HTTPError) as exc:
        return templates.TemplateResponse(request, "_error.html", {"message": str(exc)})
    return templates.TemplateResponse(
        request, "_sync_result.html", {"preview": preview, "applied": True, "settings": settings}
    )
```

- [ ] **Step 6: Monter le router et les fichiers statiques dans l'app**

Modifier `app/main.py` :
```python
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.prowlarr import ProwlarrClient
from app.routers import sync as sync_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.prowlarr_client = ProwlarrClient(settings.prowlarr_url, settings.prowlarr_api_key)
    yield
    app.state.prowlarr_client.close()


app = FastAPI(title="Cross-Seed Companion", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)
app.include_router(sync_router.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_sync_routes.py -v`
Expected: PASS

- [ ] **Step 8: Lancer toute la suite de tests**

Run: `pytest -v`
Expected: PASS (tous les tests des tâches 1 à 7)

- [ ] **Step 9: Commit**

```bash
git add app/routers app/templates app/static app/main.py tests/test_sync_routes.py
git commit -m "feat: add sync web page with htmx diff preview and apply flow"
```

---

### Task 8: Image Docker, exemples de config, licence et documentation

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.example.yml`
- Create: `.env.example`
- Create: `LICENSE`
- Create: `README.md`
- Create: `CONTRIBUTING.md`

**Interfaces:**
- Consumes: `app/main.py` (Task 7), `requirements.txt` (Task 1).
- Produces: image Docker buildable exposant le port `8000`.

- [ ] **Step 1: Écrire le Dockerfile**

`Dockerfile`:
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

RUN useradd --create-home --shell /bin/false csc
USER csc

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Construire l'image et vérifier qu'elle démarre**

Run: `docker build -t cross-seed-companion:test .`
Expected: build réussi.

Run:
```bash
docker run -d --name csc-smoke-test \
  -p 8000:8000 \
  -e PROWLARR_URL=http://localhost:9696 \
  -e PROWLARR_API_KEY=dummy \
  -e CROSSSEED_URL=http://localhost:2468 \
  -e CROSSSEED_API_KEY=dummy \
  -e CROSSSEED_CONFIG_PATH=/config \
  -v /tmp:/config \
  cross-seed-companion:test
sleep 2
curl -fsS http://localhost:8000/healthz
docker rm -f csc-smoke-test
```
Expected: `{"status":"ok"}`

- [ ] **Step 3: Écrire les fichiers d'exemple de configuration**

`.env.example`:
```
PROWLARR_URL=http://prowlarr:9696
PROWLARR_API_KEY=changeme
CROSSSEED_URL=http://cross-seed:2468
CROSSSEED_API_KEY=changeme
CROSSSEED_CONFIG_PATH=/crossseed-config
SYNC_EXCLUDE_PUBLIC=true
SYNC_EXCLUDE_TAG=no-cross-seed
SYNC_INTERVAL_MINUTES=60
DOCKER_MANAGER_URL=https://portainer.example.com
```

`docker-compose.example.yml`:
```yaml
services:
  cross-seed-companion:
    image: cross-seed-companion:latest
    build: .
    ports:
      - "8000:8000"
    environment:
      PROWLARR_URL: "http://prowlarr:9696"
      PROWLARR_API_KEY: "changeme"
      CROSSSEED_URL: "http://cross-seed:2468"
      CROSSSEED_API_KEY: "changeme"
      CROSSSEED_CONFIG_PATH: "/crossseed-config"
      SYNC_EXCLUDE_PUBLIC: "true"
      SYNC_EXCLUDE_TAG: "no-cross-seed"
      SYNC_INTERVAL_MINUTES: "60"
      DOCKER_MANAGER_URL: "https://portainer.example.com"
    volumes:
      - /path/to/cross-seed/config:/crossseed-config
```

- [ ] **Step 4: Ajouter la licence MIT**

`LICENSE`:
```
MIT License

Copyright (c) 2026 Cross-Seed Companion contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 5: Écrire le README**

`README.md`:
```markdown
# Cross-Seed Companion (CSC)

Compagnon web self-hosted pour [cross-seed](https://www.cross-seed.org/).

> Ce projet est développé avec l'assistance d'IA ("vibe codé"), assumé
> ouvertement. Par prudence, il évite volontairement tout mécanisme
> sensible : pas de SSH, pas d'accès au socket Docker, pas d'exécution de
> commande shell depuis la configuration.

## Fonctionnalités (phase 1)

- Synchronisation des indexers activés dans Prowlarr vers le bloc `torznab`
  de `config.js` de cross-seed, avec aperçu du diff, confirmation, et
  sauvegarde automatique avant toute écriture.

## Prérequis de déploiement

CSC doit tourner **sur le même hôte Docker que cross-seed**, avec le
répertoire de configuration de cross-seed monté en bind mount (lecture et
écriture) dans le container CSC.

## Installation

1. Copier `.env.example` vers `.env` et renseigner les valeurs.
2. Copier `docker-compose.example.yml` vers `docker-compose.yml`, ajuster le
   chemin du volume vers le répertoire de config de cross-seed.
3. `docker compose up -d`
4. Ouvrir `http://<host>:8000/sync`.

## Variables d'environnement

| Variable | Requis | Rôle |
|---|---|---|
| `PROWLARR_URL` | oui | URL de base de Prowlarr |
| `PROWLARR_API_KEY` | oui | Clé API Prowlarr |
| `CROSSSEED_URL` | oui | URL de base du daemon cross-seed |
| `CROSSSEED_API_KEY` | oui | Clé API cross-seed |
| `CROSSSEED_CONFIG_PATH` | oui | Chemin (bind mount) vers le répertoire de config cross-seed |
| `SYNC_EXCLUDE_PUBLIC` | non | Exclut les indexers publics de la sync (défaut : `false`) |
| `SYNC_EXCLUDE_TAG` | non | Nom d'un tag Prowlarr à exclure de la sync |
| `SYNC_INTERVAL_MINUTES` | non | Active une sync automatique périodique |
| `DOCKER_MANAGER_URL` | non | Lien affiché après une sync vers votre outil de gestion Docker |

## Important

Après une synchronisation, cross-seed doit être **redémarré manuellement**
pour prendre en compte la nouvelle configuration (CSC ne redémarre jamais de
container automatiquement).

## Licence

MIT — voir [`LICENSE`](./LICENSE).
```

- [ ] **Step 6: Écrire CONTRIBUTING.md**

`CONTRIBUTING.md`:
```markdown
# Contribuer à Cross-Seed Companion

Merci de votre intérêt !

- Les tests s'exécutent avec `pytest -v` (installer `requirements-dev.txt`).
- Toute modification de comportement doit être accompagnée d'un test.
- Ouvrez une issue avant un changement de fonctionnalité important, pour
  discuter de l'approche.
```

- [ ] **Step 7: Commit**

```bash
git add Dockerfile docker-compose.example.yml .env.example LICENSE README.md CONTRIBUTING.md
git commit -m "docs: add Docker packaging, deployment examples, MIT license and README"
```

---

### Task 9: Synchronisation périodique optionnelle

**Files:**
- Create: `app/scheduler.py`
- Test: `tests/test_scheduler.py`
- Modify: `app/main.py`

**Interfaces:**
- Consumes: `apply_sync` (Task 6), `Settings.sync_interval_minutes` (Task 2).
- Produces: `async def periodic_sync_loop(interval_seconds: float, run_once: Callable[[], None], stop_event: asyncio.Event) -> None`.

- [ ] **Step 1: Écrire le test qui échoue**

`tests/test_scheduler.py`:
```python
import asyncio

from app.scheduler import periodic_sync_loop


def test_periodic_sync_loop_calls_run_once_repeatedly_until_stopped():
    call_count = 0

    def run_once() -> None:
        nonlocal call_count
        call_count += 1

    async def scenario() -> int:
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            periodic_sync_loop(interval_seconds=0.01, run_once=run_once, stop_event=stop_event)
        )
        await asyncio.sleep(0.05)
        stop_event.set()
        await task
        return call_count

    result = asyncio.run(scenario())

    assert result >= 2


def test_periodic_sync_loop_survives_run_once_raising():
    call_count = 0

    def run_once() -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    async def scenario() -> int:
        stop_event = asyncio.Event()
        task = asyncio.create_task(
            periodic_sync_loop(interval_seconds=0.01, run_once=run_once, stop_event=stop_event)
        )
        await asyncio.sleep(0.05)
        stop_event.set()
        await task
        return call_count

    result = asyncio.run(scenario())

    assert result >= 2
```

- [ ] **Step 2: Lancer les tests, vérifier qu'ils échouent**

Run: `pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.scheduler'`

- [ ] **Step 3: Implémenter**

`app/scheduler.py`:
```python
import asyncio
import logging
from typing import Callable

logger = logging.getLogger(__name__)


async def periodic_sync_loop(
    interval_seconds: float,
    run_once: Callable[[], None],
    stop_event: asyncio.Event,
) -> None:
    while not stop_event.is_set():
        try:
            run_once()
        except Exception:
            logger.exception("La synchronisation périodique a échoué")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
```

- [ ] **Step 4: Lancer les tests, vérifier qu'ils passent**

Run: `pytest tests/test_scheduler.py -v`
Expected: PASS

- [ ] **Step 5: Brancher la boucle dans le cycle de vie de l'application**

Modifier `app/main.py` :
```python
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.prowlarr import ProwlarrClient
from app.routers import sync as sync_router
from app.scheduler import periodic_sync_loop
from app.sync_service import apply_sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    app.state.prowlarr_client = ProwlarrClient(settings.prowlarr_url, settings.prowlarr_api_key)

    stop_event = asyncio.Event()
    scheduler_task: asyncio.Task | None = None
    if settings.sync_interval_minutes:
        def run_once() -> None:
            apply_sync(app.state.prowlarr_client, settings)

        scheduler_task = asyncio.create_task(
            periodic_sync_loop(
                interval_seconds=settings.sync_interval_minutes * 60,
                run_once=run_once,
                stop_event=stop_event,
            )
        )

    yield

    stop_event.set()
    if scheduler_task is not None:
        await scheduler_task
    app.state.prowlarr_client.close()


app = FastAPI(title="Cross-Seed Companion", lifespan=lifespan)
app.mount(
    "/static",
    StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
    name="static",
)
app.include_router(sync_router.router)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Lancer toute la suite de tests**

Run: `pytest -v`
Expected: PASS (tous les tests, tâches 1 à 9)

- [ ] **Step 7: Commit**

```bash
git add app/scheduler.py app/main.py tests/test_scheduler.py
git commit -m "feat: add optional periodic auto-sync loop"
```

---

## Après ce plan

Les fonctionnalités 2 (actions API déclaratives), 3 (logs temps réel) et 4
(torrents ajoutés) seront chacune l'objet d'un plan séparé, écrit une fois
ce socle en place et testé sur un déploiement réel — la spec
(`docs/superpowers/specs/2026-09-15-cross-seed-companion-design.md`) reste
la référence pour leur contenu fonctionnel.
