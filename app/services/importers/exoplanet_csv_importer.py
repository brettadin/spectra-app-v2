"""Importer for exoplanet transmission/emission spectra CSV files.

These files typically contain CENTRALWAVELNG (in microns), BANDWIDTH, and 
optionally FLAM or other flux columns. Used for JWST and HST exoplanet spectra.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import numpy as np

from .base import ImporterResult


class ExoplanetCsvImporter:
    """Import exoplanet spectra with CENTRALWAVELNG/BANDWIDTH format."""

    def can_read(self, path: Path) -> bool:
        """Check if this file appears to be an exoplanet spectrum CSV.
        
        Returns True if the first non-comment line contains CENTRALWAVELNG
        or similar exoplanet spectrum headers.
        """
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    # Check for exoplanet-specific headers
                    line_upper = line.upper()
                    if "CENTRALWAVELNG" in line_upper or "CENTRALWAVE" in line_upper:
                        return True
                    # If we hit data rows without finding the header, bail
                    if any(c.isdigit() for c in line[:20]):
                        return False
                    break
        except (OSError, UnicodeDecodeError):
            pass
        return False

    def read(self, path: Path) -> ImporterResult:
        """Parse exoplanet CSV and return spectrum data.
        
        Expected columns:
        - CENTRALWAVELNG: wavelength in microns (required)
        - BANDWIDTH: spectral resolution/bin width (optional, can be empty)
        - FLAM or similar: flux values (optional)
        
        If no flux column exists, uses row index as placeholder Y values.
        """
        with path.open("r", encoding="utf-8") as f:
            lines = [line for line in f if line.strip() and not line.strip().startswith("#")]
        
        if not lines:
            raise ValueError(f"No data found in {path}")
        
        reader = csv.DictReader(lines)
        fieldnames = reader.fieldnames or []
        
        if not fieldnames:
            raise ValueError(f"No header row found in {path}")
        
        # Normalize field names for lookup
        field_map = {name.strip().upper(): name for name in fieldnames}
        
        # Find wavelength column
        wave_col = None
        for candidate in ["CENTRALWAVELNG", "CENTRALWAVE", "WAVELENGTH", "LAMBDA"]:
            if candidate in field_map:
                wave_col = field_map[candidate]
                break
        
        if wave_col is None:
            raise ValueError(
                f"No wavelength column found in {path}. "
                f"Expected CENTRALWAVELNG or similar. Found: {fieldnames}"
            )
        
        # Find flux column (optional)
        flux_col = None
        for candidate in ["FLAM", "FLUX", "INTENSITY", "F_LAMBDA", "SPECTRUM"]:
            if candidate in field_map:
                flux_col = field_map[candidate]
                break
        
        # Find bandwidth column (informational only for now)
        bandwidth_col = None
        if "BANDWIDTH" in field_map:
            bandwidth_col = field_map["BANDWIDTH"]
        
        # Parse data
        wavelengths: List[float] = []
        fluxes: List[float] = []
        bandwidths: List[float] = []
        
        for row_idx, row in enumerate(reader):
            # Parse wavelength (required)
            wave_str = row.get(wave_col, "").strip()
            if not wave_str:
                continue
            
            try:
                wavelength = float(wave_str)
            except ValueError:
                continue
            
            # Parse flux (optional)
            if flux_col:
                flux_str = row.get(flux_col, "").strip()
                if flux_str:
                    try:
                        flux = float(flux_str)
                    except ValueError:
                        flux = float(row_idx)  # Fallback to index
                else:
                    flux = float(row_idx)
            else:
                # No flux column - use row index
                flux = float(row_idx)
            
            # Parse bandwidth (informational)
            if bandwidth_col:
                bw_str = row.get(bandwidth_col, "").strip()
                if bw_str:
                    try:
                        bandwidth = float(bw_str)
                    except ValueError:
                        bandwidth = 0.0
                else:
                    bandwidth = 0.0
                bandwidths.append(bandwidth)
            
            wavelengths.append(wavelength)
            fluxes.append(flux)
        
        if not wavelengths:
            raise ValueError(f"No valid wavelength data found in {path}")
        
        x = np.asarray(wavelengths, dtype=float)
        y = np.asarray(fluxes, dtype=float)
        
        # Metadata
        metadata: Dict[str, object] = {
            "format": "exoplanet-csv",
            "columns": {
                "wavelength": wave_col,
                "flux": flux_col,
                "bandwidth": bandwidth_col,
            },
            "all_fields": list(fieldnames),
        }
        
        if bandwidths:
            metadata["bandwidths"] = bandwidths
        
        # Determine units
        # Exoplanet spectra typically use microns for wavelength
        x_unit = "um"
        
        # Y unit depends on what column we found
        if flux_col:
            flux_upper = flux_col.upper()
            if "FLAM" in flux_upper:
                # FLAM = erg/s/cm²/Å or similar flux density
                y_unit = "flux_density"
            else:
                y_unit = "flux"
        else:
            # No flux column - just relative spectrum
            y_unit = "absorbance"  # Generic intensity
        
        # Ensure monotonic increasing wavelength
        if x.size > 1 and x[0] > x[-1]:
            x = x[::-1]
            y = y[::-1]
            metadata["sorted"] = "descending→ascending"
        
        return ImporterResult(
            name=path.stem,
            x=x,
            y=y,
            x_unit=x_unit,
            y_unit=y_unit,
            metadata=metadata,
            source_path=path,
        )
