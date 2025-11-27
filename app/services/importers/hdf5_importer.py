"""HDF5 importer for JWST/Eureka pipeline outputs and generic HDF5 spectral data.

Supports:
- Eureka! Stage 4 light curve outputs (.h5)
- Generic HDF5 files with wavelength/flux datasets
- JWST pipeline products in HDF5 format

This is separate from modis_hdf_importer.py which handles HDF4 files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import h5py  # type: ignore[import-not-found]
    HDF5_AVAILABLE = True
except ImportError:
    HDF5_AVAILABLE = False

import numpy as np

from .base import ImporterResult, SupportsImport


class Hdf5Importer:
    """Import spectral data from HDF5 files (.h5, .hdf5).
    
    Attempts to detect common HDF5 structures:
    1. Eureka! pipeline outputs (wavelength, spectrum, error)
    2. Generic wavelength/flux pairs
    3. JWST pipeline products
    """

    def can_import(self, path: Path) -> bool:
        """Check if file is HDF5 format."""
        if not HDF5_AVAILABLE:
            return False
        
        suffix = path.suffix.lower()
        if suffix not in {".h5", ".hdf5"}:
            return False
        
        # Quick header check
        try:
            with h5py.File(path, "r") as f:
                # HDF5 files should have at least one dataset
                return len(f.keys()) > 0
        except Exception:
            return False

    def read(self, path: Path) -> ImporterResult:
        """Import spectral data from HDF5 file."""
        if not HDF5_AVAILABLE:
            raise ImportError(
                "h5py is required for HDF5 import. "
                "Install with: pip install h5py"
            )
        
        with h5py.File(path, "r") as f:
            # Try Eureka! format first (most common for JWST transit spectra)
            if self._is_eureka_format(f):
                return self._import_eureka(f, path)
            
            # Try generic wavelength/flux structure
            wave, flux = self._find_wavelength_flux_datasets(f)
            if wave is not None and flux is not None:
                return self._import_generic(wave, flux, path)
            
            # Fallback: list available datasets for debugging
            datasets = self._list_datasets(f)
            raise ValueError(
                f"Could not find recognized spectral data structure in {path.name}. "
                f"Available datasets: {datasets}. "
                f"Supported formats: Eureka! Stage 4, generic wavelength/flux pairs."
            )

    def _is_eureka_format(self, f: h5py.File) -> bool:
        """Check if HDF5 file matches Eureka! Stage 4 output structure."""
        # Eureka! typically has: wavelength, spectrum/data, errors/err, time
        # Check for wavelength + (spectrum OR data)
        available = set(f.keys())
        has_wavelength = "wavelength" in available
        has_flux = "spectrum" in available or "data" in available
        return has_wavelength and has_flux

    def _import_eureka(self, f: h5py.File, path: Path) -> ImporterResult:
        """Import Eureka! Stage 4 light curve data."""
        wave = np.array(f["wavelength"])
        
        # Eureka! uses 'spectrum' or 'data' for flux
        flux_key = "spectrum" if "spectrum" in f else "data"
        flux = np.array(f[flux_key])
        
        # Eureka! may store 2D arrays
        # Common shapes: (wavelength, time) or (time, wavelength)
        # If 2D, collapse across time dimension (axis with more elements usually time)
        if flux.ndim == 2:
            # Determine which axis is time vs wavelength
            if flux.shape[0] == len(wave):
                # Shape is (wavelength, time) - collapse axis 1
                flux = np.median(flux, axis=1)
            else:
                # Shape is (time, wavelength) - collapse axis 0
                flux = np.median(flux, axis=0)
        
        # Load uncertainties if available
        metadata: dict[str, Any] = {
            "format": "Eureka! Stage 4",
            "dimensions": f[flux_key].shape,
        }
        
        # Check for errors dataset (various naming conventions)
        err_key = None
        if "errors" in f:
            err_key = "errors"
        elif "err" in f:
            err_key = "err"
        
        if err_key:
            err = np.array(f[err_key])
            if err.ndim == 2:
                # Propagate errors: median of variances -> sqrt
                # Use same axis logic as flux
                if err.shape[0] == len(wave):
                    uncertainty = np.sqrt(np.median(err**2, axis=1))
                else:
                    uncertainty = np.sqrt(np.median(err**2, axis=0))
            else:
                uncertainty = err
            metadata["uncertainty"] = uncertainty
        
        # Eureka! wavelengths are typically in microns
        x_unit = "µm"
        
        return ImporterResult(
            name=path.stem,
            x=wave,
            y=flux,
            x_unit=x_unit,
            y_unit="intensity",  # Normalized flux
            metadata=metadata,
            source_path=path,
        )

    def _find_wavelength_flux_datasets(
        self, f: h5py.File
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """Attempt to find wavelength and flux datasets by common naming."""
        wave_candidates = ["wavelength", "wave", "lambda", "wl", "x"]
        flux_candidates = ["spectrum", "flux", "intensity", "y", "data"]
        
        wave_data = None
        flux_data = None
        
        for key in f.keys():
            lower_key = key.lower()
            
            # Find wavelength
            if wave_data is None:
                for candidate in wave_candidates:
                    if candidate in lower_key:
                        try:
                            wave_data = np.array(f[key])
                            break
                        except Exception:
                            pass
            
            # Find flux
            if flux_data is None:
                for candidate in flux_candidates:
                    if candidate in lower_key:
                        try:
                            flux_data = np.array(f[key])
                            break
                        except Exception:
                            pass
        
        return wave_data, flux_data

    def _import_generic(
        self, wave: np.ndarray, flux: np.ndarray, path: Path
    ) -> ImporterResult:
        """Import generic wavelength/flux HDF5 data."""
        # Handle 2D flux (take first spectrum or median)
        if flux.ndim == 2:
            if flux.shape[0] == 1:
                flux = flux[0]
            else:
                flux = np.median(flux, axis=0)
        
        # Ensure 1D
        wave = wave.flatten()
        flux = flux.flatten()
        
        # Guess units based on wavelength range
        wave_median = np.median(wave)
        if wave_median < 1:
            x_unit = "µm"
        elif wave_median < 100:
            x_unit = "µm"
        elif wave_median < 10000:
            x_unit = "nm"
        else:
            x_unit = "Å"
        
        return ImporterResult(
            name=path.stem,
            x=wave,
            y=flux,
            x_unit=x_unit,
            y_unit="intensity",
            metadata={"format": "Generic HDF5"},
            source_path=path,
        )

    def _list_datasets(self, f: h5py.File, prefix: str = "") -> list[str]:
        """Recursively list all datasets in HDF5 file."""
        datasets = []
        
        for key in f.keys():
            item = f[key]
            full_path = f"{prefix}/{key}" if prefix else key
            
            if isinstance(item, h5py.Dataset):
                shape = item.shape if hasattr(item, "shape") else "scalar"
                datasets.append(f"{full_path} {shape}")
            elif isinstance(item, h5py.Group):
                datasets.extend(self._list_datasets(item, full_path))
        
        return datasets


def create_importer() -> SupportsImport:
    """Factory function to create HDF5 importer instance."""
    return Hdf5Importer()  # type: ignore[return-value]
