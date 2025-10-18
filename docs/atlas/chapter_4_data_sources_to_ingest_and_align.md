# Chapter 4 — Data Sources to Ingest and Align

> **Purpose.** Catalog authoritative datasets and archives for elemental and molecular spectroscopy, specify ingestion adapters and metadata contracts, and define how external data are aligned with campus‑acquired spectra for comparison and prediction.
>
> **Scope.** Lab datasets, evaluated reference line/band lists, spectral libraries (minerals, compounds, stars), and astronomical archives. Includes licensing, citation, caching, and alignment procedures.
>
> **Path notice.** File and folder names are **placeholders**. All paths must be resolved by the application’s path resolver at runtime. Tokens like `[DATASET_ID]`, `[SESSION_ID]`, `[YYYYMMDD]`, `[MODALITY]` are variables.

---

## 0. Source taxonomy

1. **Lab‑generated spectra** (campus instruments)
   - Raw and processed outputs from atomic emission/AAS, FTIR/ATR, Raman, UV–Vis, fluorescence.
   - Stored in `sessions/[SESSION_ID]/...` with manifests (see Chapter 2 and 8).

2. **Evaluated atomic line databases**
   - NIST Atomic Spectra Database (ASD): wavelengths, energy levels, transition probabilities.
   - Other vetted catalogs noted in Appendix A; always check licensing and version.

3. **Molecular line/cross‑section databases**
   - HITRAN/HITEMP: high‑resolution line parameters and cross sections for gases.
   - ExoMol: extensive molecular line lists for high‑T applications.
   - JPL/CDMS catalogs: rotational spectroscopy for interstellar molecules.

4. **Spectral libraries (materials/minerals/organics)**
   - RRUFF: Raman + XRD + chemistry for minerals.
   - IRTF/SpeX libraries (stellar/solar system reflectance), X‑shooter Spectral Library (XSL), other vetted sets.

5. **Astrophysical archives and standards**
   - CALSPEC (HST standards), MAST (HST/JWST), SDSS, ESO, NASA PDS nodes, solar irradiance references (e.g., TSIS‑1 HSRS).

6. **Instrument response/standards**
   - Lamp line sets (Hg/Ne/Xe/He), polystyrene film (IR), silicon Raman 520.7 cm⁻¹, holmium oxide filters (UV–Vis). Used for calibration alignment.

---

## 1. Source registry schema (master index)

Maintain a machine‑readable "source registry" that enumerates every external dataset with access, licensing, and adapter info.

```json
{
  "source_id": "hitran:2020:CO2",
  "name": "HITRAN 2020 CO2 lines",
  "type": "molecular_lines",
  "uri": "https://[HITRAN_ENDPOINT]",
  "access_method": "http|https|ftp|local_cache",
  "auth": {"type": "none|token|key", "env_var": "HITRAN_API_KEY"},
  "license": "HITRAN-terms",
  "version": "2020.1",
  "citation": {
    "authors": ["Gordon, I. E.", "et al."],
    "title": "The HITRAN2020 molecular spectroscopic database",
    "journal": "JQSRT",
    "doi": "10.1016/j.jqsrt.2021.107949",
    "accessed": "[YYYY-MM-DD]"
  },
  "content": {"species": ["CO2"], "format": "txt|par|hdf5", "columns": ["nu", "S", "Aij", "E"], "units": {"nu": "cm^-1"}},
  "adapter": {
    "parser": "hitran_lines_v2020",
    "axis": {"canonical": "cm^-1"},
    "lsf": null,
    "post": ["pressure_broadening_map", "temperature_partition_function"]
  },
  "cache": {"strategy": "etag+checksum", "path": "cache/sources/hitran/2020/CO2/"},
  "validation": {"row_count_min": 1, "sha256": "[OPTIONAL]"}
}
```

All registry entries must include: `source_id`, `license`, `version`, `citation`, `adapter.parser`, `axis.canonical`, and `cache.strategy`.

