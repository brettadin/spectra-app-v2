# Chapter 8 — Provenance and Reproducibility You Will Not Skip

> **Purpose.** Make every result traceable, auditable, and repeatable by any future agent or human. Define the provenance model, manifest schema, hashing/version rules, and export/report formats that guarantee someone in 2031 can push the same buttons and get the same answers.
>
> **Scope.** All modalities (atomic/UV–Vis, FTIR/ATR, Raman, fluorescence) and external sources (NIST/HITRAN/RRUFF/CALSPEC/etc.). Applies to raw data, processed views, transforms, calibration artifacts, ML models, and reports.
>
> **Path notice.** All paths below are **placeholders** and MUST be resolved via the application’s path resolver at runtime. Do not hardcode. Treat tokens like `[SESSION_ID]`, `[MODALITY]`, `[DATASET_ID]`, `[CAL_ID]`, `[YYYYMMDD]` as variables.

---

## 0. Non‑negotiable principles
1. **Raw is immutable.** Stored once, never overwritten. Every transform creates a new view with a provenance record.
2. **Idempotent units.** Canonical axis per modality (Chapter 5). No chained conversions; all re‑derived from canonical.
3. **Every action leaves a breadcrumb.** Calibrations, baselines, fits, normalizations, convolutions, re‑samplings, and ML inferences must record parameters, code versions, input hashes, and outputs.
4. **Version pinning.** Source datasets, model weights, constants (CODATA), and line lists carry explicit versions in manifests and reports.
5. **Determinism by default.** Any step with randomness pins a `seed` and logs the RNG backend.

---

## 1. Provenance bundle (object model)
Each spectrum or derived product packages the following **bundle**:
```
{
  raw,               # vendor/native + interchange copy
  processed,         # one or more views derived from raw
  calibration,       # references to session calibration artifacts
  instrument_meta,   # make/model/serial/firmware/resolution/LSF
  environment_meta,  # T, P, humidity, purge, gas flows, etc.
  transforms_applied,# ordered list of transforms with params and hashes
  references,        # libraries/line lists/templates with versions
  checksums,         # SHA-256 (or better) of all files in the bundle
  created_by         # app build/version, agent, host OS, RNG seed
}
```

---

## 2. Session manifest (JSON schema, minimum)
**File:** `sessions/[SESSION_ID]/manifest.json`
```
{
  "session_id": "[SESSION_ID]",
  "operator": {"id":"[USER]","role":"student|pi|ta"},
  "course_or_project": "[STRING]",
  "instruments": [
    {"instrument_id":"[INSTRUMENT_ID]","make":"","model":"","serial":"","firmware":"","lsf":{"kind":"gaussian|voigt|sinc","fwhm_units":"nm|cm-1","params":{}}}
  ],
  "environment": {"lab":"[ROOM]","T_K":298.15,"RH":0.35,"pressure_Pa":101325},
  "constants": {"c":"CODATA-20xx","h":"CODATA-20xx"},
  "axis_units": {"canonical":"nm|cm-1|eV|THz","medium":"vacuum|air","air_model":{"name":"Ciddor96","params":{}}},
  "calibration_artifacts": [
    {"cal_id":"[CAL_ID]","type":"dark|lamp|polystyrene|Si520|response|extinction|velocity","path":"sessions/[SESSION_ID]/cal/[FILE]","hash":"sha256:...","created_at":"ISO-8601"}
  ],
  "sources": [
    {"source_id":"NIST_ASD@vX","citation":"...","accessed":"YYYY-MM-DD"},
    {"source_id":"HITRAN@2020","citation":"...","accessed":"YYYY-MM-DD"}
  ],
  "software_env": {"app_build":"[SEMVER]","python":"3.x","packages":{"numpy":"1.x","scipy":"1.x","astropy":"x.y"},"os":"[NAME VERSION]"},
  "rng": {"backend":"numpy","seed":123456},
  "notes":"free text",
  "checksums": {"manifest":"sha256:..."}
}
```

**Rule:** if a required field is missing, the app refuses to accept the session until remedied.

---

## 3. Transform log entries (ordered ledger)
Every transform appends an entry to `transforms_applied` for the relevant product. Example:
```
{
  "step": 3,
  "name": "lsf_convolution",
  "inputs": ["sessions/[SESSION_ID]/[MODALITY]/processed/[INPUT].h5"],
  "outputs": ["sessions/[SESSION_ID]/[MODALITY]/processed/[OUTPUT].h5"],
  "params": {"kernel":"gaussian","fwhm":6.0,"units":"cm-1"},
  "code": {"module":"spectra.transforms.convolution","version":"1.3.2","git":"commit:abc123"},
  "hash": {"input":"sha256:...","output":"sha256:..."},
  "timestamp":"ISO-8601"
}
```
**Never** reuse a previous step number; ledger order is authoritative.

---

