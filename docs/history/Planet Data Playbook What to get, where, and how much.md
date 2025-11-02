# Planet Data Playbook: What to get, where, and how much

Use these instrument and product pointers to narrow searches. Prefer calibrated science products with label files (.LBL). Always dry-run downloaders and visually verify URLs.

General tips
- Keep both data and label files together.
- Exclude engineering, INDEX, CATALOG, and checksum files.
- Target 10–30 representative observations per instrument to build a robust composite.

Mercury
- Mission/instruments: MESSENGER MASCS (UVVS, VIRS)
- Wavelengths:
  - UVVS: ~115–600 nm (FUV/MUV/VIS)
  - VIRS: ~0.3–1.45 µm
- Product types: CDR (calibrated), DDR (derived)
- File patterns to include:
  - UVVS: ufc_*.dat/img, umc_*.dat/img, uvc_*.dat/img + .LBL
  - VIRS: vvc_*.dat/img, vnc_*.dat/img + .LBL
- Avoid: grs_*, grs_eng, messgrs_*, *_eng*, *_hdr*, INDEX/, CATALOG/
- How many: UVVS 20–40; VIRS 10–20 across multiple orbits and phase angles
- Nodes/portals: PDS Geosciences (MESSENGER), Atmospheres (UVVS)
- Notes: Favor dayside reflectance for surface; nightside UVVS may capture exosphere emissions (exclude for surface composites).

Venus
- Best sources: Venus Express VIRTIS (VIRTIS-M VIS/IR), Akatsuki (UVI, IR2), HST (UV reflectance)
- Wavelengths:
  - VIRTIS-M VIS: ~0.35–1.05 µm; IR: ~1–5 µm (nightside thermal windows near 1.02, 1.10, 1.18, 1.31 µm)
  - Akatsuki UVI: ~283/365 nm; IR2: ~1–2 µm
- Product types: Calibrated (LEVEL 2/3; PDS3 CAL/DDR); VIRTIS cubes often .IMG/.QUB + .LBL
- How many: 15–30 scenes balanced across dayside (reflectance) and nightside (thermal windows)
- Filters: Target=VENUS; Instruments=VIRTIS-M, UVI, IR2; exclude housekeeping/engineering
- Notes: Use derived reflectance/I/F where available; nightside spectra are emission-dominated.

Mars
- Best sources: MRO CRISM, Mars Express OMEGA
- Wavelengths:
  - CRISM: 0.36–3.92 µm; OMEGA: 0.35–5.1 µm
- Products: CRISM TRDR (FRT/HRL/HRS), OMEGA calibrated cubes; .IMG/.QUB + .LBL
- How many: 10–20 CRISM targeted scenes (FRT_*) across diverse terrains; 10 OMEGA for coverage
- Notes: CRISM often requires CAT processing for atmospherics; for quick-look, prefer products labeled I/F or reflectance.

Jupiter and Saturn
- Best source: Cassini VIMS
- Wavelength: 0.35–5.1 µm
- Products: Calibrated VIMS cubes (.QUB/.IMG + .LBL) from COVIMS_00xx volumes
- How many: 10–20 per planet covering multiple phase angles and latitudes; exclude rings-only when targeting planet disk
- Notes: Use observation metadata to ensure TARGET_NAME matches the planet.

Uranus and Neptune
- Sources: HST (STIS, WFC3), IUE legacy spectra
- Wavelengths: UV–NIR depending on instrument (e.g., WFC3 200–1000 nm)
- Products: Calibrated spectral files (often FITS + keyword headers); export to CSV via astropy if needed
- How many: 5–15 well-exposed spectra per planet across epochs
- Notes: Favor disk-integrated or large-aperture observations for global spectra.

Pluto (and Triton)
- Source: New Horizons LEISA (for Pluto), HST for reflectance curves
- Wavelengths: LEISA ~1.25–2.5 µm
- Products: Calibrated spectral cubes (.IMG/.LBL)
- How many: 5–10 representative cubes/tiles; extract disk-averaged spectra
- Notes: Strong CH4, N2 features; ensure geometry is documented.

Moon
- Sources: Chandrayaan-1 M3, Clementine UVVIS
- Wavelengths: M3 0.46–3.0 µm; Clementine UV/Vis bands
- Products: Calibrated strips/mosaics; .IMG/.LBL
- How many: 10–20 strips for diverse terrains (mare/highlands)
- Notes: Use derived reflectance where available to avoid heavy preprocessing.

How to search on PDS (quick filters)
- Use PDS Imaging/Geosciences/Atmospheres search portals.
- Set: Target Name, Mission/Instrument, Product Level (Calibrated/Derived), File Type (.IMG/.DAT + .LBL).
- Exclude: ENGINEERING, INDEX, CATALOG, CHECKSUM, MD5.

Minimal download checklist (all targets)
- Include label files (.LBL) with each data file.
- Prefer calibrated (CDR/TRDR/Level 2+) over raw/EDR.
- Collect 10–30 observations per instrument for merging.
- Verify by eye that filenames match expected science prefixes.
- Run conversion with existing parsers; if FITS, convert with astropy to CSV.

Next steps
- Re-verify MASCS volume layout and update downloader allow-list.
- Add PDS-portal scraping utility that applies the filters above and exports a curated file list.