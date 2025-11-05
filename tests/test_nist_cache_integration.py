"""Integration tests for NIST ASD service with caching."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from app.services import nist_asd_service
from app.services.line_list_cache import LineListCache


@pytest.fixture
def mock_cache(tmp_path: Path) -> LineListCache:
    """Return a fresh cache for testing."""
    cache_dir = tmp_path / "nist_cache"
    return LineListCache(cache_dir, enabled=True)


@pytest.fixture
def sample_nist_response() -> Dict[str, Any]:
    """Sample NIST query response structure."""
    return {
        "wavelength_nm": [656.3, 486.1],
        "intensity": [100.0, 50.0],
        "intensity_normalized": [1.0, 0.5],
        "lines": [
            {
                "wavelength_nm": 656.3,
                "relative_intensity": 100.0,
                "relative_intensity_normalized": 1.0,
            },
            {
                "wavelength_nm": 486.1,
                "relative_intensity": 50.0,
                "relative_intensity_normalized": 0.5,
            },
        ],
        "meta": {
            "source_type": "reference",
            "archive": "NIST ASD",
            "label": "H I (NIST ASD)",
            "element_symbol": "H",
            "ion_stage": "I",
        },
    }


def test_cache_stats_api() -> None:
    """Cache stats API returns dictionary with hit/miss/store/eviction counts."""
    stats = nist_asd_service.cache_stats()
    assert isinstance(stats, dict)
    assert "hits" in stats
    assert "misses" in stats
    assert "stores" in stats
    assert "evictions" in stats


def test_get_cache_returns_singleton() -> None:
    """get_cache returns the same instance on repeated calls."""
    cache1 = nist_asd_service.get_cache()
    cache2 = nist_asd_service.get_cache()
    assert cache1 is cache2


@patch.object(nist_asd_service, "_CACHE", None)
@patch.dict("os.environ", {"SPECTRA_DISABLE_LINE_CACHE": "1"})
def test_cache_can_be_disabled_via_environment() -> None:
    """Cache can be disabled via SPECTRA_DISABLE_LINE_CACHE environment variable."""
    cache = nist_asd_service.get_cache()
    assert not cache.enabled


@patch.object(nist_asd_service, "Nist")
@patch.object(nist_asd_service, "ASTROQUERY_AVAILABLE", True)
@patch.object(nist_asd_service, "_CACHE", None)
def test_fetch_lines_uses_cache_on_hit(
    mock_nist: MagicMock,
    tmp_path: Path,
    sample_nist_response: Dict[str, Any],
) -> None:
    """fetch_lines returns cached data without querying NIST on cache hit."""
    # Setup cache with pre-populated data
    cache_dir = tmp_path / "cache"
    cache = LineListCache(cache_dir, enabled=True)
    cache.set("H", 1, 400.0, 700.0, sample_nist_response)
    
    # Replace global cache
    nist_asd_service._CACHE = cache
    
    # Call fetch_lines
    result = nist_asd_service.fetch_lines(
        "H I",
        lower_wavelength=400.0,
        upper_wavelength=700.0,
        use_cache=True,
    )
    
    # Should return cached data
    assert result is not None
    assert result["meta"]["cache_hit"] is True
    assert result["wavelength_nm"] == [656.3, 486.1]
    
    # NIST should NOT have been queried
    mock_nist.query.assert_not_called()
    
    # Cache stats should show a hit
    assert cache.stats["hits"] == 1


@patch.object(nist_asd_service, "Nist")
@patch.object(nist_asd_service, "ASTROQUERY_AVAILABLE", True)
@patch.object(nist_asd_service, "_CACHE", None)
def test_fetch_lines_populates_cache_on_miss(
    mock_nist: MagicMock,
    tmp_path: Path,
) -> None:
    """fetch_lines populates cache after successful NIST query."""
    # Setup empty cache
    cache_dir = tmp_path / "cache"
    cache = LineListCache(cache_dir, enabled=True)
    nist_asd_service._CACHE = cache
    
    # Mock NIST response
    mock_table = MagicMock()
    mock_table.colnames = ["Observed", "Ritz", "Rel.", "Aki", "fik", "Acc.", 
                           "Lower level", "Upper level", "Type", "TP", "Line", 
                           "Ei           Ek"]
    mock_row = {
        "Observed": 656.3,
        "Ritz": 656.28,
        "Rel.": 100.0,
        "Aki": None,
        "fik": None,
        "Acc.": "A",
        "Lower level": "2p",
        "Upper level": "3d",
        "Type": None,
        "TP": None,
        "Line": None,
        "Ei           Ek": "10.2  12.1",
    }
    mock_table.__iter__ = lambda self: iter([mock_row])
    mock_nist.query.return_value = mock_table
    
    # Call fetch_lines
    result = nist_asd_service.fetch_lines(
        "H I",
        lower_wavelength=400.0,
        upper_wavelength=700.0,
        use_cache=True,
    )
    
    # Should have queried NIST
    mock_nist.query.assert_called_once()
    
    # Should have stored in cache
    assert cache.stats["stores"] == 1
    assert result["meta"]["cache_hit"] is False
    
    # Second call should hit cache
    mock_nist.query.reset_mock()
    result2 = nist_asd_service.fetch_lines(
        "H I",
        lower_wavelength=400.0,
        upper_wavelength=700.0,
        use_cache=True,
    )
    
    assert result2["meta"]["cache_hit"] is True
    mock_nist.query.assert_not_called()
    assert cache.stats["hits"] == 1


@patch.object(nist_asd_service, "Nist")
@patch.object(nist_asd_service, "ASTROQUERY_AVAILABLE", True)
@patch.object(nist_asd_service, "_CACHE", None)
def test_fetch_lines_bypasses_cache_when_disabled(
    mock_nist: MagicMock,
    tmp_path: Path,
) -> None:
    """fetch_lines bypasses cache when use_cache=False."""
    # Setup cache with data
    cache_dir = tmp_path / "cache"
    cache = LineListCache(cache_dir, enabled=True)
    sample_data = {
        "wavelength_nm": [656.3],
        "meta": {"cache_hit": True},
    }
    cache.set("H", 1, 400.0, 700.0, sample_data)
    nist_asd_service._CACHE = cache
    
    # Mock NIST response
    mock_table = MagicMock()
    mock_table.colnames = ["Observed", "Ritz", "Rel."]
    mock_table.__iter__ = lambda self: iter([])
    mock_nist.query.return_value = mock_table
    
    # Call with use_cache=False
    result = nist_asd_service.fetch_lines(
        "H I",
        lower_wavelength=400.0,
        upper_wavelength=700.0,
        use_cache=False,
    )
    
    # Should have queried NIST despite cache
    mock_nist.query.assert_called_once()
    assert result["meta"]["cache_hit"] is False
    
    # Cache should not have been checked (no hits)
    assert cache.stats["hits"] == 0


@patch.object(nist_asd_service, "_CACHE", None)
def test_clear_cache_removes_all_entries(tmp_path: Path) -> None:
    """clear_cache removes all cached line lists."""
    cache_dir = tmp_path / "cache"
    cache = LineListCache(cache_dir, enabled=True)
    
    # Populate cache
    sample = {"wavelength_nm": [656.3], "meta": {}}
    cache.set("H", 1, 400.0, 700.0, sample)
    cache.set("He", 1, 400.0, 700.0, sample)
    
    nist_asd_service._CACHE = cache
    
    # Clear via service
    count = nist_asd_service.clear_cache()
    
    assert count == 2
    assert len(list(cache_dir.glob("*.json"))) == 0
