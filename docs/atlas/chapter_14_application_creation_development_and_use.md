# Chapter 14 — Application Creation, Development, and Use

> **Purpose.** Specify how the Spectra App is architected, developed, tested, packaged, deployed, and used by scientists and students so it faithfully implements the workflow and constraints from Chapters 1–13.
>
> **Scope.** Backend services, front‑end UI, data/ML layers, configuration, path resolution, plugin system, CI/CD, testing, packaging, security, and CLI/SDK ergonomics. Targets campus laptops and lab workstations first; optional server mode for class deployments.
>
> **Path notice.** All filenames and directories below are **placeholders**. Resolve tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[INSTRUMENT_ID]`, `[YYYYMMDD]` at runtime via the app’s path resolver. Do **not** hardcode actual paths.

---

## 0. Architecture overview

**Goals:** deterministic science (reproducible, logged), offline‑friendly, plugin‑extensible, minimal moving parts.

```
[UI (React/TypeScript)]  ⇄  [Application API (HTTP/IPC, OpenAPI)]  ⇄  [Core Engine (Python)]
                                                         │
                        [Adapters: file/source plugins]  │  [Models: identification, ML]
                                                         │
                                            [Storage: HDF5/Parquet bundles, cache/]
```

- **Core Engine (Python):** numerical kernels for ingest, calibration, unit conversions, LSF, scoring, fusion (Ch. 5–7).
- **Application API:** typed, versioned endpoints; also callable locally via IPC for offline mode.
- **UI:** multi‑pane Spectral Viewer, Report Builder, Calibration Manager (Ch. 9).
- **Plugins:** adapters for vendor formats and external sources (Ch. 4). Loaded from a registry; sandboxed.
- **Storage:** session bundles + manifests (Ch. 8), formats from Ch. 12. Content‑addressable cache for libraries.

---

## 1. Reproducibility contract (non‑negotiable)
1. **Deterministic builds:** pin all deps; lockfiles checked into repo. App displays build hash in About dialog and in every report footer.
2. **Immutable raw:** raw files are write‑once; transforms write new views and append ledger entries (Ch. 8 §3).
3. **Pinned constants:** CODATA versions recorded in each session manifest (Ch. 5 §1).
4. **Version‑pinned sources:** all line lists/libraries referenced as `source_id@version` (Ch. 4 §5).

---

## 2. Configuration and path resolution

### 2.1 App config (YAML) — placeholder
```yaml
app:
  semver: "[MAJOR.MINOR.PATCH]"
  build_hash: "[GIT-SHORTSHA]"
paths:
  sessions_root: "[RESOLVED_AT_RUNTIME]"
  cache_root: "[RESOLVED_AT_RUNTIME]"
  exports_root: "[RESOLVED_AT_RUNTIME]"
units:
  constants: {c: "CODATA-20xx", h: "CODATA-20xx"}
  air_model: {name: "Ciddor96", params: {P_Pa: 101325, T_K: 293.15, xCO2: 0.0004, RH: 0.0}}
security:
  offline_mode: true
  allowed_plugins: ["adapters/hitran_lines_v2020", "adapters/rruff_raman_v1"]
```

### 2.2 Path resolver API
```python
def resolve(tokenized_path: str, context: dict) -> Path:
    """Replace tokens [SESSION_ID], [DATASET_ID], [MODALITY], [YYYYMMDD] from context.
    Never accepts absolute paths from user uploads; normalizes and sandboxes."""
