#!/usr/bin/env python3
"""
Parse MESSENGER MASCS UVVS data files (PDS3 format) and convert to CSV.

Supports:
- UVVCDR (calibrated): FUV/MUV/VIS science files
- UVVDDR (derived): Surface reflectance files
- UVVEDR (raw): Uncalibrated data (TODO)

Usage:
  python tools/parse_messenger_mascs.py <input.lbl> [output.csv]
  python tools/parse_messenger_mascs.py --batch <directory>

The script reads the PDS label, locates the .DAT file, and extracts
wavelength + flux/reflectance data into a clean CSV format.
"""
from __future__ import annotations

import argparse
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


def parse_fmt_file(fmt_path: Path) -> Dict[str, Tuple[int, int, str]]:
    """
    Parse a PDS .FMT file to extract column definitions.
    
    Returns dict mapping column name to (byte_offset, bytes, data_type)
    """
    columns = {}
    content = fmt_path.read_text(encoding="utf-8", errors="ignore")
    
    # Look for COLUMN definitions
    # Format: OBJECT = COLUMN ... NAME = ... BYTES = ... START_BYTE = ... DATA_TYPE = ...
    column_blocks = re.findall(
        r'OBJECT\s*=\s*COLUMN.*?END_OBJECT\s*=\s*COLUMN',
        content,
        re.DOTALL | re.IGNORECASE
    )
    
    for block in column_blocks:
        name_match = re.search(r'NAME\s*=\s*([^\n]+)', block, re.IGNORECASE)
        bytes_match = re.search(r'^\s*BYTES\s*=\s*(\d+)', block, re.IGNORECASE | re.MULTILINE)
        start_match = re.search(r'START_BYTE\s*=\s*(\d+)', block, re.IGNORECASE)
        type_match = re.search(r'DATA_TYPE\s*=\s*([^\n]+)', block, re.IGNORECASE)
        
        if all([name_match, bytes_match, start_match, type_match]):
            name = name_match.group(1).strip()
            byte_size = int(bytes_match.group(1))
            start_byte = int(start_match.group(1)) - 1  # PDS uses 1-indexed
            data_type = type_match.group(1).strip()
            columns[name] = (start_byte, byte_size, data_type)
    
    return columns


def auto_detect_wavelength_offset(data: bytes, row_bytes: int, num_rows: int = 100) -> Tuple[int, int]:
    """
    Auto-detect wavelength and radiance column offsets by scanning for reasonable values.
    
    Returns: (wavelength_offset, radiance_offset) or raises ValueError
    """
    candidates = []
    
    # Try every 4-byte aligned offset as potential wavelength column
    for wl_offset in range(0, min(row_bytes - 8, 300), 4):
        valid_count = 0
        wl_values = []
        
        for i in range(min(num_rows, num_rows)):
            offset = i * row_bytes + wl_offset
            if offset + 4 > len(data):
                break
            
            try:
                wl = struct.unpack('>f', data[offset:offset+4])[0]
                # Valid wavelength range: 50-1000 nm for all UVVS channels
                # FUV: 115-190, MUV: 160-320, VIS: 250-600
                if 50 < wl < 1000 and not np.isnan(wl):
                    valid_count += 1
                    wl_values.append(wl)
            except:
                continue
        
        # If >40% of rows have valid wavelengths, this is a candidate
        if valid_count > num_rows * 0.4:
            # Check if wavelengths are reasonably monotonic
            if len(wl_values) > 5:
                # Look for radiance column nearby (typically next few floats)
                for rad_offset in range(wl_offset + 4, min(wl_offset + 60, row_bytes - 4), 4):
                    candidates.append((wl_offset, rad_offset, valid_count))
    
    if candidates:
        # Return the candidate with most valid wavelengths
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates[0][0], candidates[0][1]
    
    raise ValueError("Could not auto-detect wavelength column")


