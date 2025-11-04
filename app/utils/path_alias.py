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
from __future__ import annotations

from pathlib import Path
import os
from typing import Dict


class PathAlias:
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
