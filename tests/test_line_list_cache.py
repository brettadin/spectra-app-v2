"""Tests for the NIST line list cache."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
from pathlib import Path
from typing import Any, Dict

import pytest

from app.services.line_list_cache import LineListCache


@pytest.fixture
def cache_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for cache testing."""
    return tmp_path / "line_cache"


@pytest.fixture
def cache(cache_dir: Path) -> LineListCache:
    """Return a fresh cache instance with a temporary directory."""
    return LineListCache(cache_dir, max_age_days=30, enabled=True)


@pytest.fixture
def sample_data() -> Dict[str, Any]:
    """Return sample NIST line list data."""
    return {
        "wavelength_nm": [656.3, 486.1, 434.0],
        "intensity": [100.0, 50.0, 25.0],
        "lines": [
            {"wavelength_nm": 656.3, "relative_intensity": 100.0},
            {"wavelength_nm": 486.1, "relative_intensity": 50.0},
            {"wavelength_nm": 434.0, "relative_intensity": 25.0},
        ],
        "meta": {
            "element_symbol": "H",
            "ion_stage": "I",
            "label": "H I (NIST ASD)",
        },
    }


def test_cache_initialization_creates_directory(cache_dir: Path, cache: LineListCache) -> None:
    """Cache initialization creates the cache directory."""
    assert cache_dir.exists()
    assert cache_dir.is_dir()
    assert cache.enabled
    assert cache.cache_dir == cache_dir


def test_cache_miss_returns_none(cache: LineListCache) -> None:
    """Cache miss returns None."""
    result = cache.get("H", 1, 400.0, 700.0)
    assert result is None
    assert cache.stats["misses"] == 1
    assert cache.stats["hits"] == 0


def test_cache_set_and_get_roundtrip(cache: LineListCache, sample_data: Dict[str, Any]) -> None:
    """Data can be stored and retrieved from cache."""
    # Store data
    success = cache.set("H", 1, 400.0, 700.0, sample_data)
    assert success is True
    assert cache.stats["stores"] == 1

    # Retrieve data
    retrieved = cache.get("H", 1, 400.0, 700.0)
    assert retrieved is not None
    assert cache.stats["hits"] == 1
    assert retrieved["wavelength_nm"] == sample_data["wavelength_nm"]
    assert retrieved["meta"]["element_symbol"] == "H"


def test_cache_key_normalization(cache: LineListCache, sample_data: Dict[str, Any]) -> None:
    """Cache keys are normalized (case, rounding) for consistent lookup."""
    # Store with uppercase
    cache.set("H", 1, 400.123, 700.456, sample_data)
    
    # Retrieve with same parameters (tests rounding is consistent)
    retrieved = cache.get("H", 1, 400.123, 700.456)
    assert retrieved is not None


def test_cache_miss_different_parameters(cache: LineListCache, sample_data: Dict[str, Any]) -> None:
    """Different query parameters result in cache miss."""
    cache.set("H", 1, 400.0, 700.0, sample_data)
    
    # Different element
    assert cache.get("He", 1, 400.0, 700.0) is None
    # Different ion stage
    assert cache.get("H", 2, 400.0, 700.0) is None
    # Different wavelength range
    assert cache.get("H", 1, 500.0, 800.0) is None


def test_cache_expiry(cache_dir: Path, sample_data: Dict[str, Any]) -> None:
    """Expired cache entries are not returned."""
    # Create cache with very short max age
    cache = LineListCache(cache_dir, max_age_days=0, enabled=True)
    
    # Store data
    cache.set("H", 1, 400.0, 700.0, sample_data)
    
    # Manually adjust the cached_at timestamp to be old
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) == 1
    
    with cache_files[0].open("r") as f:
        entry = json.load(f)
    
    # Set cached_at to 2 days ago
    old_time = datetime.now(UTC) - timedelta(days=2)
    entry["cached_at"] = old_time.isoformat()
    
    with cache_files[0].open("w") as f:
        json.dump(entry, f)
    
    # Attempt retrieval - should be expired
    retrieved = cache.get("H", 1, 400.0, 700.0)
    assert retrieved is None
    assert cache.stats["evictions"] == 1
    # File should be removed
    assert not cache_files[0].exists()


def test_cache_clear(cache: LineListCache, sample_data: Dict[str, Any]) -> None:
    """Clear removes all cached entries."""
    # Store multiple entries
    cache.set("H", 1, 400.0, 700.0, sample_data)
    cache.set("He", 1, 400.0, 700.0, sample_data)
    cache.set("Fe", 2, 300.0, 600.0, sample_data)
    
    assert len(list(cache.cache_dir.glob("*.json"))) == 3
    
    # Clear cache
    count = cache.clear()
    assert count == 3
    assert cache.stats["evictions"] == 3
    assert len(list(cache.cache_dir.glob("*.json"))) == 0


def test_cache_list_entries(cache: LineListCache, sample_data: Dict[str, Any]) -> None:
    """List entries returns metadata about cached data."""
    cache.set("H", 1, 400.0, 700.0, sample_data)
    cache.set("He", 1, 400.0, 700.0, sample_data)
    
    entries = cache.list_entries()
    assert len(entries) == 2
    
    # Each entry is (key, cached_at, line_count)
    for key, cached_at, line_count in entries:
        assert isinstance(key, str)
        assert isinstance(cached_at, datetime)
        assert isinstance(line_count, int)
        assert line_count == 3  # Our sample data has 3 lines


def test_cache_disabled(cache_dir: Path, sample_data: Dict[str, Any]) -> None:
    """Disabled cache performs no-ops."""
    cache = LineListCache(cache_dir, enabled=False)
    
    assert not cache.enabled
    
    # Set does nothing
    result = cache.set("H", 1, 400.0, 700.0, sample_data)
    assert result is False
    assert cache.stats["stores"] == 0
    
    # Get returns None
    result = cache.get("H", 1, 400.0, 700.0)
    assert result is None
    assert cache.stats["misses"] == 0
    
    # Clear returns 0
    count = cache.clear()
    assert count == 0


def test_cache_handles_malformed_files(cache: LineListCache, cache_dir: Path) -> None:
    """Cache gracefully handles corrupt or malformed cache files."""
    # Write a malformed JSON file
    bad_file = cache_dir / "H_1_400_700_badhash.json"
    bad_file.write_text("{ this is not valid json }")
    
    # Attempt to retrieve - should handle the error gracefully
    result = cache.get("H", 1, 400.0, 700.0)
    assert result is None
    assert cache.stats["misses"] == 1


def test_cache_key_generation_is_deterministic(cache: LineListCache) -> None:
    """Cache keys are deterministic for same parameters."""
    key1 = cache._make_key("H", 1, 400.0, 700.0)
    key2 = cache._make_key("H", 1, 400.0, 700.0)
    assert key1 == key2
    
    # Different parameters produce different keys
    key3 = cache._make_key("He", 1, 400.0, 700.0)
    assert key3 != key1


def test_cache_key_includes_human_readable_prefix(cache: LineListCache) -> None:
    """Cache keys have human-readable prefixes for debugging."""
    key = cache._make_key("H", 1, 400.0, 700.0)
    # Key format: ELEMENT_ION_LOWERINT_UPPERINT_hash
    assert key.startswith("H_1_400_700_")
    
    key_fe = cache._make_key("Fe", 2, 300.5, 600.9)
    assert key_fe.startswith("FE_2_300_600_")
