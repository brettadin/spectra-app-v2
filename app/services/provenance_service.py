"""Generate and parse provenance manifests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence
import datetime as dt
import hashlib
import json

from .spectrum import Spectrum


@dataclass
class ProvenanceService:
    """Service for creating and persisting provenance manifests."""

    app_name: str = "spectra-app-beta"
    app_version: str = "0.1.0"

    def timestamp(self) -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat()

    def create_manifest(
        self,
        spectra: Sequence[Spectrum],
        *,
        operations: Optional[Sequence[Mapping[str, object]]] = None,
        citations: Optional[Sequence[Mapping[str, object]]] = None,
    ) -> Mapping[str, object]:
        """Create a machine-readable provenance manifest."""

        entries: List[Mapping[str, object]] = []
        for spectrum in spectra:
            entries.append(
                {
                    "id": spectrum.id,
                    "name": spectrum.name,
                    "checksum": spectrum.checksum(),
                    "units": {
                        "wavelength": "nm",
                        "flux": spectrum.flux_unit,
                    },
                    "metadata": dict(spectrum.metadata),
                    "provenance": [dict(p) for p in spectrum.provenance],
                }
            )

        manifest = {
            "app": {"name": self.app_name, "version": self.app_version},
            "created": self.timestamp(),
            "spectra": entries,
            "operations": [dict(op) for op in (operations or [])],
            "citations": [dict(c) for c in (citations or [])],
        }
        return manifest

    def save_manifest(self, manifest: Mapping[str, object], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2)

    def manifest_for_operation(
        self,
        result: Spectrum,
        inputs: Iterable[Spectrum],
        *,
        operation: Mapping[str, object],
    ) -> Mapping[str, object]:
        operations = [dict(operation)]
        manifest = self.create_manifest([result] + list(inputs), operations=operations)
        return manifest

    def checksum_bytes(self, data: bytes) -> str:
        digest = hashlib.sha256()
        digest.update(data)
        return digest.hexdigest()
