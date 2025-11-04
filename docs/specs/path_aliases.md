# Path Aliases and Modular Storage — Specification (Cleanup Branch, Nov 4, 2025)

This spec defines logical path aliases used in code and docs so the repository can migrate storage locations without breaking
imports, exports, or links. Aliases decouple documentation and feature plans from concrete directories and keep the cleanup modular.

---

## Goals
- Decouple code/docs from concrete folders that will move (`downloads/`, `exports/`, heavy `samples/`).
- Provide a single registry for resolving logical locations at runtime.
- Offer stable prose handles for docs and PRs, with acceptance checks.

## Aliases (canonical)
- storage://cache — transient and cached content-addressed blobs
  - Backed by: `storage/cache/` (post-migration). Pre-migration compatibility: `downloads/`.
  - Subpaths:
    - `storage://cache/_incoming` — provider temp area
    - `storage://cache/files` — content-addressed payloads (index maps metadata)
    - `storage://cache/_cache/line_lists` — NIST ASD line-list cache
- storage://exports — exported manifests, CSVs, plots, logs
  - Backed by: `storage/exports/` (post-migration). Pre-migration compatibility: `exports/`.
  - Typical subpaths: `sources/`, `spectra/`, `logs/`.
- storage://curated — large curated demo/regression datasets
  - Backed by: `storage/curated/` (post-migration). Source of truth for heavy sample trees formerly under `samples/`.
- samples:// — tiny quick-start sample files packaged in-repo
  - Backed by: `samples/` (post-migration slimmed). Max a few MB total.
- repo://docs — documentation root
  - Backed by: `docs/` (unchanged). Used in link-checking and index generation.

## Runtime resolution (code contract)
- LocalStore.base_path MUST default to resolve(storage://cache) and create subfolders on demand.
- Export centers MUST resolve(storage://exports) for default destinations; UI should reflect this path.
- Tests and fixtures SHOULD use samples:// unless the test explicitly targets curated data.
- Providers and caches MUST NOT hardcode `downloads/` or `exports/`.

Suggested interface (Python):

- PathAlias.resolve(alias: str) -> pathlib.Path
- PathAlias.set_override(alias: str, path: Path) -> None (for tests)
- PathAlias.list_aliases() -> dict[str, Path] (diagnostics)

## Docs usage
- Prefer alias notation in prose, diagrams, and plans, e.g., “write manifests to storage://exports/spectra”.
- When linking to files in-repo, use the current physical path but add a parenthetical alias for clarity during cleanup.

## Acceptance criteria
- No in-repo docs or code refer directly to `downloads/` or `exports/` for post-migration behavior.
- CI link checker finds zero broken links after moving the trees.
- A grep for `downloads/` or `exports/` in code shows only redirect stubs/archives, not live references.

## Migration sequencing
1) Land this spec and add a minimal `PathAlias` helper in code (backward-compatible to current paths).
2) Flip LocalStore and export centers to use the alias helper; update tests.
3) Move folders; add README redirects in old roots.
4) After soak, remove old roots and purge compatibility code.

## Examples
- NIST cache write: storage://cache/_cache/line_lists/hydrogen_1_400-700.json
- Export manifest: storage://exports/sources/2025-11-04-....txt
- Demo dataset pointer: storage://curated/solar_system/mercury/...

## Notes
- On Windows, paths are resolved with `pathlib.Path` and kept relative to repo root by default. Support overrides via environment
  variables for CI (e.g., `SPECTRA_STORAGE_CACHE=` to point at an ephemeral workspace).
- Keep alias names short, lowercase, and stable.
