from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.services import KnowledgeLogService


def test_record_and_load_round_trip(tmp_path: Path) -> None:
    log_path = tmp_path / "knowledge_log.md"
    service = KnowledgeLogService(log_path=log_path, author="tester", default_context="Unit Test")

    entry = service.record_event("Export", "Generated calibration manifest", ["exports/calibration.json"])

    assert log_path.exists()
    contents = log_path.read_text(encoding="utf-8")
    assert "Generated calibration manifest" in contents
    assert "Export" in contents

    entries = service.load_entries()
    assert entries
    first = entries[0]
    assert first.component == "Export"
    assert "Generated calibration manifest" in first.summary
    assert first.references == ("exports/calibration.json",)
    assert first.author == "tester"
    assert first.context == "Unit Test"
    assert entry.summary == first.summary


def test_record_without_persist(tmp_path: Path) -> None:
    log_path = tmp_path / "knowledge_log.md"
    service = KnowledgeLogService(log_path=log_path, author="tester", default_context="Unit Test")

    entry = service.record_event("Import", "Loaded calibration frame", persist=False)

    assert not log_path.exists()
    assert entry.component == "Import"
    assert entry.summary == "Loaded calibration frame"
    assert entry.references == ()


def test_load_filters_and_export(tmp_path: Path) -> None:
    log_path = tmp_path / "knowledge_log.md"
    service = KnowledgeLogService(
        log_path=log_path,
        author="tester",
        runtime_only_components=(),
    )

    service.record_event(
        "Import",
        "Initial spectrum ingest",
        ["samples/a.csv"],
        timestamp=datetime(2025, 1, 1, 12, 0, 0),
    )
    service.record_event(
        "Export",
        "Created manifest bundle",
        ["exports/manifest.json"],
        timestamp=datetime(2025, 1, 2, 8, 30, 0),
    )
    service.record_event(
        "Import",
        "Follow-up ingest with cache hit",
        ["samples/b.csv"],
        timestamp=datetime(2025, 1, 3, 9, 15, 0),
    )

    imports = service.load_entries(component="Import")
    assert len(imports) == 2
    assert all(entry.component == "Import" for entry in imports)

    search = service.load_entries(search="manifest")
    assert len(search) == 1
    assert search[0].component == "Export"

    export_path = tmp_path / "subset.md"
    service.export_entries(export_path, imports)
    exported = export_path.read_text(encoding="utf-8")
    assert "Follow-up ingest" in exported
    assert "Created manifest bundle" not in exported


def test_runtime_only_components_skip_disk(tmp_path: Path) -> None:
    log_path = tmp_path / "knowledge_log.md"
    service = KnowledgeLogService(log_path=log_path, author="tester")

    entry = service.record_event("Remote Import", "Fetched WASP-96 b from MAST")

    assert not log_path.exists()
    assert entry.component == "Remote Import"
    assert "Fetched WASP-96 b" in entry.summary
