# Contributing to Cross-Seed Companion

Thanks for your interest!

- Tests run with `pytest -v` (install `requirements-dev.txt`).
- Any behavior change needs a test.
- Open an issue before a significant feature change, to discuss the approach
  first.

## Releasing

Versions follow [semantic versioning](https://semver.org/): `PATCH` for bug
fixes, `MINOR` for backwards-compatible features, `MAJOR` for anything that can
break an existing deployment (renamed environment variable or action id, changed
YAML schema or mount path). While the major version is `0`, breaking changes
may ship in a minor release, and the release notes must say so.

```bash
git tag v0.2.0
git push --tags        # CI builds and publishes ghcr.io/exoenjoi/cross-seed-companion:0.2.0, :0.2 and :latest
gh release create v0.2.0 --title v0.2.0 \
  --notes "$(git log --pretty='- %s' "$(git describe --tags --abbrev=0 HEAD^)"..HEAD)"
```

The notes are the commit subjects since the previous tag: edit them if a change
needs a warning (e.g. a breaking change).