```

**Rule:** any module that reads/writes files must call `resolve()`; direct `open()` on user strings is forbidden.

---

## 3. Data model and core modules (Python)

- `spectra.units`: conversions and medium flags (Ch. 5), Raman shift with uncertainty.
- `spectra.calibration`: wavelength/shift solutions, response functions, LSF kernels (Ch. 6).
- `spectra.features`: peak picking, baseline, fits with covariance (Ch. 3 §2).
- `spectra.fusion`: per‑modality scoring, priors, Bayesian fusion (Ch. 7).
- `spectra.ingest`: vendor parsers, sidecars, HDF5/Parquet IO (Ch. 12).
- `spectra.prov`: manifests, transform ledger, hashing/Merkle (Ch. 8).
- `spectra.adapters`: external source loaders (Ch. 4) with caching and checksums.

All modules expose **pure functions** that accept arrays + metadata, and return new arrays + metadata + a provenance step.

---

## 4. Application API (OpenAPI‑described)

### 4.1 Example endpoints (placeholders)
```
POST  /ingest/session                 → Validate + import a session bundle
GET   /sessions/{session_id}/spectra  → List spectra and views
POST  /spectra/{id}/calibrate         → Apply calibration artifacts
POST  /spectra/{id}/extract_features  → Peak/fit with stored params
POST  /identify                       → Run fusion, return ranked hypotheses
GET   /reports/{id}                   → Render report bundle (PDF + data)
```
All endpoints accept/return JSON with schema versions; binary arrays transported as HDF5/NPZ attachments when large.

---

## 5. Front‑end principles (UI)
- **No silent transforms.** Every change yields a visible ledger entry (Ch. 8).
- **Unit badges and tooltips** synchronized across views (Ch. 5).
- **Resolution banner** shown when views are convolved (Ch. 6).
- **Evidence graph** and **Rubric tables** visible for each identification (Ch. 3, 11).
- **Education mode** overlays concept cards and locks risky actions (Ch. 13).

---

## 6. CLI and SDK

### 6.1 CLI commands (sketch)
```
spectra ingest  --bundle /path/to/zip --session [SESSION_ID]
spectra qc      --session [SESSION_ID] --print-metrics
spectra fit     --spectrum [ID] --model voigt --window 1000:1800
spectra identify --session [SESSION_ID] --dataset [DATASET_ID] \
                 --rubric rubrics/[YYYYMMDD]/rubric.json