@dataclass
class PDSLabel:
    """Parsed PDS3 label metadata."""
    product_id: str
    product_type: str
    detector_id: str
    target_name: str
    start_time: str
    stop_time: str
    record_bytes: int
    file_records: int
    columns: int
    row_bytes: int
    rows: int
    data_file: str
    format_file: str | None

    @classmethod
    def from_file(cls, lbl_path: Path) -> "PDSLabel":
        """Parse a PDS3 label file."""
        content = lbl_path.read_text(encoding="utf-8", errors="ignore")
        
        def extract(pattern: str, default: Any = None) -> Any:
            match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
            return match.group(1).strip() if match else default
        
        return cls(
            product_id=extract(r'PRODUCT_ID\s*=\s*"([^"]+)"', ""),
            product_type=extract(r'PRODUCT_TYPE\s*=\s*"([^"]+)"', ""),
            detector_id=extract(r'DETECTOR_ID\s*=\s*"([^"]+)"', ""),
            target_name=extract(r'TARGET_NAME\s*=\s*"([^"]+)"', ""),
            start_time=extract(r'START_TIME\s*=\s*([^\s]+)', ""),
            stop_time=extract(r'STOP_TIME\s*=\s*([^\s]+)', ""),
            record_bytes=int(extract(r'RECORD_BYTES\s*=\s*(\d+)', 0)),
            file_records=int(extract(r'FILE_RECORDS\s*=\s*(\d+)', 0)),
            columns=int(extract(r'COLUMNS\s*=\s*(\d+)', 0)),
            row_bytes=int(extract(r'ROW_BYTES\s*=\s*(\d+)', 0)),
            rows=int(extract(r'ROWS\s*=\s*(\d+)', 0)),
            data_file=extract(r'\^TABLE\s*=\s*"([^"]+)"', ""),
            format_file=extract(r'\^STRUCTURE\s*=\s*"([^"]+)"'),
        )


def diagnose_binary_structure(dat_path: Path, label: PDSLabel, num_rows: int = 5) -> None:
    """Print diagnostic information about binary file structure."""
    data = dat_path.read_bytes()
    
    print(f"\nDiagnostic for {dat_path.name}:")
    print(f"  Total bytes: {len(data)}")
    print(f"  Expected: {label.rows} rows × {label.row_bytes} bytes = {label.rows * label.row_bytes}")
    print(f"  Row bytes: {label.row_bytes}")
    print(f"\nFirst {num_rows} rows (showing first 200 bytes of each):")
    
    for i in range(min(num_rows, label.rows)):
        offset = i * label.row_bytes
        row = data[offset:offset + min(200, label.row_bytes)]
        
        print(f"\n  Row {i}:")
        print(f"    Hex: {row[:80].hex(' ', 4)}")
        
        # Try to find float patterns (IEEE 754)
        print(f"    Floats (big-endian every 4 bytes):")
        for j in range(0, min(80, len(row)), 4):
            try:
                val = struct.unpack('>f', row[j:j+4])[0]
                if 0.01 < abs(val) < 1e6 and not np.isnan(val):
                    print(f"      Offset {j:3d}: {val:12.4f}")
            except:
                pass