---

## 2. Ingestion adapters (design and contracts)

### 2.1 Adapter responsibilities
- **Download/Load**: fetch remote or local files with retry, checksum, and etag support; respect rate limits and robots policies.
- **Parse**: convert to internal tables using strict schemas; raise on missing units or corrupted headers.
- **Normalize**: map to canonical axis and units without overwriting original values.
- **Annotate**: attach `provenance` (source_id, version, citation, access date, checksum) and `transforms_applied`.
- **Validate**: run dataset‑specific sanity checks (e.g., monotonic axis, no negative intensities unless allowed, expected columns present).

### 2.2 Adapter interface (pseudo‑signature)
```
load_dataset(source_id: str, selector: dict) -> DatasetBundle

DatasetBundle = {
  "raw": [FileRef...],
  "tables": {"lines": DataFrame?, "spectrum": DataFrame?},
  "meta": {"axis": "nm|cm^-1|eV", "units": {...}, "provenance": {...}},
  "quality": {"row_count": int, "warnings": [str]}
}
```

### 2.3 Alignment hooks
- **Instrument response**: supply response curves for standards (e.g., CALSPEC) to convert counts→flux.
- **LSF/Resolution**: if provided, store as separate kernel metadata; do not conflate with spectrum.
- **Velocity frames**: astronomical data must track frame (topocentric, barycentric) and radial‑velocity corrections.

---

## 3. Alignment strategies by source class

1. **Line lists (atomic/molecular)**
   - Treat wavelengths/wavenumbers as ideal laboratory positions. When matching, convolve expected transitions with instrument LSF and apply environmental models (temperature/pressure broadening).
   - Maintain species/isotope/transition quantum numbers where available.

2. **Spectral libraries (lab materials)**
   - Use their native resolution; for overlays, convolve campus spectra down or upsample libraries with caution.
   - For Raman libraries, record **laser wavelength** used for reference and convert to Raman shift for comparison.

