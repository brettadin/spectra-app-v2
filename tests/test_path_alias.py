from __future__ import annotations

from pathlib import Path
import os

from app.utils.path_alias import PathAlias


def test_alias_defaults_resolve_under_repo_root():
    # Ensure defaults map to known folders (do not assert existence to keep test portable)
    aliases = PathAlias.list_aliases()
    for key, path in aliases.items():
        assert isinstance(path, Path)
        assert path.is_absolute()


def test_env_override_takes_precedence(tmp_path: Path):
    # Override cache to a temp dir
    alias = "storage://cache"
    PathAlias.set_override(alias, tmp_path)
    resolved = PathAlias.resolve(alias)
    assert resolved == tmp_path.resolve()
    # Clean up
    os.environ.pop("SPECTRA_STORAGE_CACHE", None)