## 4. Hashing and file integrity
- **Algorithm:** SHA‑256 for files and JSON canonicalization for structured objects (UTF‑8, sorted keys, trimmed whitespace).
- **Bundle digest:** each bundle also stores a **Merkle‑root** over member hashes for rapid verification.
- **On ingest:** verify hash if provided, else compute and stamp; if mismatch, quarantine file with a red banner in UI.

---

## 5. Version pinning and registries
- **Sources:** `source_id@version` (e.g., `HITRAN@2020`, `RRUFF@2024-09`) in both session and report.
- **Libraries:** maintain a **source registry** (Chapter 4) with licensing and DOI/URL, access date, and adapter version.
- **Constants:** CODATA set version pinned and recorded.
- **Models:** ML model cards: `{name, hash, training_set_id, metrics, date}`; stored under `models/` with checksums.

---

## 6. Environment capture for reproducibility
- `software_env` includes package names and exact versions; when available, attach a lockfile snapshot (e.g., `conda-lock.yaml` or `requirements-lock.txt`).
- Record OS, CPU/GPU, BLAS backend (MKL/OpenBLAS), and any CUDA libraries that affect numerics.
- For notebook‑style runs, embed the executed cell history (IDs + hashes) with timestamps.

---

## 7. Calibration artifacts — linkage and validity
- Each product references the **exact** calibration artifact IDs used. Artifacts carry **validity windows** (time, instrument state, temperature/humidity ranges).
- If an artifact is used outside its validity window, the UI raises an amber warning and the report flags it.

---

## 8. Data lineage graph
Represent provenance as a directed acyclic graph (DAG): nodes are files/objects; edges are transforms. Save to `graphs/[SESSION_ID]/lineage_[DATASET_ID].json` with:
```
{
  "nodes": [{"id":"raw:...","kind":"raw"},{"id":"proc:...","kind":"view"},{"id":"cal:...","kind":"cal"}],
  "edges": [{"from":"raw:...","to":"proc:...","step":1,"transform":"dark_subtract"}]
}
```
The UI should display this DAG and allow clicking any node to open its manifest and preview.

---

## 9. Export packages
- **Human‑readable:** CSV/TXT spectra + plots (PNG/SVG) + a **Report.pdf** and `manifest.json`.
- **Machine‑readable:** HDF5/Parquet bundle with arrays, uncertainties, LSF kernels, masks, and the full transform ledger.
- **Naming:** `exports/[SESSION_ID]/[DATASET_ID]/export_[YYYYMMDD].zip` (placeholder). Paths resolved at runtime.
- **Checksum file:** `CHECKSUMS.txt` (sha256sum lines) at the package root.

---

## 10. Reports (minimum sections)
1. Summary of goals, sample IDs, instruments, and operator.
2. Calibration table: wavelength RMS, LSF FWHM, response function IDs.
3. Identification results: top‑N hypotheses with confidence, per‑modality contributions, and nearest alternatives.
4. Transform ledger (ordered) with parameter tables.
5. Library/source list with versions, DOIs/URLs, and access dates.
6. Unit/axis constants used (Chapter 5), with air/vacuum model parameters if conversions applied.

---

## 11. Reproducibility tests (ship with app)
- **Round‑trip units:** nm ↔ cm⁻¹ ↔ nm; eV ↔ nm (Chapter 5 tolerances).
- **Determinism:** re‑run identification with the same seed returns identical ranked hypotheses and scores.
- **Hash stability:** recomputing manifest and bundle digests without content changes yields identical hashes.
- **Environment reinstalls:** recreate environment from lockfile; run a smoke suite; compare numeric tolerances.

---

## 12. Privacy, ethics, and attribution
- Strip PII beyond operator initials (if policy requires). No student grades or IDs in manifests.
- Always attribute external sources in exports and public plots; include **full citations** and versions.
- Respect licensing; do not redistribute restricted datasets. Cache according to terms.

---

## 13. Failure modes and safeguards
- **Missing units/medium flags:** block ingest with actionable error.
- **Drift beyond spec:** auto‑prompt re‑calibration; mark session amber until resolved.
- **Vendor auto‑processing hidden:** detect suspicious headers; force explicit toggles and log any vendor preprocessing.
- **Clock skew:** if timestamps look impossible, record warning and include both wall clock and monotonic counters.

---

## 14. Cross‑links
- Ch. 2 — how manifests are filled during acquisition.
- Ch. 4 — source registry and licensing.
- Ch. 5 — axis/unit rules preserved in provenance.
- Ch. 6 — calibration artifacts.
- Ch. 7 — identification outputs and report wiring.
- Ch. 11 — scoring rubric that consumes provenance fields.

---

## 15. Future upgrades
- DOIs for campus datasets via an institutional repository; store DOI in manifest.
- Signed manifests (Ed25519) and transparency logs for tamper‑evidence.
- W3C PROV serialization export alongside our JSON.
- Immutable object store backend with content‑addressable paths.
- Autogenerated **method cards** that summarize SOPs, parameters, and QC in a single page for each dataset.

