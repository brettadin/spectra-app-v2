"""Regression tests for the local cache index."""

from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services.store import LocalStore


@pytest.fixture()
def mini_source(tmp_path: Path) -> Path:
    source = tmp_path / "mini.csv"
    source.write_text("lambda,absorbance\n500,0.1\n", encoding="utf-8")
    return source


def test_data_dir_prefers_appdata(monkeypatch, tmp_path: Path):
    appdata = tmp_path / "Roaming"
    monkeypatch.setenv("APPDATA", str(appdata))
    store = LocalStore()
    expected = appdata / "SpectraApp" / "data"
    assert store.data_dir == expected


def test_record_creates_index_and_copies(tmp_path: Path, mini_source: Path):
    clock_values = deque(
        [
            datetime(2025, 10, 14, 8, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 14, 8, 5, tzinfo=timezone.utc),
        ]
    )

    def clock(_tz=timezone.utc):
        return clock_values.popleft()

    base_dir = tmp_path / "store"
    manifest = tmp_path / "bundle" / "manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("{}", encoding="utf-8")

    store = LocalStore(base_dir=base_dir, clock=clock)
    entry = store.record(
        mini_source,
        x_unit="nm",
        y_unit="absorbance",
        source={"event": "ingest", "importer": "CsvImporter"},
        manifest_path=manifest,
        alias="mini.csv",
    )

    index_path = base_dir / "index.json"
    assert index_path.exists()
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert entry["sha256"] in index["items"]
    stored = index["items"][entry["sha256"]]
    assert stored["units"] == {"x": "nm", "y": "absorbance"}
    assert stored["source"]["event"] == "ingest"
    assert stored["manifest_path"].endswith("manifest.json")
    stored_path = Path(stored["stored_path"])
    assert stored_path.exists()
    assert stored_path.read_text(encoding="utf-8") == mini_source.read_text(encoding="utf-8")
    assert stored["created"] == "2025-10-14T08:00:00+00:00"
    assert stored["updated"] == "2025-10-14T08:05:00+00:00"


def test_record_preserves_created_timestamp(tmp_path: Path, mini_source: Path):
    moments = deque(
        [
            datetime(2025, 10, 14, 9, 0, tzinfo=timezone.utc),
            datetime(2025, 10, 14, 9, 5, tzinfo=timezone.utc),
            datetime(2025, 10, 14, 9, 10, tzinfo=timezone.utc),
            datetime(2025, 10, 14, 9, 15, tzinfo=timezone.utc),
        ]
    )

    def clock(_tz=timezone.utc):
        return moments.popleft()

    store = LocalStore(base_dir=tmp_path / "cache", clock=clock)
    first = store.record(mini_source, x_unit="nm", y_unit="absorbance")
    second = store.record(mini_source, x_unit="nm", y_unit="absorbance")

    assert first["sha256"] == second["sha256"]
    assert first["created"] == second["created"]
    assert first["updated"] != second["updated"]
