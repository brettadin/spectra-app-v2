"""Cache for NIST spectral line lists to avoid repeated network queries."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class LineListCache:
    """
    Disk-backed cache for NIST spectral line query results.
    
    Cache keys are derived from query parameters (element, ion_stage, wavelength_range).
    Entries are stored as JSON files under storage://cache/_cache/line_lists/ (defaulting to
    <repo>/downloads/_cache/line_lists during migration) with metadata
    including fetch timestamp and expiry.
    """

    def __init__(
        self,
        cache_dir: str | Path | None = None,
        *,
        max_age_days: int = 365,
        enabled: bool = True,
    ) -> None:
        """
        Initialize the line list cache.
        
        Args:
            cache_dir: Directory to store cached line lists. If None, defaults to
                      storage://cache/_cache/line_lists/ (resolved via PathAlias) relative
                      to the workspace root.
            max_age_days: Maximum age in days before cached entries are considered stale.
                         Defaults to 365 days (spectral lines are stable reference data).
            enabled: Whether caching is enabled. If False, all operations become no-ops.
        """
        self._enabled = enabled
        self._max_age = timedelta(days=max_age_days)
        
        if cache_dir is None:
            # Default to storage://cache/_cache/line_lists (compatible with downloads/ during migration)
            try:
                from app.utils.path_alias import PathAlias  # lazy import to avoid cycles
                cache_root = PathAlias.resolve("storage://cache")
            except Exception:
                # Fallback to repo_root/downloads for maximum compatibility if alias helper unavailable
                cache_root = Path(__file__).resolve().parents[2] / "downloads"
            cache_dir = cache_root / "_cache" / "line_lists"
        
        self._cache_dir = Path(cache_dir)
        
        if self._enabled:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Line list cache initialized: {self._cache_dir}")
        
        self._stats = {
            "hits": 0,
            "misses": 0,
            "stores": 0,
            "evictions": 0,
        }

    @property
    def enabled(self) -> bool:
        """Return True if caching is enabled."""
        return self._enabled

    @property
    def cache_dir(self) -> Path:
        """Return the cache directory path."""
        return self._cache_dir

    @property
    def stats(self) -> Dict[str, int]:
        """Return cache statistics (hits, misses, stores, evictions)."""
        return self._stats.copy()

    def _make_key(
        self,
        element_symbol: str,
        ion_stage: int,
        lower_wavelength_nm: float,
        upper_wavelength_nm: float,
    ) -> str:
        """
        Generate a unique cache key from query parameters.
        
        Returns a deterministic hash string suitable for use as a filename.
        """
        # Normalize to ensure consistent keys
        symbol = element_symbol.strip().upper()
        lower = round(float(lower_wavelength_nm), 3)
        upper = round(float(upper_wavelength_nm), 3)
        
        # Canonical representation for hashing
        parts = [symbol, str(ion_stage), f"{lower:.3f}", f"{upper:.3f}"]
        canonical = "|".join(parts)
        
        # Generate short hash for filename
        digest = hashlib.sha256(canonical.encode()).hexdigest()[:16]
        
        # Human-readable prefix for debugging
        prefix = f"{symbol}_{ion_stage}_{int(lower)}_{int(upper)}"
        
        return f"{prefix}_{digest}"

    def _get_path(self, key: str) -> Path:
        """Return the filesystem path for a cache entry."""
        return self._cache_dir / f"{key}.json"

    def get(
        self,
        element_symbol: str,
        ion_stage: int,
        lower_wavelength_nm: float,
        upper_wavelength_nm: float,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached line list data if available and not expired.
        
        Returns None on cache miss or if caching is disabled.
        """
        if not self._enabled:
            return None
        
        key = self._make_key(element_symbol, ion_stage, lower_wavelength_nm, upper_wavelength_nm)
        path = self._get_path(key)
        
        if not path.exists():
            self._stats["misses"] += 1
            logger.debug(f"Cache miss: {key}")
            return None
        
        try:
            with path.open("r", encoding="utf-8") as f:
                entry = json.load(f)
            
            # Check expiry
            cached_at_str = entry.get("cached_at")
            if cached_at_str:
                cached_at = datetime.fromisoformat(cached_at_str)
                age = datetime.now(UTC) - cached_at
                
                if age > self._max_age:
                    logger.info(f"Cache entry expired (age={age.days}d): {key}")
                    self._stats["evictions"] += 1
                    path.unlink()
                    self._stats["misses"] += 1
                    return None
            
            # Valid cache hit
            self._stats["hits"] += 1
            logger.debug(f"Cache hit: {key}")
            return entry.get("data")
        
        except Exception as exc:
            logger.warning(f"Failed to read cache entry {key}: {exc}")
            self._stats["misses"] += 1
            return None

    def set(
        self,
        element_symbol: str,
        ion_stage: int,
        lower_wavelength_nm: float,
        upper_wavelength_nm: float,
        data: Dict[str, Any],
    ) -> bool:
        """
        Store line list data in the cache.
        
        Returns True on success, False on failure or if caching is disabled.
        """
        if not self._enabled:
            return False
        
        key = self._make_key(element_symbol, ion_stage, lower_wavelength_nm, upper_wavelength_nm)
        path = self._get_path(key)
        
        try:
            entry = {
                "cached_at": datetime.now(UTC).isoformat(),
                "query": {
                    "element_symbol": element_symbol,
                    "ion_stage": ion_stage,
                    "lower_wavelength_nm": lower_wavelength_nm,
                    "upper_wavelength_nm": upper_wavelength_nm,
                },
                "data": data,
            }
            
            with path.open("w", encoding="utf-8") as f:
                json.dump(entry, f, indent=2)
            
            self._stats["stores"] += 1
            logger.debug(f"Cached line list: {key}")
            return True
        
        except Exception as exc:
            logger.warning(f"Failed to cache line list {key}: {exc}")
            return False

    def clear(self) -> int:
        """
        Remove all cached entries.
        
        Returns the number of entries removed.
        """
        if not self._enabled:
            return 0
        
        count = 0
        try:
            for path in self._cache_dir.glob("*.json"):
                try:
                    path.unlink()
                    count += 1
                except Exception as exc:
                    logger.warning(f"Failed to remove cache entry {path.name}: {exc}")
            
            logger.info(f"Cleared {count} cached line lists")
            self._stats["evictions"] += count
            return count
        
        except Exception as exc:
            logger.warning(f"Failed to clear cache directory: {exc}")
            return count

    def list_entries(self) -> list[Tuple[str, datetime, int]]:
        """
        List all cached entries with metadata.
        
        Returns a list of tuples: (key, cached_at, line_count)
        """
        if not self._enabled:
            return []
        
        entries = []
        try:
            for path in self._cache_dir.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as f:
                        entry = json.load(f)
                    
                    key = path.stem
                    cached_at_str = entry.get("cached_at", "")
                    cached_at = datetime.fromisoformat(cached_at_str) if cached_at_str else None
                    
                    lines = entry.get("data", {}).get("lines", [])
                    line_count = len(lines) if isinstance(lines, list) else 0
                    
                    if cached_at:
                        entries.append((key, cached_at, line_count))
                
                except Exception as exc:
                    logger.debug(f"Skipping invalid cache entry {path.name}: {exc}")
            
            # Sort by cached_at descending (most recent first)
            entries.sort(key=lambda e: e[1], reverse=True)
            return entries
        
        except Exception as exc:
            logger.warning(f"Failed to list cache entries: {exc}")
            return []