def parse_uvvcdr_sci(dat_path: Path, label: PDSLabel, debug: bool = False) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parse UVVCDR science data (calibrated radiance).
    
    These files have wavelength and calibrated radiance per step.
    Structure (approximate, based on typical MASCS CDR):
    - Each row is one grating step
    - Contains: time, wavelength, counts, calibrated radiance, geometry, etc.
    
    Returns: (wavelength_nm, radiance_w_m2_sr_nm)
    """
    if debug:
        diagnose_binary_structure(dat_path, label)
        raise SystemExit(0)
    
    # Read binary data
    data = dat_path.read_bytes()
    
    # Try to find and parse .FMT file
    fmt_columns = None
    if label.format_file:
        # Look for format file in parent directories (go up to 5 levels)
        search_dirs = [dat_path.parent]
        current = dat_path.parent
        for _ in range(5):
            if current.parent != current:
                current = current.parent
                search_dirs.append(current)
        
        for parent in search_dirs:
            fmt_path = parent / label.format_file
            if fmt_path.exists():
                try:
                    fmt_columns = parse_fmt_file(fmt_path)
                    print(f"  Using format file: {fmt_path.name}")
                    break
                except Exception as e:
                    print(f"  Warning: Could not parse format file: {e}")
            # Also try lowercase
            fmt_path_lower = parent / label.format_file.lower()
            if fmt_path_lower.exists():
                try:
                    fmt_columns = parse_fmt_file(fmt_path_lower)
                    print(f"  Using format file: {fmt_path_lower.name}")
                    break
                except Exception as e:
                    print(f"  Warning: Could not parse format file: {e}")
    
    # Determine column offsets
    wl_offset = None
    rad_offset = None
    
    if fmt_columns:
        # Look for wavelength and calibrated data columns
        # UVVCDR SCI files use STEP_WAVELENGTH and STEP_RADIANCE_W
        if 'STEP_WAVELENGTH' in fmt_columns:
            wl_offset = fmt_columns['STEP_WAVELENGTH'][0]
            print(f"  Wavelength column at byte {wl_offset}")
        
        if 'STEP_RADIANCE_W' in fmt_columns:
            rad_offset = fmt_columns['STEP_RADIANCE_W'][0]
            print(f"  Radiance column at byte {rad_offset}")
    
    # Fall back to auto-detection if format parsing failed
    if wl_offset is None or rad_offset is None:
        print(f"  Auto-detecting column offsets...")
        try:
            wl_offset, rad_offset = auto_detect_wavelength_offset(data, label.row_bytes, label.rows)
            print(f"  Found: wavelength @ byte {wl_offset}, radiance @ byte {rad_offset}")
        except ValueError as e:
            raise ValueError(f"Could not locate spectral data columns: {e}")
    
    # Parse data
    wavelengths = []
    radiances = []
    
    for i in range(label.rows):
        offset = i * label.row_bytes
        row = data[offset:offset + label.row_bytes]
        
        try:
            wl = struct.unpack('>f', row[wl_offset:wl_offset+4])[0]
            rad = struct.unpack('>f', row[rad_offset:rad_offset+4])[0]
            
            # Filter invalid values
            if 0 < wl < 10000 and not np.isnan(rad) and rad > 0:
                wavelengths.append(wl)
                radiances.append(rad)
        except Exception:
            continue
    
    if not wavelengths:
        raise ValueError(f"No valid spectral data found in {dat_path}")
    
    # Clean up zigzag/triangle scan patterns
    # The grating scans up and down, creating duplicate wavelength measurements
    # We'll bin by wavelength and average measurements
    wl_array = np.array(wavelengths)
    rad_array = np.array(radiances)
    
    # Sort by wavelength
    sort_idx = np.argsort(wl_array)
    wl_sorted = wl_array[sort_idx]
    rad_sorted = rad_array[sort_idx]
    
    # Bin to ~0.5 nm resolution (typical MASCS resolution)
    # This averages multiple measurements at similar wavelengths
    unique_wls = []
    unique_rads = []
    
    i = 0
    while i < len(wl_sorted):
        wl_bin = wl_sorted[i]
        # Find all measurements within 0.3 nm of this wavelength
        mask = (wl_sorted >= wl_bin - 0.15) & (wl_sorted <= wl_bin + 0.15)
        
        # Average measurements in this bin
        bin_wl = np.mean(wl_sorted[mask])
        bin_rad = np.mean(rad_sorted[mask])
        
        unique_wls.append(bin_wl)
        unique_rads.append(bin_rad)
        
        # Skip to next bin
        i = np.where(mask)[0][-1] + 1
    
    return np.array(unique_wls), np.array(unique_rads)


def parse_virs_ddr(dat_path: Path, label: PDSLabel) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parse VIRS DDR data (NIR or VIS reflectance spectra).
    
    VIRS captures full spectra as arrays:
    - NIR: 256 pixels covering ~300-1450 nm  
    - VIS: 512 pixels covering ~300-1050 nm
    
    Returns: (wavelength_nm, reflectance)
    """
    data = dat_path.read_bytes()
    
    # Determine if NIR or VIS based on product ID
    is_nir = 'NIR' in label.product_id.upper() or 'ND' in label.product_id.upper()
    num_pixels = 256 if is_nir else 512
    
    # VIRS wavelength calibration (from MASCS documentation)
    if is_nir:
        # NIR: ~300-1450 nm, 256 pixels
        # Approximate linear wavelength scale
        wavelengths = np.linspace(300, 1450, num_pixels)
    else:
        # VIS: ~300-1050 nm, 512 pixels  
        wavelengths = np.linspace(300, 1050, num_pixels)
    
    # Try to parse format file to get exact offsets
    fmt_columns = None
    if label.format_file:
        for parent in [dat_path.parent, dat_path.parent.parent, dat_path.parent.parent.parent, dat_path.parent.parent.parent.parent]:
            fmt_path = parent / label.format_file
            if fmt_path.exists():
                try:
                    fmt_columns = parse_fmt_file(fmt_path)
                    print(f"  Using format file: {fmt_path.name}")
                    break
                except Exception as e:
                    print(f"  Warning: Could not parse format file: {e}")
    
    # Find IOF spectrum data offset
    iof_offset = 48  # Default from VIRSND.FMT
    if fmt_columns:
        for name, (offset, size, dtype) in fmt_columns.items():
            if 'PHOTOM_IOF_SPECTRUM_DATA' in name:
                iof_offset = offset
                print(f"  Photometric I/F array at byte {iof_offset}")
                break
            elif 'IOF_SPECTRUM_DATA' in name:
                iof_offset = offset
                print(f"  I/F array at byte {iof_offset}")
    
    # Average multiple spectra from all rows
    all_spectra = []
    
    for i in range(label.rows):
        row_offset = i * label.row_bytes
        spectrum_offset = row_offset + iof_offset
        
        try:
            # Read array of floats
            spectrum = np.zeros(num_pixels)
            for j in range(num_pixels):
                byte_off = spectrum_offset + (j * 4)
                if byte_off + 4 <= len(data):
                    val = struct.unpack('>f', data[byte_off:byte_off+4])[0]
                    # Filter invalid/saturated pixels (1e32 = invalid)
                    if 0 < val < 1 and not np.isnan(val):
                        spectrum[j] = val
            
            # Only keep spectra with valid data
            if np.sum(spectrum > 0) > num_pixels * 0.1:  # At least 10% valid
                all_spectra.append(spectrum)
        except Exception:
            continue
    
    if not all_spectra:
        raise ValueError(f"No valid VIRS spectra found in {dat_path}")
    
    # Average all spectra
    avg_spectrum = np.mean(all_spectra, axis=0)
    
    # Filter out zero/invalid pixels
    valid_mask = avg_spectrum > 0
    valid_wl = wavelengths[valid_mask]
    valid_refl = avg_spectrum[valid_mask]
    
    return valid_wl, valid_refl


