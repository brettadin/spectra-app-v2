Pass 4 — Data & Provenance Cohesion
0) Outcomes (what “done” looks like)
	• One authoritative manifest schema (versioned) that every service writes to and every export validates against.
	• Export-what-I-see parity: the bundle exactly reproduces the current view (units, normalization, smoothing, LSF/frames, masks, palettes, LOD, etc.).
	• Content-addressed LocalStore with clear retention & dedupe; portable across machines.
	• Library ⇄ Knowledge-log ⇄ History crosslinks (clickable both ways).
	• CI: schema validation, round-trip reproducibility, UI-contract checks, and drift detectors.

1) Single Source of Truth (Schema & IDs)
1.1 Manifest schema (semver)
	• File: docs/specs/provenance_schema.json (versioned, e.g., 1.2.0).
	• Top-level fields (minimal but complete):
		○ schema_version, app_version, created_at_et (ET, full timestamp), platform.
		○ inputs[] (each: id, kind = upload/remote/bundled, source_path_or_uri, hash_sha256, units, instrument, metadata).
		○ transforms[] (ordered steps; see §2).
		○ calibration block (see Pass 3).
		○ identification block (see Pass 3).
		○ view_state (see §3).
		○ outputs[] (CSV/PNG/JSON produced in the bundle with hashes).
		○ citations[] (DOIs/ADS/URLs with title, authors, year, publisher).
		○ seed (determinism), notes.
1.2 Stable IDs
	• Dataset ID = sha256(canonical_nm_x || y || units || instrument_id); store once in LocalStore.
	• Transform ID = sha256(kind || normalized_params || parent_ids || code_version).
	• Run/Manifest ID = sha256(all_top_level_fields_without_hashes); placed in bundle root as MANIFEST_ID.
This keeps Library entries, Knowledge-log items, and manifests consistent and dedupe-friendly.

2) Transform Registry (ordered, typed, unit-safe)
Create a small registry (constants + doc) that names every transform and its canonical parameters/units:
	• ingest_csv, ingest_fits, ingest_jcamp
	• airvac_convert (to = air|vacuum)
	• velocity_shift (rv_kms, frame= topocentric|heliocentric|barycentric)
	• lsf_convolve (kernel, fwhm_nm, convolve_down_only)
	• resample (method, grid = canon)
	• normalize (mode= none|max|area)
	• smooth (method= sg, window, poly)
	• mask_interval (x_nm_start, x_nm_end, reason)
	• math_op (op= A_minus_B|A_div_B, inputs[] ids, epsilon if needed)
Rules
	• Units explicitly recorded for every numeric in params.
	• Idempotence: transforms describe math on canon arrays; no chained unit mutations.
	• Serialization: every applied step is appended to transforms[] and mirrored in calibration/identification blocks when relevant.

3) Export-what-I-see Parity
Extend ProvenanceService.export_bundle(view=True) to serialize UI state:
	• view_state:
		○ display_unit (nm|angstrom|micrometer|wavenumber_cm-1)
		○ normalization (none|max|area)
		○ smoothing (method + params)
		○ palette_key
		○ lod_budget_points
		○ crosshair_visible, uncertainty_visible, snap_to_peak, snap_radius_nm
		○ masks[] (intervals)
		○ Calibration banner snapshot (kernel, target FWHM, frame, RV)
		○ active_traces[] (ids & visibility order)
Bundle layout
/export_<MANIFEST_ID>/
  manifest.json
  view.png                      # current canvas
  spectra/<DATASET_ID>.csv      # canonical x_nm, y, sigma?
  sources/<original_name.ext>   # raw copies
  logs/log.txt                  # chronological human-readable log
  reports/identification.json   # explainable score + tables (if present)
Round-trip test: a replay utility can load manifest.json, re-ingest canon CSVs, re-apply ordered transforms, set view_state, and regenerate view.png within a small pixel RMSE tolerance.

4) LocalStore (content-addressed, portable)
4.1 Index & layout
	• Root (configurable): %APPDATA%/SpectraApp/data/
	• index.json (maps DATASET_ID → metadata, original filename, timestamps, citations).
	• blobs/<first2>/<next2>/<sha256> (content-addressed data chunks).
	• manifests/<MANIFEST_ID>.json (optional cache of exports for re-open).
4.2 Dedupe & retention
	• Dedupe by DATASET_ID. Re-ingest same canon arrays results in a single Library entry with updated last-seen time.
	• Retention policy: LRU by size/age with opt-out; never purge pinned datasets (UI pin).
	• Portability: Export → Rehydrate to Library reads bundles and re-imports all spectra + manifest, preserving IDs and links.

