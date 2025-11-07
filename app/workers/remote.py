"""Shared remote data workers for search and download.

These mirror the behavior used by RemoteDataDialog and the main window, but
live in a reusable module to avoid duplication.
"""
from __future__ import annotations


from app.qt_compat import get_qt
from app.services import DataIngestService, RemoteDataService, RemoteRecord

QtCore, QtGui, QtWidgets, _ = get_qt()  # type: ignore[misc]

# Dynamic Signal/Slot resolution for PySide6/PyQt6 compatibility
Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:  # pragma: no cover - compatibility shim
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]

Slot = getattr(QtCore, "Slot", None)  # type: ignore[attr-defined]
if Slot is None:  # pragma: no cover - compatibility shim
    Slot = getattr(QtCore, "pyqtSlot")  # type: ignore[attr-defined]


class SearchWorker(QtCore.QObject):  # type: ignore[name-defined]
    """Background worker that streams search results from a remote provider."""

    started = Signal()  # type: ignore[misc]
    record_found = Signal(object)  # type: ignore[misc]
    finished = Signal(list)  # type: ignore[misc]
    failed = Signal(str)  # type: ignore[misc]
    cancelled = Signal()  # type: ignore[misc]

    def __init__(self, remote_service: RemoteDataService) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._cancel_requested = False

    @Slot(str, dict, bool)  # type: ignore[misc]
    def run(self, provider: str, query: dict[str, str], include_imaging: bool) -> None:
        self.started.emit()  # type: ignore[attr-defined]
        collected: list[RemoteRecord] = []

        try:
            # Fast path for NIST or providers without a batching strategy
            if provider == RemoteDataService.PROVIDER_NIST:
                results = self._remote_service.search(provider, query, include_imaging=include_imaging)
                for record in results:
                    if self._cancel_requested:
                        self.cancelled.emit()  # type: ignore[attr-defined]
                        return
                    collected.append(record)
                    self.record_found.emit(record)  # type: ignore[attr-defined]
                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            # Progressive strategy for MAST and ExoSystems
            seen: set[tuple[str, str]] = set()

            def _emit_batch(batch: list[RemoteRecord]) -> None:
                for rec in batch:
                    if self._cancel_requested:
                        self.cancelled.emit()  # type: ignore[attr-defined]
                        return
                    key = (rec.download_url, rec.identifier)
                    if key in seen:
                        continue
                    seen.add(key)
                    collected.append(rec)
                    self.record_found.emit(rec)  # type: ignore[attr-defined]

            if provider == RemoteDataService.PROVIDER_MAST:
                # Prioritise calibrated spectra from common missions first.
                base = dict(query)
                mission_batches: list[list[str]] = [
                    ["JWST"],
                    ["HST"],
                    ["IUE", "FUSE", "GALEX"],
                    ["Kepler", "K2", "TESS"],
                ]

                # Spectra (calib 2/3), by mission group
                for missions in mission_batches:
                    for mission in missions:
                        if self._cancel_requested:
                            self.cancelled.emit()  # type: ignore[attr-defined]
                            return
                        criteria = {**base, "obs_collection": mission, "dataproduct_type": "spectrum", "calib_level": [2, 3], "intentType": "SCIENCE"}
                        try:
                            batch = self._remote_service.search(
                                RemoteDataService.PROVIDER_MAST, criteria, include_imaging=False
                            )
                        except Exception:
                            batch = []
                        _emit_batch(batch)

                # Imaging next (optional)
                if include_imaging:
                    for missions in mission_batches:
                        for mission in missions:
                            if self._cancel_requested:
                                self.cancelled.emit()  # type: ignore[attr-defined]
                                return
                            criteria = {**base, "obs_collection": mission, "dataproduct_type": "image", "intentType": "SCIENCE"}
                            try:
                                batch = self._remote_service.search(
                                    RemoteDataService.PROVIDER_MAST, criteria, include_imaging=True
                                )
                            except Exception:
                                batch = []
                            _emit_batch(batch)

                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            if provider == RemoteDataService.PROVIDER_EXOSYSTEMS:
                # Fetch spectra first to get relevant results quickly
                try:
                    spectral = self._remote_service.search(
                        RemoteDataService.PROVIDER_EXOSYSTEMS, query, include_imaging=False
                    )
                except Exception:
                    spectral = []
                _emit_batch(spectral)

                if include_imaging:
                    try:
                        mixed = self._remote_service.search(
                            RemoteDataService.PROVIDER_EXOSYSTEMS, query, include_imaging=True
                        )
                    except Exception:
                        mixed = []
                    imaging_only: list[RemoteRecord] = []
                    for rec in mixed:
                        meta = rec.metadata if isinstance(rec.metadata, dict) else {}
                        dtype = str(meta.get("dataproduct_type") or meta.get("productType") or "").lower()
                        desc = str(meta.get("description") or meta.get("display_name") or "").lower()
                        if ("image" in dtype) or ("image" in desc):
                            imaging_only.append(rec)
                    _emit_batch(imaging_only)

                self.finished.emit(collected)  # type: ignore[attr-defined]
                return

            # Fallback: non-batched search
            results = self._remote_service.search(provider, query, include_imaging=include_imaging)
            _emit_batch(results)
            self.finished.emit(collected)  # type: ignore[attr-defined]
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))  # type: ignore[attr-defined]
            return

    @Slot()  # type: ignore[misc]
    def cancel(self) -> None:
        self._cancel_requested = True