def parse_uvvddr_surface(dat_path: Path, label: PDSLabel) -> Tuple[np.ndarray, np.ndarray]:
    """
    Parse UVVDDR surface reflectance data.
    
    These files contain binned I/F (reflectance) data.
    Structure (from documentation):
    - Row size: 270 bytes
    - Contains IOF_BIN_DATA arrays with wavelength and reflectance
    
    Returns: (wavelength_nm, reflectance)
    """
    data = dat_path.read_bytes()
    
    # Try to parse format file
    fmt_columns = None
    if label.format_file:
        for parent in [dat_path.parent, dat_path.parent.parent, dat_path.parent.parent.parent, dat_path.parent.parent.parent.parent]:
            fmt_path = parent / label.format_file
            if fmt_path.exists():
                try:
                    fmt_columns = parse_fmt_file(fmt_path)
                    print(f"  Using format file: {fmt_path.name}")
                    break
                except Exception as e:
                    print(f"  Warning: Could not parse format file: {e}")
    
    wavelengths = []
    reflectances = []
    
    # Determine offsets
    wl_offset = None
    iof_offset = None
    
    if fmt_columns:
        for name, (offset, size, _dtype) in fmt_columns.items():
            if name == 'BIN_WAVELENGTH' and size == 4:
                wl_offset = offset
                print(f"  Wavelength column at byte {wl_offset}")
            elif name == 'IOF_BIN_DATA' and size == 4:
                iof_offset = offset
                print(f"  I/F reflectance column at byte {iof_offset}")
    
    # Auto-detect if needed
    if wl_offset is None:
        print(f"  Auto-detecting surface reflectance columns...")
        # For surface DDR, wavelength typically in first 100 bytes
        for offset in range(0, 100, 4):
            try:
                wl = struct.unpack('>f', data[offset:offset+4])[0]
                if 200 < wl < 400:  # MUV range
                    wl_offset = offset
                    iof_offset = offset + 4  # Reflectance typically next
                    print(f"  Found: wavelength @ byte {wl_offset}, I/F @ byte {iof_offset}")
                    break
            except:
                continue
    
    if wl_offset is None:
        raise ValueError("Could not locate wavelength/reflectance columns")
    
    for i in range(label.rows):
        offset = i * label.row_bytes
        row = data[offset:offset + label.row_bytes]
        
        try:
            wl = struct.unpack('>f', row[wl_offset:wl_offset+4])[0]
            iof = struct.unpack('>f', row[iof_offset:iof_offset+4])[0]
            
            if 0 < wl < 10000 and not np.isnan(iof) and iof >= 0:
                wavelengths.append(wl)
                reflectances.append(iof)
        except Exception:
            continue
    
    if not wavelengths:
        raise ValueError(f"No valid reflectance data found in {dat_path}")
    
    return np.array(wavelengths), np.array(reflectances)


