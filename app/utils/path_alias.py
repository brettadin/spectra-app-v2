"""Path alias helper for logical storage locations.

Provides stable logical URIs like ``storage://cache`` that resolve to
concrete folders under the repository root by default, with optional
environment overrides. The helper keeps code and documentation resilient to
future storage reorganizations (e.g. moving ``downloads/`` to ``storage/cache``).

Supported aliases (defaults):
  - storage://cache     → <repo_root>/downloads
  - storage://exports   → <repo_root>/exports
  - storage://samples   → <repo_root>/samples
  - storage://docs      → <repo_root>/docs
  - storage://curated   → <repo_root>/storage/curated
  - samples://          → <repo_root>/samples (friendly shorthand)

Environment overrides (absolute paths):
  - SPECTRA_STORAGE_CACHE
  - SPECTRA_STORAGE_EXPORTS
  - SPECTRA_STORAGE_SAMPLES
  - SPECTRA_STORAGE_DOCS
  - SPECTRA_STORAGE_CURATED
  - SPECTRA_SAMPLES
"""

from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[2]


def _normalize_alias(alias: str) -> str:
    """Return the canonical alias key used in defaults/env maps."""

    # Allow ``samples:`` prefix variations for convenience during migration
    if alias.startswith("samples://") or alias.startswith("samples:///"):
        return "samples://"
    if alias.startswith("samples:"):
        return "samples://"
    return alias


_DEFAULTS: Mapping[str, Path] = {
    "storage://cache": _REPO_ROOT / "downloads",
    "storage://exports": _REPO_ROOT / "exports",
    "storage://samples": _REPO_ROOT / "samples",
    "storage://docs": _REPO_ROOT / "docs",
    "storage://curated": _REPO_ROOT / "storage" / "curated",
    "samples://": _REPO_ROOT / "samples",
}

_ENV_MAP: Mapping[str, str] = {
    "storage://cache": "SPECTRA_STORAGE_CACHE",
    "storage://exports": "SPECTRA_STORAGE_EXPORTS",
    "storage://samples": "SPECTRA_STORAGE_SAMPLES",
    "storage://docs": "SPECTRA_STORAGE_DOCS",
    "storage://curated": "SPECTRA_STORAGE_CURATED",
    "samples://": "SPECTRA_SAMPLES",
}


class PathAlias:
    """Resolve logical storage aliases to absolute paths."""

    @staticmethod
    def list_aliases() -> Dict[str, Path]:
        """Return a mapping of alias → resolved absolute Path.

        Resolution respects environment variable overrides. Returned paths are
        absolute (creation is not enforced here).
        """

        resolved: Dict[str, Path] = {}
        for alias, default in _DEFAULTS.items():
            key = _normalize_alias(alias)
            env_var = _ENV_MAP.get(key)
            override = os.environ.get(env_var, "") if env_var else ""
            path = Path(override).expanduser() if override else default
            resolved[alias] = path.resolve()
        return resolved

    @staticmethod
    def env_var_for(alias: str) -> str | None:
        """Return the environment variable name used for the alias, if any."""

        key = _normalize_alias(alias)
        return _ENV_MAP.get(key)

    @staticmethod
    def set_override(alias: str, path: Path | str) -> None:
        """Set an environment override for ``alias`` to ``path``.

        This only affects the current process and children. It does not persist
        to disk.
        """

        key = _normalize_alias(alias)
        env = _ENV_MAP.get(key)
        if not env:
            raise ValueError(f"Unknown alias: {alias}")
        os.environ[env] = str(Path(path).expanduser().resolve())

    @staticmethod
    def resolve(path_or_alias: Path | str) -> Path:
        """Resolve a storage alias or concrete path to an absolute Path.

        - If ``path_or_alias`` starts with ``storage://`` (or ``samples://``), map via
          defaults and environment overrides.
        - Otherwise, treat it as a filesystem path and return ``Path(...).resolve()``.
        """

        if isinstance(path_or_alias, Path):
            return path_or_alias.resolve()

        text = str(path_or_alias)
        if text.startswith("storage://") or text.startswith("samples://") or text.startswith("samples:"):
            key = _normalize_alias(text)
            if key not in _DEFAULTS:
                raise ValueError(f"Unknown alias: {text}")
            env_var = _ENV_MAP.get(key)
            override = os.environ.get(env_var, "") if env_var else ""
            if override:
                return Path(override).expanduser().resolve()
            return _DEFAULTS[key].resolve()

        return Path(text).expanduser().resolve()
