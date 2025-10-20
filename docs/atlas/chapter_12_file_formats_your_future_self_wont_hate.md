# Chapter 12 — File Formats Your Future Self Won’t Hate

> **Purpose.** Define lossless, reproducible, and future‑proof file formats for spectra, features, calibration artifacts, and reports. Provide schema conventions, examples, and validation checks so the app can read/write without brittle hacks.
>
> **Scope.** 1D spectra across modalities (atomic/UV–Vis, FTIR/ATR, Raman, fluorescence) and astrophysical spectra. Formats considered: CSV/TSV, JSON/JSON‑Lines, JCAMP‑DX, HDF5, Apache Parquet, FITS (astro). Also defines sidecar manifests and graph exports.
>
> **Path notice.** Filenames and directories below are **placeholders** and must be resolved by the app’s path resolver at runtime. Do **not** hardcode. Tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]` are variables.

---

## 0. Design rules (non‑negotiable)
1. **Raw is sacred.** Store vendor‑native raw exactly once. Never alter in place.
2. **Canonical arrays.** One canonical axis per modality (Ch. 5). Views are computed and never saved as new ground truth.
3. **Uncertainty and masks.** Every spectrum can carry optional `uncertainty` and `mask` arrays aligned to the data length.
4. **Resolution honesty.** Store LSF/ILS kernels and target FWHM used for overlays. Don’t bake convolution into raw arrays.
5. **UTF‑8 only.** Text files are UTF‑8 with `\n` line endings; JSON is canonicalized (sorted keys) before hashing.
6. **Units explicit.** Units are strings following VOUnits/UDUNITS style; FITS uses `CUNIT*`/`BUNIT`; JCAMP uses `##XUNITS`/`##YUNITS`.
7. **Time is ISO‑8601.** Timestamps in UTC or with explicit offset. No local‑time orphan strings.

---

## 1. What a 1D spectrum must contain

Minimum fields regardless of container:
```
axis: float64[N]          # canonical (nm or cm^-1 or shift cm^-1)
intensity: float64[N]
uncertainty: float64[N]?  # optional per‑point 1σ
mask: uint8[N]?           # 1=masked/bad, 0=good
meta: {
  modality, unit, medium (air|vacuum?), lambda0_nm? (Raman),
  instrument_id, lsf_ref?, response_ref?, calibration_refs[],
  environment: {T_K?, P_Pa?, RH?},
  constants: {c: CODATA‑XXXX, h: CODATA‑XXXX},
  source: {vendor_file?, source_id@version?}
}
```

---

## 2. Format selection matrix

| Use case | Preferred | Also acceptable | Notes |
|---|---|---|---|
| Teaching/simple interchange | **CSV/TSV + JSON sidecar** | JCAMP‑DX | CSV is human‑friendly; sidecar carries units and meta to avoid header wars. |
| Vibrational spectroscopy libraries | **JCAMP‑DX** | HDF5/Parquet | JCAMP is widely used for IR/Raman; stick to NTUPLES for metadata richness. |
| Long‑term campus archive | **HDF5** | Parquet | Hierarchical, chunked, compressible, self‑describing; great for arrays and kernels. |
| Analytics table store | **Parquet** | HDF5 | Columnar, compressed, splittable; nice for feature tables and line lists. |
| Astrophysical spectra | **FITS** | HDF5 | FITS + WCS is standard; keep header provenance. |
| Evidence/lineage graphs | **JSON** | GraphML | JSON keeps it simple; one file per graph. |

> If you must export plots, use **SVG/PNG** alongside data, never as the only artifact.

---

## 3. CSV/TSV + JSON sidecar

**Data file** (CSV):
```
# axis_unit=nm, intensity_unit=counts, medium=vacuum, modality=uvvis
axis,intensity,uncertainty,mask
400.000,1234.0,15.2,0
400.500,1201.2,15.1,0
...
```
- Decimal point is `.` regardless of locale.
- Missing values: `NaN` (IEEE) allowed in numeric columns; masks indicate exclusion.