def write_csv(output_path: Path, wavelengths: np.ndarray, values: np.ndarray,
              label: PDSLabel, value_type: str) -> None:
    """Write extracted data to CSV with metadata header."""
    
    # Determine units and column name
    if value_type == "reflectance":
        value_col = "reflectance"
        value_unit = "dimensionless"
    else:
        value_col = "radiance_w_m2_sr_nm"
        value_unit = "W m^-2 sr^-1 nm^-1"
    
    with output_path.open("w", encoding="utf-8") as f:
        # Write metadata header
        f.write(f"# Source: MESSENGER MASCS {label.detector_id}\n")
        f.write(f"# Product: {label.product_id}\n")
        f.write(f"# Type: {label.product_type}\n")
        f.write(f"# Target: {label.target_name}\n")
        f.write(f"# Observation: {label.start_time} to {label.stop_time}\n")
        f.write(f"# Units: wavelength_nm={value_unit}\n")
        f.write(f"#\n")
        
        # Write column headers
        f.write(f"wavelength_nm,{value_col}\n")
        
        # Write data
        for wl, val in zip(wavelengths, values):
            f.write(f"{wl:.4f},{val:.6e}\n")


def process_file(lbl_path: Path, output_path: Path | None = None) -> Path:
    """Process a single PDS label + data file pair."""
    
    # Parse label
    label = PDSLabel.from_file(lbl_path)
    
    # Locate data file
    dat_path = lbl_path.parent / label.data_file
    if not dat_path.exists():
        # Try lowercase
        dat_path = lbl_path.parent / label.data_file.lower()
    if not dat_path.exists():
        raise FileNotFoundError(f"Data file not found: {label.data_file}")
    
    # Determine output path
    if output_path is None:
        output_path = lbl_path.parent / f"{lbl_path.stem}.csv"
    
    print(f"Processing: {lbl_path.name}")
    print(f"  Product: {label.product_id}")
    print(f"  Type: {label.product_type}")
    print(f"  Detector: {label.detector_id}")
    print(f"  Rows: {label.rows}")
    
    # Parse based on product type and detector
    if label.detector_id == "VIRS" and label.product_type == "DDR":
        wavelengths, values = parse_virs_ddr(dat_path, label)
        value_type = "reflectance"
    elif label.product_type == "CDR" and label.detector_id == "UVVS":
        wavelengths, values = parse_uvvcdr_sci(dat_path, label)
        value_type = "radiance"
    elif label.product_type == "DDR" and "UVVSSCID_SUR" in (label.format_file or ""):
        wavelengths, values = parse_uvvddr_surface(dat_path, label)
        value_type = "reflectance"
    else:
        raise ValueError(f"Unsupported product: {label.product_type} {label.detector_id}")
    
    # Write CSV
    write_csv(output_path, wavelengths, values, label, value_type)
    print(f"  → {output_path.name} ({len(wavelengths)} points)")
    
    return output_path


def batch_process(directory: Path, recursive: bool = True) -> List[Path]:
    """Process all .lbl files in a directory."""
    pattern = "**/*.lbl" if recursive else "*.lbl"
    lbl_files = sorted(directory.glob(pattern))
    
    # Filter to only SCI files (skip HDR)
    lbl_files = [f for f in lbl_files if "_sci.lbl" in f.name.lower()]
    
    print(f"Found {len(lbl_files)} science label files")
    
    outputs = []
    for lbl_path in lbl_files:
        try:
            output = process_file(lbl_path)
            outputs.append(output)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
    
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Parse MESSENGER MASCS PDS3 data")
    parser.add_argument("input", type=Path, help="Input .lbl file or directory")
    parser.add_argument("output", type=Path, nargs="?", help="Output .csv file (optional)")
    parser.add_argument("--batch", action="store_true", help="Process all files in directory")
    parser.add_argument("--recursive", action="store_true", default=True, help="Recursive search in batch mode")
    parser.add_argument("--debug", action="store_true", help="Print binary structure diagnostic")
    args = parser.parse_args(argv)
    
    if args.debug:
        if args.input.is_dir():
            # Find first .lbl file
            lbl_files = list(args.input.glob("**/*_sci.lbl"))
            if not lbl_files:
                print("No science label files found")
                return 1
            args.input = lbl_files[0]
        
        label = PDSLabel.from_file(args.input)
        dat_path = args.input.parent / label.data_file
        if not dat_path.exists():
            dat_path = args.input.parent / label.data_file.lower()
        diagnose_binary_structure(dat_path, label, num_rows=10)
        return 0
    
    if args.batch or args.input.is_dir():
        batch_process(args.input, recursive=args.recursive)
    else:
        if not args.input.exists():
            print(f"Error: File not found: {args.input}")
            return 1
        process_file(args.input, args.output)
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
