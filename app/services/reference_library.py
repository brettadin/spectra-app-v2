"""Curated spectroscopy reference datasets bundled with the app."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


@dataclass(frozen=True)
class ReferencePaths:
    """Container for on-disk reference assets."""

    base_dir: Path

    @property
    def hydrogen(self) -> Path:
        return self.base_dir / "nist_hydrogen_lines.json"

    @property
    def ir_groups(self) -> Path:
        return self.base_dir / "ir_functional_groups.json"

    @property
    def jwst_targets(self) -> Path:
        return self.base_dir / "jwst_targets.json"

    @property
    def line_shapes(self) -> Path:
        return self.base_dir / "line_shape_placeholders.json"


class ReferenceLibrary:
    """Load spectral reference datasets for in-app and programmatic use."""

    def __init__(self, data_dir: Path | None = None) -> None:
        default_dir = Path(__file__).resolve().parent.parent / "data" / "reference"
        base = Path(data_dir) if data_dir is not None else default_dir
        if not base.exists():
            raise FileNotFoundError(f"Reference data directory not found: {base}")
        self.paths = ReferencePaths(base)
        self._cache: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    def spectral_lines(self, *, series: str | None = None) -> List[Mapping[str, Any]]:
        payload = self._load_json(self.paths.hydrogen)
        lines: List[Mapping[str, Any]] = list(payload.get("lines", []))
        if not series:
            return lines
        needle = series.lower()
        return [line for line in lines if str(line.get("series", "")).lower() == needle]

    def hydrogen_metadata(self) -> Mapping[str, Any]:
        payload = self._load_json(self.paths.hydrogen)
        meta = payload.get("metadata", {})
        meta.setdefault("source_id", "nist_asd_unknown")
        return meta

    # ------------------------------------------------------------------
    def ir_functional_groups(self) -> List[Mapping[str, Any]]:
        payload = self._load_json(self.paths.ir_groups)
        return list(payload.get("groups", []))

    def ir_metadata(self) -> Mapping[str, Any]:
        payload = self._load_json(self.paths.ir_groups)
        return payload.get("metadata", {})

    # ------------------------------------------------------------------
    def line_shape_placeholders(self) -> List[Mapping[str, Any]]:
        payload = self._load_json(self.paths.line_shapes)
        return list(payload.get("placeholders", []))

    def line_shape_metadata(self) -> Mapping[str, Any]:
        payload = self._load_json(self.paths.line_shapes)
        return payload.get("metadata", {})

    # ------------------------------------------------------------------
    def jwst_targets(self, *, include_unavailable: bool = True) -> List[Mapping[str, Any]]:
        payload = self._load_json(self.paths.jwst_targets)
        targets: List[Mapping[str, Any]] = list(payload.get("targets", []))
        if include_unavailable:
            return targets
        return [t for t in targets if t.get("status") != "not_observed"]

    def jwst_target(self, target_id: str) -> Optional[Mapping[str, Any]]:
        for target in self.jwst_targets():
            if target.get("id") == target_id:
                return target
        return None

    def jwst_metadata(self) -> Mapping[str, Any]:
        payload = self._load_json(self.paths.jwst_targets)
        return payload.get("metadata", {})

    # ------------------------------------------------------------------
    def bibliography(self) -> List[Mapping[str, str]]:
        entries: List[Mapping[str, str]] = []
        metas = [
            self.hydrogen_metadata(),
            self.ir_metadata(),
            self.line_shape_metadata(),
            self.jwst_metadata(),
        ]
        for meta in metas:
            citation = meta.get("citation") or meta.get("notes")
            if citation:
                entry: Dict[str, str] = {"citation": str(citation)}
                url = meta.get("url")
                if url:
                    entry["url"] = str(url)
                entries.append(entry)
            if meta is metas[2]:  # line-shape metadata includes nested references
                references = meta.get("references")
                if isinstance(references, list):
                    for ref in references:
                        if isinstance(ref, Mapping):
                            citation = ref.get("citation")
                            if not citation:
                                continue
                            entry = {"citation": str(citation)}
                            url = ref.get("url")
                            if url:
                                entry["url"] = str(url)
                            entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    def _load_json(self, path: Path) -> Mapping[str, Any]:
        key = str(path)
        if key not in self._cache:
            with path.open("r", encoding="utf-8") as handle:
                self._cache[key] = json.load(handle)
        return self._cache[key]

    # Convenience -------------------------------------------------------
    @staticmethod
    def flatten_entry(entry: Mapping[str, Any]) -> List[str]:
        tokens: List[str] = []

        def _collect(value: Any) -> None:
            if value is None:
                return
            if isinstance(value, Mapping):
                for inner in value.values():
                    _collect(inner)
                return
            if isinstance(value, (list, tuple, set)):
                for inner in value:
                    _collect(inner)
                return
            tokens.append(str(value))

        _collect(entry)
        return tokens