5) Library ⇄ Knowledge-log ⇄ History (crosslinks)
5.1 Click-throughs
	• Library detail pane: add buttons:
		○ “Open manifest” (if it came from an export),
		○ “Open knowledge-log entry” (if attached),
		○ “Rebuild current view”.
	• History dock events link to:
		○ the Library record (dataset or manifest),
		○ the Knowledge-log section.
5.2 Knowledge-log policy (canonical vs runtime)
	• Canonical: only conceptual entries (design decisions, new services, data policy changes, acceptance test deltas).
	• Runtime noise (routine ingest/open/overlay) → History dock only.
	• When a manifest is exported, add one Knowledge-log entry referencing the MANIFEST_ID, not each sub-action.
Entry shape (Markdown + front-matter recommended)
# [2025-10-17 19:11:32 ET] Export bundle created — MANIFEST_ID=<…>
- Context: Export-what-I-see after calibration & identification
- Inputs: 3 datasets (IDs …)
- Key Steps: velocity_shift(+12.4 km/s, heliocentric), lsf_convolve(gaussian, 0.30 nm)
- Outputs: view.png, spectra/*.csv, identification.json
- References: docs/specs/provenance_schema.json@1.2.0


6) CI / QA (preventing drift)
Add a CI job “Provenance & Cohesion” with these steps:
	1. Schema validation
		○ Use jsonschema to validate every test-produced manifest.json against docs/specs/provenance_schema.json.
		○ Fail if unknown fields, wrong units, or missing blocks.
	2. Round-trip reproducibility
		○ Run a smoke test that: ingest fixture → apply transforms → export view bundle → replay manifest → regenerate view → measure image RMSE and metadata equality (units, masks, calibration banner, order of transforms).
	3. Determinism & seeds
		○ Sweep tests with the default seed. Assert deterministic scores, peak lists, and identification results (± small tolerances).
	4. UI-contract verifier
		○ Script that launches the app in headless mode and asserts:
			§ Presence of required controls (units, palette, LOD, uncertainty, snap, mask, calibration dock, export-view).
			§ Default states (e.g., crosshair on; teaching mode preset accessible).
		○ Fails if any control disappears (prevents accidental UI regressions).
	5. Doc consistency
		○ Lint links from UI “?” buttons to doc anchors.
		○ Ensure docs updated in PRs that touch services referenced in Atlas (small rule file: service → docs mapping).
	6. Performance guard
		○ Time budgets: calibration on 1e6 points, xcorr scan across RV grid, plot redraw at LOD budget. Fail with informative margin if exceeded.

7) Security, licensing, and privacy
	• Manifests must not embed secrets or PII. Remote API keys read from user config (already guarded).
	• Cite all datasets (NIST/MAST/…); ensure licenses stored in citations[].
	• If a dataset is proprietary/course-limited, mark data_restrictions in manifest and require opt-in to export sources.

8) Documentation to add/upgrade
	• docs/specs/provenance_schema.json (authoritative).
	• docs/dev/provenance.md (how services write steps; examples; migration).
	• docs/user/exporting.md (what’s inside bundles; how replay works).
	• docs/user/library.md (pins, retention, crosslinks to knowledge-log).
	• Add a 1-page map: docs/MAP.md linking Atlas chapters → code modules → tests.

9) Concrete tasks (atomic & merge-friendly)
	1. Schema & validators
		○ Add provenance_schema.json (v1.2.0), Python validator, sample manifests.
	2. Export-view parity
		○ Extend ProvenanceService and toolbar action; include view_state and calibration banner snapshot.
	3. LocalStore CAS & retention
		○ Introduce blobs/ layout; write index.json reader/writer; add pin/LRU; rehydrate from bundles.
	4. Crosslinks
		○ Library detail buttons → manifest & knowledge-log; History rows → Library entries.
	5. CI “Provenance & Cohesion” job
		○ Schema validation, round-trip, determinism, UI-contract, doc map lint.
	6. Docs
		○ provenance.md, exporting.md, library.md, MAP.md; add “?” deep-links in UI.

Does the whole picture make sense?
Yes. Pass 1–3 ensure the math and UI are honest and explainable; Pass 4 wires the data model and tooling so everything is replayable, auditable, and portable. Together they align tightly with Atlas’ priorities (truth-first visuals, deterministic science, reproducibility, and pedagogy).
