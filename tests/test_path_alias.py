from __future__ import annotations

from pathlib import Path
import os

import pytest

from app.utils.path_alias import PathAlias


def test_alias_defaults_resolve_under_repo_root():
    # Ensure defaults map to known folders (do not assert existence to keep test portable)
    for path in PathAlias.list_aliases().values():
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


def test_samples_alias_and_shorthand(tmp_path: Path):
    PathAlias.set_override("samples://", tmp_path)
    assert PathAlias.resolve("samples://") == tmp_path.resolve()
    assert PathAlias.resolve("samples:path") == tmp_path.resolve()
    os.environ.pop("SPECTRA_SAMPLES", None)


def test_unknown_alias_raises():
    with pytest.raises(ValueError):
        PathAlias.resolve("storage://unknown")