class DownloadWorker(QtCore.QObject):  # type: ignore[name-defined]
    """Background worker that downloads and ingests selected remote records."""

    started = Signal(int)  # type: ignore[misc]
    record_progress = Signal(object, int, int)  # type: ignore[misc]
    record_ingested = Signal(object)  # type: ignore[misc]
    record_failed = Signal(object, str)  # type: ignore[misc]
    finished = Signal(list)  # type: ignore[misc]
    failed = Signal(str)  # type: ignore[misc]
    cancelled = Signal()  # type: ignore[misc]

    def __init__(
        self,
        remote_service: RemoteDataService,
        ingest_service: DataIngestService,
    ) -> None:
        super().__init__()
        self._remote_service = remote_service
        self._ingest_service = ingest_service
        self._cancel_requested = False

    @Slot(list)  # type: ignore[misc]
    def run(self, records: list[RemoteRecord]) -> None:
        self.started.emit(len(records))  # type: ignore[attr-defined]
        ingested: list[object] = []
        try:
            for record in records:
                if self._cancel_requested:
                    self.cancelled.emit()  # type: ignore[attr-defined]
                    return
                try:
                    def _progress(rec: RemoteRecord, received: int, total: int | None) -> None:
                        if self._cancel_requested:
                            return
                        self.record_progress.emit(
                            rec,
                            int(received),
                            int(total) if total is not None else -1,
                        )

                    download = self._remote_service.download(record, progress=_progress)
                    file_path = download.path

                    # Skip non-spectral file types (images, logs, etc.)
                    non_spectral_extensions = {
                        '.gif', '.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.svg',
                        '.txt', '.log', '.xml', '.html', '.htm', '.json', '.md'
                    }
                    if file_path.suffix.lower() in non_spectral_extensions:
                        self.record_failed.emit(
                            record,
                            f"Skipped non-spectral file type: {file_path.suffix}"
                        )  # type: ignore[attr-defined]
                        continue

                    ingested_item = self._ingest_service.ingest(file_path)
                except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
                    self.record_failed.emit(record, str(exc))  # type: ignore[attr-defined]
                    continue
                if isinstance(ingested_item, list):
                    ingested.extend(ingested_item)
                else:
                    ingested.append(ingested_item)
                self.record_ingested.emit(record)  # type: ignore[attr-defined]
            if self._cancel_requested:
                self.cancelled.emit()  # type: ignore[attr-defined]
                return
        except Exception as exc:  # pragma: no cover - defensive: surfaced via signal
            self.failed.emit(str(exc))  # type: ignore[attr-defined]
            return
        self.finished.emit(ingested)  # type: ignore[attr-defined]

    @Slot()  # type: ignore[misc]
    def cancel(self) -> None:
        self._cancel_requested = True
