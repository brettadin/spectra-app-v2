"""Path alias helper for logical storage locations.

Provides stable logical URIs like ``storage://cache`` that resolve to
concrete folders under the repository root by default, with environment
variable overrides.

Aliases (defaults):
  - storage://cache   → <repo_root>/downloads
  - storage://exports → <repo_root>/exports
  - storage://samples → <repo_root>/samples
  - storage://docs    → <repo_root>/docs

Environment overrides (absolute paths):
  - SPECTRA_STORAGE_CACHE
  - SPECTRA_STORAGE_EXPORTS
  - SPECTRA_STORAGE_SAMPLES
  - SPECTRA_STORAGE_DOCS
"""

from __future__ import annotations

from pathlib import Path
import os
from typing import Dict, Mapping


_REPO_ROOT = Path(__file__).resolve().parents[2]

_DEFAULTS: Mapping[str, Path] = {
    "storage://cache": _REPO_ROOT / "downloads",
    "storage://exports": _REPO_ROOT / "exports",
    "storage://samples": _REPO_ROOT / "samples",
    "storage://docs": _REPO_ROOT / "docs",
}

_ENV_MAP: Mapping[str, str] = {
    "storage://cache": "SPECTRA_STORAGE_CACHE",
    "storage://exports": "SPECTRA_STORAGE_EXPORTS",
    "storage://samples": "SPECTRA_STORAGE_SAMPLES",
    "storage://docs": "SPECTRA_STORAGE_DOCS",
}


class PathAlias:
    """Resolve logical storage aliases to absolute paths.

    All methods are static for simple use: PathAlias.resolve("storage://cache").
    """

    @staticmethod
    def list_aliases() -> Dict[str, Path]:
        """Return a mapping of alias → resolved absolute Path.

        Resolution respects environment variable overrides. Returned paths are
        absolute (creation is not enforced here).
        """
        resolved: Dict[str, Path] = {}
        for alias, default in _DEFAULTS.items():
            env = _ENV_MAP.get(alias)
            override = os.environ.get(env, "") if env else ""
            path = Path(override).expanduser() if override else default
            resolved[alias] = path.resolve()
        return resolved

    @staticmethod
    def env_var_for(alias: str) -> str | None:
        """Return the environment variable name used for the alias, if any."""
        return _ENV_MAP.get(alias)

    @staticmethod
    def set_override(alias: str, path: Path | str) -> None:
        """Set an environment override for ``alias`` to ``path``.

        This only affects the current process and children. It does not persist
        to disk.
        """
        env = PathAlias.env_var_for(alias)
        if not env:
            raise ValueError(f"Unknown alias: {alias}")
        os.environ[env] = str(Path(path).resolve())

    @staticmethod
    def resolve(path_or_alias: Path | str) -> Path:
        """Resolve a storage alias or concrete path to an absolute Path.

        - If ``path_or_alias`` is a string starting with ``storage://``, map via
          defaults and environment overrides.
        - Otherwise, treat as a filesystem path and resolve to absolute.
        """
        if isinstance(path_or_alias, Path):
            return path_or_alias.resolve()
        s = str(path_or_alias)
        if s.startswith("storage://"):
            aliases = PathAlias.list_aliases()
            if s not in aliases:
                raise ValueError(f"Unknown alias: {s}")
            return aliases[s]
        return Path(s).expanduser().resolve()
"""Path alias resolution helper (Cleanup branch).

Purpose:
- Provide a single place to resolve logical storage aliases to physical paths during and after migration.
- Keep code and docs resilient to folder moves (downloads/ → storage/cache, exports/ → storage/exports).

Aliases (docs/specs/path_aliases.md):
- storage://cache → storage/cache/ (compat: downloads/)
- storage://exports → storage/exports/ (compat: exports/)
- storage://curated → storage/curated/
- samples:// → samples/

Environment overrides:
- SPECTRA_STORAGE_CACHE, SPECTRA_STORAGE_EXPORTS, SPECTRA_STORAGE_CURATED, SPECTRA_SAMPLES

Notes:
- Resolution is relative to the repo root by default (parent of this file's parent).
- Keep this helper backward-compatible until Phase 4 removes legacy roots.
"""
# from __future__ import annotations  # (disabled in mid-file; future imports must be at top)

from pathlib import Path
# import os  # duplicate import (already imported above)
from typing import Dict


class _PathAliasLegacy:
    ROOT = Path(__file__).resolve().parents[2]  # repo root

    ENV_VARS = {
        "storage://cache": "SPECTRA_STORAGE_CACHE",
        "storage://exports": "SPECTRA_STORAGE_EXPORTS",
        "storage://curated": "SPECTRA_STORAGE_CURATED",
        "samples://": "SPECTRA_SAMPLES",
    }

    DEFAULTS = {
        # Backward-compatible defaults during migration
        "storage://cache": Path("downloads"),
        "storage://exports": Path("exports"),
        "storage://curated": Path("storage") / "curated",
        "samples://": Path("samples"),
    }

    @classmethod
    def resolve(cls, alias: str) -> Path:
        """Resolve an alias to an absolute Path under the repo root or overridden via env.

        Raises:
            KeyError: if alias is unknown.
        """
        # Normalize alias keys (ensure trailing // for samples)
        key = alias
        if key.startswith("samples:"):
            key = "samples://"
        if key not in cls.DEFAULTS:
            raise KeyError(f"Unknown alias: {alias}")

        # Env override
        env_var = cls.ENV_VARS.get(key)
        if env_var and os.getenv(env_var):
            return Path(os.getenv(env_var, "")).resolve()

        # Default physical location (relative to repo root)
        return (cls.ROOT / cls.DEFAULTS[key]).resolve()

    @classmethod
    def list_aliases(cls) -> Dict[str, Path]:
        return {k: cls.resolve(k) for k in cls.DEFAULTS.keys()}

    @classmethod
    def set_override(cls, alias: str, path: Path) -> None:
        env = cls.ENV_VARS.get(alias)
        if not env:
            raise KeyError(f"Unknown alias: {alias}")
        os.environ[env] = str(Path(path).resolve())