spectra report  --session [SESSION_ID] --dataset [DATASET_ID] --out exports/[...].zip
```

### 6.2 Python SDK (typed stubs)
```python
from spectra import ingest, identify
bundle = ingest.load_session("sessions/[SESSION_ID]")
results = identify.run(bundle, priors={"elements":["Na","K"]})
identify.explain(results[0]).to_markdown()
```

---

## 7. Testing strategy

- **Unit tests:** conversions (nm↔cm⁻¹↔eV), Raman propagation, wavelength solutions, response/LSF math (Ch. 5–6).
- **Property‑based tests:** monotonic axes; round‑trip conversions precise to tolerance (Ch. 5 §10).
- **Golden tests:** benchmark sessions; identification results identical given fixed seeds (Ch. 7 §10).
- **Integration tests:** full ingest→calibrate→extract→identify→report pipeline on small fixtures.
- **Fuzzing:** malformed JCAMP/FITS headers; adapter hardening (Ch. 4 §8–10).
- **Performance tests:** convolution, cross‑correlation, large line lists.

CI runs on every commit; artifacts saved with checksums. A release gate blocks when **determinism** tests fail.

---

## 8. Packaging and deployment

- **Python packaging:** wheel + constraints/lock files; optional conda recipe.
- **App bundling:** desktop build with embedded Python runtime for offline labs.
- **Containers (optional):** minimal image with non‑root user, no network at runtime by default.
- **Hardware notes:** CPU first; optional GPU for heavy cross‑correlation is behind a feature flag.

**Release artifact**: `releases/[SEMVER]/spectra_app_[OS]_x86_64.zip` with `CHECKSUMS.txt` and a provenance stamp.

---

## 9. Security, privacy, and licensing

- **Sandbox plugins:** adapters run in a restricted environment; no outbound network unless whitelisted source registry entry (Ch. 4).
- **Role‑based access:** student/TA/PI roles (Ch. 9 §7). Destructive actions gated to PI.
- **PII minimization:** manifests keep operator initials only where policy requires (Ch. 8 §12).
- **License enforcement:** per‑source terms in registry; UI blocks redistribution if prohibited (Ch. 4 §7).
- **Supply‑chain hygiene:** pin deps; verify vendor packages with checksums; optional signature verification of releases.

---

## 10. Logging, telemetry, and troubleshooting

- **Local logs:** structured JSON logs per run under `logs/[YYYYMMDD]/[SESSION_ID].jsonl` (placeholder path). Include timing, memory, warnings.
- **Provenance first:** transform ledger is the primary debug tool (Ch. 8 §3).
- **Telemetry:** opt‑in only; aggregate anonymized metrics (e.g., feature fit failures) to improve defaults; never collect spectra content.
- **Crash dumps:** redact paths and PII; include module versions and seeds.

---

## 11. Performance tips

- Vectorized math; FFT‑based convolutions for large windows.
- Cache expensive views keyed by content hashes (axis, intensity, params) with eviction policy.
- Convolve high‑res to low (never the reverse) for overlays (Ch. 6 §5).
- Stream HDF5 reads by wavelength blocks to avoid loading entire arrays when rendering.

---

## 12. Contribution guidelines (for humans and agents)

1. Write tests before or with features; keep benchmark size small but representative.
2. Document every public function with parameter units and return types.
3. Update **Docs/Learning** (Ch. 13) with examples. No feature ships without documentation.
4. Update **rubric configs** if identification logic changes; bump minor version and note migration instructions.
5. Run `make verify` (placeholder) to execute lint, tests, schema checks, docs build, and determinism tests.

---

## 13. Migration and backward compatibility

- **Schemas:** bump semantic versions on JSON/HDF5 schemas; provide migration scripts.
- **Rubrics:** keep old rubrics available; the app warns when opening sessions with older rubric IDs.
- **Sources:** permit side‑by‑side library versions (e.g., HITRAN 2020 vs 2024) with explicit selection (Ch. 4 §5).

---

## 14. User workflows (operational quick starts)

### 14.1 Lab session
1. Create session via Ingest Manager; fill manifest skeleton.
2. Calibrate: attach lamp/polystyrene/Si/response artifacts.
3. Extract features; verify QC; convolve to target FWHM for overlays.
4. Identify; review evidence graph and rubric tables; export report.

### 14.2 Observatory/archive session
1. Load FITS; confirm WCS/units; set barycentric context.
2. Build sensitivity function from standard; flux‑calibrate; mask tellurics.
3. Cross‑correlate templates; compute `v_r`; run identification with priors.
4. Export bundle with velocity context.

### 14.3 Teaching mode
1. Toggle Teaching Mode; follow checklists; complete auto‑graded checkpoints.
2. Submit report bundle; rubric auto‑grades process and evidence (Ch. 11 §8).

---

## 15. Future upgrades
- Spectral‑imaging cubes (2D/3D) with ROI extraction and per‑pixel identification.
- Live instrument bridges for supported vendors to auto‑capture manifests and calibration artifacts.
- Active‑learning loop to propose the next most informative measurement (Ch. 7 §13).
- W3C PROV export alongside our JSON provenance (Ch. 8 §15).
- Built‑in dataset DOI minting for campus archive sessions.

---

## 16. References (anchor list; full citations in Ch. 32)
- **OpenAPI** specification for API description.
- **JSON Schema** for config and manifest validation.
- **Semantic Versioning (SemVer)** for releases and schema bumps.
- **HDF5/Parquet/FITS/JCAMP‑DX** format docs.
- **IUPAC Gold Book** for units/definitions; **CODATA** for constants.

> Cross‑links: Ch. 4 (source registry), Ch. 5 (units), Ch. 6 (calibration/LSF), Ch. 7 (identification), Ch. 8 (provenance), Ch. 9 (feature expectations), Ch. 12 (formats), Ch. 13 (docs & pedagogy).

