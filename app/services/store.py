
"""Local persistence for ingested spectra and provenance manifests."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, Callable, Dict, Mapping, MutableMapping


_INDEX_TEMPLATE: Dict[str, Any] = {"version": 1, "items": {}}


@dataclass
class LocalStore:
    """Persist ingested spectra into the application data directory."""

    app_name: str = "SpectraApp"
    base_dir: Path | None = None
    env: Mapping[str, str] | None = None
    clock: Callable[..., datetime] = datetime.now
    _index_cache: Dict[str, Any] = field(default_factory=dict, init=False)

    @property
    def data_dir(self) -> Path:
        if self.base_dir is not None:
            return Path(self.base_dir)
        environ: Mapping[str, str] = self.env or os.environ
        appdata = environ.get("APPDATA")
        if appdata:
            return Path(appdata) / self.app_name / "data"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / self.app_name / "data"
        if sys.platform == "win32":
            return Path.home() / "AppData" / "Roaming" / self.app_name / "data"
        return Path.home() / ".local" / "share" / self.app_name / "data"

    @property
    def index_path(self) -> Path:
        return self.data_dir / "index.json"

    def load_index(self) -> Dict[str, Any]:
        if self._index_cache:
            return self._index_cache
        path = self.index_path
        if not path.exists():
            self._index_cache = json.loads(json.dumps(_INDEX_TEMPLATE))
            return self._index_cache
        with path.open("r", encoding="utf-8") as handle:
            self._index_cache = json.load(handle)
        self._index_cache.setdefault("version", 1)
        self._index_cache.setdefault("items", {})
        return self._index_cache

    def save_index(self, index: MutableMapping[str, Any] | None = None) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        payload = index or self.load_index()
        with self.index_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        self._index_cache = json.loads(json.dumps(payload))

    def record(
        self,
        source_path: Path,
        *,
        x_unit: str,
        y_unit: str,
        source: Mapping[str, Any] | None = None,
        manifest_path: Path | None = None,
        alias: str | None = None,
    ) -> Dict[str, Any]:
        source_path = Path(source_path)
        stored_path = self._copy_into_store(source_path, alias=alias)
        checksum = self._sha256(stored_path)

        index = self.load_index()
        items: MutableMapping[str, Any] = index.setdefault("items", {})  # type: ignore[assignment]
        entry = dict(items.get(checksum, {}))
        created = entry.get("created", self._timestamp())

        entry.update(
            {
                "sha256": checksum,
                "filename": stored_path.name,
                "stored_path": str(stored_path),
                "original_path": str(source_path),
                "bytes": stored_path.stat().st_size,
                "units": {"x": x_unit, "y": y_unit},
                "source": dict(source or {}),
                "created": created,
                "updated": self._timestamp(),
            }
        )
        if manifest_path is not None:
            entry["manifest_path"] = str(manifest_path)
        items[checksum] = entry
        self.save_index(index)
        return entry

    def list_entries(self) -> Dict[str, Any]:
        return self.load_index().get("items", {})

    # ------------------------------------------------------------------
    def _copy_into_store(self, source_path: Path, alias: str | None = None) -> Path:
        checksum = self._sha256(source_path)
        target_dir = self.data_dir / "files" / checksum[:2]
        target_dir.mkdir(parents=True, exist_ok=True)
        filename = alias or source_path.name
        target_path = target_dir / filename
        if not target_path.exists():
            shutil.copy2(source_path, target_path)
        return target_path

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _timestamp(self) -> str:
        clock = self.clock
        try:
            moment = clock(timezone.utc)  # type: ignore[misc]
        except TypeError:  # clock without tz argument
            moment = clock()  # type: ignore[misc]
        if not isinstance(moment, datetime):
            moment = datetime.now(timezone.utc)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.isoformat()
