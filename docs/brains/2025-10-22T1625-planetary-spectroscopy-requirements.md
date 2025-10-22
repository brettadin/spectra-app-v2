# Planetary Spectroscopy Data Requirements and Inspector Tab Migration

**Date**: 2025-10-22T16:25:50-04:00 (EDT) / 2025-10-22T20:25:50Z (UTC)  
**Status**: Accepted  
**Context**: Educational lab development requires real planetary spectroscopic data across multiple modalities

## Decision

1. **Relocate Remote Data UI**: Move "Fetch Remote Data" from File menu to dedicated Inspector tab
2. **Planetary Data Requirements**: Fetch real (non-synthetic) spectroscopic observations for all solar system planets
3. **Wavelength Coverage**: Target 0-2000 nm (UV-VIS-NIR) minimum; extend to MIR where available
4. **Multi-Modal Spectroscopy Support**: Align with educational lab covering UV-VIS, FTIR, Raman, and AES

## Rationale

### Why Move to Inspector Tab?
- **Progressive Disclosure**: Remote data fetching is an advanced workflow; inspector tab reduces menu clutter
- **Persistent Access**: Inspector remains visible during data exploration; less context-switching than modal dialog
- **Consistency**: Aligns with existing inspector pattern (Info, Math, Style, Reference tabs)

### Why Real Planetary Data?
**Educational Use Case**: Classroom lab where students:
1. Record lab spectra (UV-VIS, FTIR, Raman) of sample compounds
2. Compare with planetary observations from JWST/HST/ground-based missions
3. Analyze spectral features to predict atmospheric/surface composition
4. Perform exoplanet transmission spectroscopy simulations (overlay solar + exoplanet spectra)

**Research Goal**: Enable lab-to-observatory comparison workflow for composition analysis

### Spectroscopy Modalities

| Modality | Wavelength Range | Application | Data Source |
|----------|------------------|-------------|-------------|
| UV | 10-400 nm | Electronic transitions, ionization | JWST/HST/FUSE |
| UV-VIS | 200-800 nm | Atomic emission, electronic states | HST/JWST/ground |
| NIR | 800-2500 nm | Overtones, molecular vibrations | JWST/HST/ground |
| MIR | 2.5-25 µm | Fundamental vibrations, functional groups | JWST MIRI, Spitzer |
| FTIR (lab) | 4000-400 cm⁻¹ | Molecular fingerprinting | Lab instruments |
| Raman | Varies | Complementary to IR | Lab instruments |
| AES | UV-VIS | Elemental identification | Lab emission sources |

### Planetary Data Availability

**Requirements**:
- Spectroscopic observations (no photometry-only products)
- Calibrated data (Level 2+ preferred)
- Full provenance (mission → instrument → processing → DOI)
- Wavelength coverage: 0-2000 nm minimum (UV-NIR)

**Sources** (via MAST/astroquery):
- **Mercury**: MESSENGER (UV-VIS), ground-based
- **Venus**: Pioneer Venus, Magellan radar (limited spectroscopy), JWST observations
- **Earth**: Multiple satellite missions, ground-based solar system  analogs
- **Mars**: MRO/CRISM (VIS-NIR), JWST, ground-based
- **Jupiter**: JWST NIRSpec/MIRI, HST STIS/WFC3, Cassini VIMS (flyby), ground-based
- **Saturn**: Cassini VIMS/UVIS, JWST, HST, ground-based
- **Uranus**: JWST NIRCam/NIRSpec, HST, Voyager (limited), ground-based
- **Neptune**: JWST NIRCam/NIRSpec, HST, Voyager (limited), ground-based
- **Pluto/Charon**: New Horizons LEISA/MVIC, JWST (recent), ground-based occultations
- **Exoplanets**: JWST transmission/emission spectra (WASP-39 b, TRAPPIST-1, HD 189733 b, etc.)

### Exoplanet Transmission Spectroscopy Workflow

**Goal**: Extract exoplanet atmospheric features by simulating transit geometry

**Workflow**:
1. Load stellar spectrum (e.g., Sun, or host star from MAST)
2. Load exoplanet transmission spectrum (JWST observations)
3. Overlay both spectra (aligned wavelength axis via `UnitsService`)
4. Apply math operation: `(Exoplanet / Star) - 1` or similar ratio to isolate transit depth vs wavelength
5. Identify absorption features (H₂O bands ~1.4µm, CH₄ ~1.7µm, CO₂ ~4.3µm)
6. Compare with lab FTIR/Raman of candidate molecules

**Implementation**: Already supported via `MathService.ratio()` and `MathService.subtract()` on canonical nm grids

## Consequences

### UI Changes
- Add "Remote Data" tab to inspector tabs (after "Reference", before "Docs")
- Remove "Fetch Remote Data…" from File menu (keep keyboard shortcut Ctrl+Shift+R for discoverability)
- Embed simplified remote data controls directly in inspector tab (provider dropdown, search field, quick-pick buttons)

### Service Changes
- Extend `RemoteDataService._CURATED_TARGETS` with all solar system planets
- Add validation to ensure MAST queries return spectroscopic products only (filter out imaging/photometry)
- Document wavelength coverage gaps in `docs/user/real_spectral_data_guide.md`

### Documentation
- Update `docs/user/remote_data.md` with inspector tab location
- Create/extend Atlas chapter on planetary spectroscopy data sources
- Add user guide section on exoplanet transmission analysis workflow
- Update `docs/atlas/chapter_4_data_sources_to_ingest_and_align.md` with planetary MAST queries

### Testing
- Validate real spectroscopic data availability for each planet (not all have UV-NIR coverage)
- Add integration tests for planetary queries (see `tests/integration/test_remote_search_targets.py`)
- Test exoplanet transmission workflow with real JWST spectra

## References
- MAST archive: https://mast.stsci.edu/
- Astroquery MAST docs: https://astroquery.readthedocs.io/en/latest/mast/
- JWST instrument specs: https://jwst-docs.stsci.edu/
- Existing remote data UX decision: `docs/brains/2025-10-18T0924-remote-data-ux.md`
- User guide: `docs/user/real_spectral_data_guide.md`
- Link collection: `docs/reference_sources/link_collection.md`