**Sidecar** `sessions/[SESSION_ID]/[MODALITY]/processed/[NAME].meta.json`:
```json
{
  "modality": "uvvis",
  "axis_unit": "nm",
  "intensity_unit": "counts",
  "medium": "vacuum",
  "lambda0_nm": null,
  "instrument_id": "[INSTRUMENT_ID]",
  "lsf_ref": "sessions/[SESSION_ID]/cal/lsf_[YYYYMMDD].h5",
  "response_ref": null,
  "calibration_refs": ["sessions/[SESSION_ID]/cal/lamp_Ne_[YYYYMMDD].csv"],
  "environment": {"T_K": 296.2, "pressure_Pa": 101325},
  "constants": {"c": "CODATA-20xx", "h": "CODATA-20xx"},
  "provenance": {"created_by": "app@[SEMVER]", "git": "commit:abc123"}
}
```

**Pros.** Easy to inspect, diff, and teach. **Cons.** No chunking; large files are slow; metadata split across files.

---

## 4. JCAMP‑DX (IR/Raman)

**Headers** (minimal):
```
##TITLE= [SAMPLE_ID] Raman spectrum
##JCAMP-DX= 5.00
##DATA TYPE= RAMAN SPECTRUM
##XUNITS= 1/CM
##YUNITS= RELATIVE INTENSITY
##FIRSTX= 100.0
##LASTX= 3500.0
##NPOINTS= 3401
##XFACTOR= 1.0
##YFACTOR= 1.0
##XYDATA= (X++(Y..Y))
...
##END=
```
- Prefer **NTUPLES** for richer metadata (laser λ, resolution, baseline model, LSF).
- Do not store smoothed data without the unsmoothed version and parameters.

**Pros.** Community standard in IR/Raman; readable. **Cons.** Inconsistent vendor dialects; limited arrays beyond XY.

---

## 5. HDF5 (campus archive default)

**Group layout** (example):
```
/ (root)
  attrs: {creator: "SpectraApp", version: "[SEMVER]"}
  /raw
    /uvvis
      axis [float64]
      intensity [float64]
      uncertainty [float64]?  # optional
      mask [uint8]?
      attrs: {unit: "nm", medium: "vacuum", instrument_id: "..."}
  /processed
    /uvvis
      view_0001
        axis [...]
        intensity [...]
        attrs: {view: "response_corrected", lsf_ref: "/cal/lsf"}
  /cal
    lsf
      kernel [float64]
      attrs: {kind: "gaussian", fwhm: 6.0, unit: "cm-1"}
    response
      axis [float64]
      rsrf [float64]
  /meta
    manifest_json [utf8]
```

**Compression/chunking**
- Use **zstd** or **gzip**; chunk around 64–512 kB per dataset; align chunks with typical view windows to accelerate IO.
- Store checksums in file attributes (`sha256` of raw arrays) and in the session manifest (Ch. 8).

**Pros.** Hierarchical, fast, single‑file bundle. **Cons.** Binary; not diff‑friendly in Git.

---

## 6. Apache Parquet (analytics/lines/features)

**Use for**: large line lists (HITRAN‑style), feature tables, identification outputs.

**Table schema** (example `features.parquet`):
```
feature_id: string
modality: string
center: double
center_unc: double
fwhm: double
intensity: double
annotations: list<string>
links.spectrum_ref: string
```
- Snappy or ZSTD compression; enable dictionary encoding for categorical columns.
- Partition by `modality` or `session_id` for scalable queries.

**Pros.** Columnar, splittable, great for Spark/DuckDB. **Cons.** Not ideal for long 1D arrays with tight coupling.

---

## 7. FITS (astronomical)

**Primary HDU**: image or table of `flux` with axis WCS in header.

**Key WCS header cards**:
```
SIMPLE  = T
BITPIX  = -64                  / float64
NAXIS   = 1
NAXIS1  = N
CTYPE1  = 'WAVE'               / or 'FREQ', 'VRAD'
CUNIT1  = 'nm'                 / or 'Angstrom', 'Hz', 'm/s'
CRVAL1  = 500.0
CRPIX1  = 1
CDELT1  = 0.05
BUNIT   = 'erg s-1 cm-2 A-1'   / flux unit
HIERARCH LSF_FWHM = 0.2        / nm at 500 nm
HIERARCH MEDIUM   = 'vacuum'
...
```
- Include `EXTNAME='UNCERTAINTY'` for 1σ arrays or use a binary table HDU.
- Preserve pipeline/provenance keywords and data release versions.

**Pros.** Community standard with WCS; rich headers. **Cons.** Header discipline required; units vary by archive.

---

## 8. Evidence and lineage graphs (JSON)

