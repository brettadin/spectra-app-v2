"""Immutable representation of spectral data."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence, Tuple, Optional
import hashlib
import uuid
import numpy as np


def _as_readonly(array: np.ndarray) -> np.ndarray:
    out = np.array(array, dtype=float, copy=True)
    out.setflags(write=False)
    return out


@dataclass(frozen=True)
class Spectrum:
    """A single spectral dataset with canonical wavelength storage."""

    id: str
    name: str
    wavelength_nm: np.ndarray = field(metadata={"unit": "nm"})
    flux: np.ndarray = field(metadata={"unit": "absorbance"})
    flux_unit: str = "absorbance"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance: Tuple[Mapping[str, Any], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:  # type: ignore[override]
        object.__setattr__(self, "wavelength_nm", _as_readonly(self.wavelength_nm))
        object.__setattr__(self, "flux", _as_readonly(self.flux))

    @classmethod
    def create(
        cls,
        name: str,
        wavelength_nm: np.ndarray,
        flux: np.ndarray,
        *,
        flux_unit: str = "absorbance",
        metadata: Optional[Mapping[str, Any]] = None,
        provenance: Optional[Sequence[Mapping[str, Any]]] = None,
        identifier: Optional[str] = None,
    ) -> "Spectrum":
        """Factory ensuring identifiers and immutability."""

        spec_id = identifier or str(uuid.uuid4())
        return cls(
            id=spec_id,
            name=name,
            wavelength_nm=_as_readonly(wavelength_nm),
            flux=_as_readonly(flux),
            flux_unit=flux_unit,
            metadata=dict(metadata or {}),
            provenance=tuple(dict(p) for p in provenance or ()),
        )

    def as_units(
        self,
        units_service: "UnitsService",
        *,
        wavelength_unit: str = "nm",
        flux_unit: Optional[str] = None,
        context: Optional[Mapping[str, Any]] = None,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return arrays converted into the requested units."""

        flux_unit = flux_unit or self.flux_unit
        x = units_service.convert_wavelength(self.wavelength_nm, "nm", wavelength_unit)
        y = units_service.convert_flux(self.flux, self.flux_unit, flux_unit, context=context or {})
        return x, y

    def with_name(self, name: str) -> "Spectrum":
        """Return a copy of the spectrum with a different display name."""

        return replace(self, name=name)

    def with_provenance(self, entry: Mapping[str, Any]) -> "Spectrum":
        """Append a provenance entry and return a new spectrum."""

        return replace(self, provenance=self.provenance + (dict(entry),))

    def checksum(self) -> str:
        """Return a SHA-256 checksum of canonical data for provenance."""

        digest = hashlib.sha256()
        digest.update(self.wavelength_nm.tobytes())
        digest.update(self.flux.tobytes())
        digest.update(self.flux_unit.encode("utf-8"))
        return digest.hexdigest()


# Avoid circular import by typing reference at runtime
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from .units_service import UnitsService