3. **Astrophysical archives**
   - Apply barycentric correction to templates, not to raw data. Match instrument response and LSF before cross‑correlation. Track data release (e.g., SDSS DR#, JWST pipeline version).

4. **Solar/standard stars (CALSPEC/TSIS‑1)**
   - Use for absolute flux calibration or sanity checks; preserve uncertainty arrays.

---

## 4. Reliability and trust scoring of sources

Assign each source a **trust tier** based on curation level, versioning, and uncertainty reporting.

- **Tier A (authoritative/evaluated)**: NIST ASD, HITRAN/HITEMP, CALSPEC.
- **Tier B (peer‑reviewed libraries)**: RRUFF, IRTF/SpeX, XSL.
- **Tier C (community/derived)**: community spectral workbenches; use cautiously, require cross‑validation.

Trust tier feeds into identification priors and report footnotes.

---

## 5. Caching, version pinning, and reproducibility

- **Cache layout**: `cache/sources/[PROVIDER]/[VERSION]/[DATASET_ID]/...`
- **Checksums**: store SHA‑256 for each file; verify on load. Keep `ETag`/`Last‑Modified` for HTTP.
- **Pinning**: record `source_id@version` in the project manifest. Inference reports list exact versions and access dates.
- **Update policy**: allow side‑by‑side versions (e.g., HITRAN2020 and HITRAN2024) and require explicit selection or migration script.

---

## 6. Example ingestion recipes

### 6.1 NIST ASD (atomic lines)
- **Selector**: element, ion stage, wavelength range.
- **Parse**: columns → wavelength (nm), A‑value, upper/lower term, uncertainty.
- **Align**: convolve with instrument LSF for matching; apply air/vacuum conversions if needed; keep index of lines used for wavelength calibration checks.

### 6.2 HITRAN CO₂ lines
- **Selector**: species=CO2, range=[2000, 2600] cm⁻¹, T/P conditions for cross‑sections.
- **Parse**: line parameters into table; compute temperature‑dependent intensities via partition functions.
- **Align**: produce synthetic Voigt profiles at instrument resolution for comparison to gas‑cell FTIR.

### 6.3 RRUFF Raman spectrum
- **Selector**: mineral name or RRUFF ID.
- **Parse**: wavelength‑based spectrum and laser λ; convert to Raman shift.
- **Align**: match low‑frequency lattice modes; compare with campus Raman at matched resolution.

### 6.4 CALSPEC standard star
- **Selector**: star ID; fetch flux vs wavelength with uncertainties.
- **Align**: fold through instrument response to calibrate counts→flux; store response curve version.

### 6.5 SDSS/ESO stellar spectrum
- **Selector**: object ID or sky coordinates; fetch FITS spectrum with header WCS, resolution, pipeline version.
- **Align**: continuum‑normalize; set radial‑velocity frame; cross‑correlate with stellar templates to derive \(v_r\) and spectral type consistency.

### 6.6 TSIS‑1 HSRS solar irradiance
- **Use**: reference for solar spectral comparisons and as an illumination standard for reflectance calculations.
- **Align**: ensure consistent irradiance units; document temporal coverage/date.

---

## 7. Licensing and citation policy

- Every dataset must include `license`, `terms_url` (if applicable), and a full `citation` block.
- Some sources require registration or restricted redistribution (e.g., certain atomic databases, VALD). Do not mirror restricted content; cache locally per terms.
- Exported reports include a consolidated bibliography with versions and access dates.

---

## 8. Validation suite for ingestion

- **Schema tests**: required columns present; unit annotations consistent.
- **Range tests**: axis monotonicity; no NaNs in required fields.
- **Spot checks**: known landmarks (e.g., Si 520.7 cm⁻¹, polystyrene lines) match expected within tolerance.
- **Round‑trip**: write → read consistency for internal formats (HDF5/Parquet bundles).

---

## 9. Data shapes and internal storage

- **Line tables**: tidy format with one transition per row; indices for species/isotopologue/quantum numbers.
- **Spectra**: columns `[axis_value, intensity, uncertainty?]`; preserve original sampling.
- **Bundles**: HDF5/Parquet with groups for `raw`, `processed`, `meta`, and `provenance`.

---

## 10. Security, robustness, and ethics

- Respect robots and API limits; exponential backoff on retries.
- Isolate network failures from UI; show cached content with warnings.
- Keep PII out of manifests; only store operator initials if policy requires.

---

## 11. Cross‑links

- See Chapter 5 for unit and axis normalization; Chapter 6 for LSF and calibration math; Chapter 7 for identification scoring; Chapter 8 for provenance manifest fields; Chapter 11 for confidence thresholds; Chapter 31 for telescope specifics.

---

## Appendix A — Non‑exhaustive source list (with notes)

- **NIST ASD** — Authoritative atomic lines; evaluated uncertainties; ideal for wavelength calibration and elemental ID.
- **HITRAN/HITEMP** — Molecular line parameters and cross sections; temperature/pressure dependent; core for gas‑phase IR.
- **ExoMol** — Very large molecular line lists; high‑temperature astrophysical relevance; heavy storage considerations.
- **JPL/CDMS** — Rotational transitions for many interstellar molecules; essential for radio/mm‑wave contexts.
- **RRUFF** — Raman/XRD mineral database; strong for campus minerals and geology tie‑ins.
- **IRTF/SpeX, XSL** — Stellar and reflectance libraries; useful for reflectance/remote sensing comparisons.
- **CALSPEC** — HST spectrophotometric standards; absolute flux calibration anchor.
- **SDSS/ESO archives** — Large public spectral datasets; include pipeline versions and resolutions in headers.
- **TSIS‑1 HSRS** — High‑resolution solar spectral irradiance; reference for solar comparisons.

> **Note:** Where a source requires account/keys, store only the reference to the environment variable name in the registry (e.g., `HITRAN_API_KEY`), never the key itself.