**Evidence graph** `graphs/[SESSION_ID]/[DATASET_ID]/evidence.json`:
```json
{
  "graph_id": "[UUID]",
  "nodes": [{"id": "feat:...", "type": "feature"}, {"id": "hyp:...", "type": "hypothesis"}],
  "edges": [{"from": "feat:...", "to": "hyp:...", "relation": "supports", "weight": 0.7}],
  "provenance": {"app_build": "[SEMVER]", "created": "[ISO-8601]"}
}
```

**Lineage graph** (Ch. 8) follows similar structure with `raw|view|cal` node kinds.

---

## 9. Conversion and IO APIs (pseudocode)

```python
def load_bundle(path_or_dir) -> SpectrumBundle: ...

def save_bundle(bundle, path_or_dir, fmt: Literal["hdf5","csv+json","jcamp","fits","parquet"]) -> None: ...

def convert(bundle, target_fmt, policy={"preserve_uncertainty": True, "preserve_masks": True}) -> Path: ...
```
- **Policy:** forbid lossy conversion when it would drop uncertainty or masks unless user overrides with explicit `allow_loss=True`.

---

## 10. Validation checks (must ship)

- **Schema validation** for JSON sidecars (JSON Schema); **header validation** for FITS (required cards present; unit sanity).
- **Round‑trip tests**: CSV+JSON ↔ HDF5; HDF5 ↔ Parquet for tables; Raman λ‑space ↔ shift space (Ch. 5) within tolerances.
- **Hash checks**: recompute SHA‑256 after save; compare to recorded.
- **Precision**: axis arrays float64; forbid silent float32 down‑cast unless explicitly requested.

---

## 11. Naming, extensions, and folders

- **Never** hardcode storage locations. The path resolver maps tokens to actual locations at runtime.
- Suggested names:
```
sessions/[SESSION_ID]/[MODALITY]/raw/[SAMPLE_ID]_[MODALITY]_raw.[vendor_ext]
sessions/[SESSION_ID]/[MODALITY]/processed/[SAMPLE_ID]_[VIEW].csv
sessions/[SESSION_ID]/cal/response_[YYYYMMDD].h5
reports/[SESSION_ID]/[DATASET_ID]/report_[YYYYMMDD].pdf
rubrics/[YYYYMMDD]/rubric.json
```

---

## 12. Edge cases and traps

- **NaN/Inf handling:** store as IEEE in binary formats; CSV uses literal `NaN`; masks mark unusable regions.
- **Locale hell:** decimal separator is `.`; thousands separators forbidden.
- **Unicode normalization:** NFC for all strings; filenames restricted to ASCII subset plus `_` and `-` for portability.
- **Line endings:** `\n` only; normalize on ingest.
- **Giant arrays:** chunk HDF5 datasets; stream CSV writes; consider splitting by wavelength blocks with index.
- **JCAMP dialects:** validate header keys; reject if units missing or wrong case; convert to internal canonical on load.

---

## 13. Worked mini‑examples

### 13.1 Minimal Raman HDF5
```
/processed/raman/sample_001
  axis [cm^-1]: 100..3500 (float64)
  intensity: [...]
  uncertainty: [...]
  attrs: {lambda0_nm: 785.02, unit: "cm-1", instrument_id: "RAMAN‑01"}
/cal/lsf: kernel + attrs
/meta/manifest_json: text
```

### 13.2 UV–Vis CSV + sidecar
```
# axis_unit=nm, intensity_unit=absorbance, path_length_cm=1.000
axis,intensity
350.0,0.005
...
```
Sidecar contains solvent, pH, slit bandwidth, scan rate.

### 13.3 FITS 1D spectrum with uncertainty
- HDU0: flux array
- HDU1: uncertainty array (same length)
- Header contains WCS cards and `BUNIT`, `HIERARCH LSF_FWHM`, `HIERARCH RESPONSE_ID`.

---

## 14. References (anchor list)
- **JCAMP‑DX** specifications for spectroscopy data exchange.
- **HDF5** documentation (The HDF Group).
- **Apache Parquet** format specification.
- **FITS** standard and **WCS** spectral axis conventions.
- **JSON Schema** draft specifications.
- **VOUnits/UDUNITS** for consistent unit strings.

> Include exact versions and access dates in the Sources chapter (Ch. 32). Replace placeholder tokens and record the chosen compression and chunking policies in the session manifest (Ch. 8).

