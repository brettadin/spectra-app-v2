"""PDS3 label parser for multi-column spectral data.

Parses .lbl files that describe the structure of companion .tab files,
extracting column definitions, target names, and metadata for proper ingestion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PDSColumn:
    """Column definition from a PDS label."""
    
    name: str
    column_number: int
    unit: str | None
    data_type: str
    start_byte: int
    bytes: int
    format: str
    description: str


@dataclass
class PDSLabel:
    """Parsed PDS3 label metadata."""
    
    version_id: str
    data_file: str
    target_names: list[str]
    instrument_name: str
    instrument_host: str
    start_time: str | None
    stop_time: str | None
    product_name: str
    note: str | None
    columns: list[PDSColumn]
    rows: int
    row_bytes: int
    
    def get_wavelength_column(self) -> PDSColumn | None:
        """Return the wavelength column (prefer air wavelength over vacuum)."""
        # Look for air wavelength first, then vacuum
        for col in self.columns:
            if "air" in col.name.lower() and "wavelength" in col.name.lower():
                return col
        for col in self.columns:
            if "wavelength" in col.name.lower():
                return col
        return None
    
    def get_target_columns(self) -> list[tuple[str, PDSColumn]]:
        """Return list of (target_name, column) for each spectral data column.
        
        Skips wavelength and absorption coefficient columns, returning only
        the actual target measurement columns (albedo, flux, etc.).
        """
        skip_keywords = {"wavelength", "absorption", "coefficient", "methane"}
        targets = []
        
        for col in self.columns:
            name_lower = col.name.lower()
            # Skip non-target columns
            if any(kw in name_lower for kw in skip_keywords):
                continue
            
            # Extract target name from column name (e.g., "JUPITER ALBEDO" -> "Jupiter")
            parts = col.name.split()
            if parts:
                target = parts[0].capitalize()
                targets.append((target, col))
        
        return targets


def parse_pds_label(label_path: Path) -> PDSLabel | None:
    """Parse a PDS3 .lbl file and return structured metadata.
    
    Returns None if the file is not a valid PDS3 label or cannot be parsed.
    """
    if not label_path.exists():
        return None
    
    try:
        content = label_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None
    
    # Check for PDS3 marker
    if "PDS_VERSION_ID" not in content or "PDS3" not in content:
        return None
    
    # Extract basic metadata
    version_id = _extract_value(content, "PDS_VERSION_ID") or "PDS3"
    data_file = _extract_value(content, r'\^TABLE') or ""
    data_file = data_file.strip('"')
    
    # Extract target names (can be a list)
    target_raw = _extract_value(content, "TARGET_NAME") or ""
    target_names = _parse_target_list(target_raw)
    
    instrument_name = _extract_value(content, "INSTRUMENT_NAME") or ""
    instrument_host = _extract_value(content, "INSTRUMENT_HOST_NAME") or ""
    start_time = _extract_value(content, "START_TIME")
    stop_time = _extract_value(content, "STOP_TIME")
    product_name = _extract_value(content, "PRODUCT_NAME") or ""
    
    # Extract NOTE field (may span multiple lines)
    note = _extract_multiline_value(content, "NOTE")
    
    # Parse TABLE object - extract ROWS and ROW_BYTES from within TABLE block
    table_match = re.search(r'OBJECT\s*=\s*TABLE\s*(.*?)\s*END_OBJECT\s*=\s*TABLE', 
                           content, re.DOTALL | re.IGNORECASE)
    if table_match:
        table_block = table_match.group(1)
        rows = int(_extract_value(table_block, "ROWS") or "0")
        row_bytes = int(_extract_value(table_block, "ROW_BYTES") or "0")
    else:
        rows = 0
        row_bytes = 0
    
    # Parse COLUMN objects
    columns = _parse_columns(content)
    
    return PDSLabel(
        version_id=version_id,
        data_file=data_file,
        target_names=target_names,
        instrument_name=instrument_name,
        instrument_host=instrument_host,
        start_time=start_time,
        stop_time=stop_time,
        product_name=product_name,
        note=note,
        columns=columns,
        rows=rows,
        row_bytes=row_bytes,
    )


def _extract_value(content: str, key: str) -> str | None:
    """Extract a simple KEY = VALUE pair from PDS label content."""
    # Match KEY = VALUE (handle quoted strings and unquoted values)
    pattern = rf'{key}\s*=\s*([^\n]+)'
    match = re.search(pattern, content)
    if not match:
        return None
    value = match.group(1).strip()
    # Remove trailing comments and clean up
    value = value.split('/')[0].strip()  # Remove inline comments
    value = value.strip('"').strip()
    return value if value else None


def _extract_multiline_value(content: str, key: str) -> str | None:
    """Extract a multiline quoted value like NOTE = \"...\"."""
    pattern = rf'{key}\s*=\s*"([^"]*(?:\n[^"]*)*)"'
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None
    # Clean up the multiline string
    value = match.group(1)
    # Remove excessive whitespace while preserving structure
    value = re.sub(r'\s+', ' ', value).strip()
    return value if value else None


def _parse_target_list(target_raw: str) -> list[str]:
    """Parse TARGET_NAME which can be single value or {A, B, C} list."""
    target_raw = target_raw.strip()
    if not target_raw:
        return []
    
    # Check for curly brace list syntax
    if target_raw.startswith('{') and target_raw.endswith('}'):
        # Extract items between braces
        inner = target_raw[1:-1]
        targets = [t.strip().capitalize() for t in inner.split(',')]
        return [t for t in targets if t]
    
    # Single target
    return [target_raw.capitalize()] if target_raw else []


def _parse_columns(content: str) -> list[PDSColumn]:
    """Extract all COLUMN objects from the PDS label."""
    columns = []
    
    # Find all OBJECT = COLUMN ... END_OBJECT = COLUMN blocks
    column_pattern = r'OBJECT\s*=\s*COLUMN\s*(.*?)\s*END_OBJECT\s*=\s*COLUMN'
    column_blocks = re.findall(column_pattern, content, re.DOTALL | re.IGNORECASE)
    
    for block in column_blocks:
        try:
            name = _extract_value(block, "NAME") or "Unknown"
            col_num = int(_extract_value(block, "COLUMN_NUMBER") or "0")
            unit = _extract_value(block, "UNIT")
            if unit and unit.upper() == "NULL":
                unit = None
            data_type = _extract_value(block, "DATA_TYPE") or "ASCII_REAL"
            start_byte = int(_extract_value(block, "START_BYTE") or "1")
            num_bytes = int(_extract_value(block, "BYTES") or "0")
            fmt = _extract_value(block, "FORMAT") or ""
            description = _extract_multiline_value(block, "DESCRIPTION") or ""
            
            columns.append(PDSColumn(
                name=name,
                column_number=col_num,
                unit=unit,
                data_type=data_type,
                start_byte=start_byte,
                bytes=num_bytes,
                format=fmt,
                description=description,
            ))
        except (ValueError, AttributeError):
            # Skip malformed column definitions
            continue
    
    # Sort by column number
    columns.sort(key=lambda c: c.column_number)
    return columns
