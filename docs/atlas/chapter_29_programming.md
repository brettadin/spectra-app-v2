# Chapter 29 — Programming

> **Purpose.** Define engineering standards, APIs, data models, and tooling so this app behaves like a grown‑up research platform: deterministic, testable, offline‑capable, and boringly reliable.
>
> **Scope.** Frontend (React/TypeScript), backend (Python), CLI tools, adapters for data sources, storage layout, schemas, testing, performance, logging, security, and release management. Contracts match earlier chapters (units, calibration, provenance, identification).
>
> **Path notice.** All filenames and directories are **placeholders**. Resolve tokens like `[SESSION_ID]`, `[DATASET_ID]`, `[MODALITY]`, `[YYYYMMDD]`, `[MODEL_ID]` at runtime via the app’s path resolver. Do **not** hardcode paths.

---

## 0. Architectural overview

- **Monorepo** with workspaces: `app/` (React), `engine/` (Python library), `cli/`, `adapters/`, `schemas/`, `docs/`.
- **Data lake layout** (content‑addressed):
  - `sessions/[SESSION_ID]/...` raw and processed spectra + manifests
  - `datasets/[DATASET_ID]/consolidated.h5` + `features.parquet`
  - `models/[MODEL_ID]/...` artifacts + model cards (Ch. 16)
  - `rubrics/[YYYYMMDD]/rubric.json` (Ch. 11)
  - `sources/registry.json` for libraries with `source_id@version` (Ch. 4)
- **Contracts** shared via `schemas/` (JSON Schema 2020‑12). Validation is mandatory at ingest, pre‑ID, and pre‑export (Ch. 8).

---

## 1. Language & framework standards

### 1.1 Frontend (React/TypeScript)
- State: component local + a lightweight store for app‑wide state.
- UI kit: Tailwind + shadcn/ui; icons via lucide.
- Plotting: a performant canvas‑based renderer with virtualized traces; no implicit smoothing.
- Internationalization: en‑US default; unit strings from Chapter 5 constants.

### 1.2 Backend/engine (Python)
- NumPy, SciPy for numerics; Pandas for tables; h5py for HDF5; pyarrow for Parquet; astropy for FITS/time/coordinates.
- Determinism: seed all randomness; freeze env with lockfiles; avoid non‑deterministic parallel reductions.
- CLIs built with `typer` or `argparse` and return non‑zero on failure. All CLIs have `--dry-run` and `--json` output.

---

## 2. Core modules (Python engine)

```
engine/
  units/          # conversions, air↔vacuum, Raman shift math (Ch. 5)
  lsf/            # kernels, convolution, FWHM estimation (Ch. 6)
  features/       # peak finding, fitting, uncertainty
  compare/        # similarity metrics, cross‑correlation (Ch. 15)
  identify/       # scoring + Bayesian fusion (Ch. 7)
  provenance/     # transform ledger + method cards (Ch. 8)
  io/
    jcamp.py      # JCAMP adapter (Ch. 12)
    fits.py       # FITS reader/writer (Ch. 12)
    hdf.py        # consolidated.h5 ops
  adapters/       # external sources registry (Ch. 4)
```

### 2.1 Deterministic transform ledger
Each transform function appends a record to `ledger.jsonl`:
```json
{"op":"convolve","params":{"kernel":"voigt","fwhm":6.0,"unit":"cm^-1"},"input":".../raw.csv","output":".../views/convolved.parq","ts":"[ISO-8601]","code":"engine.lsf:v1.3.0","seed":1729}
```

### 2.2 Identification API
```python
def identify(sample: str, *, dataset_ref: str, rubric_ref: str, prior_ref: str|None=None,
             template_refs: list[str]|None=None, seed: int=1729) -> dict:
    """Deterministic identification with per‑modality scores and evidence graph ref.
    Returns: {hypotheses:[...], scorecards:[...], evidence_graph_ref:str, ledger_tail:[...]}
    """
```

---

## 3. Schemas (JSON Schema 2020‑12)

### 3.1 Spectrum sidecar (`schemas/spectrum.schema.json`)
Key fields:
- `axis.unit` in {`nm`,`cm^-1`,`eV`}; `medium` in {`air`,`vacuum`}; `bunit` intensity unit
- `instrument`: make/model/ID; `lsf_ref`; `response_ref`
- `uncertainty`: method and per‑point or aggregate
- `masks`: array of masked windows with reasons

### 3.2 Evidence graph (`schemas/evidence.schema.json`)
Matches Chapter 3; nodes, edges, and justification arrays; graph has a content hash for reproducibility.

### 3.3 Rubric (`schemas/rubric.schema.json`)
Thresholds, modality weights, penalties, and quality weights. Versioned with semver and checksum.

Validation is enforced at ingest, before ID, and before export. On failure, produce a human‑readable diff plus the JSON pointer to the offending field.

---

## 4. CLI tools (indicative)

- `spectra ingest --in path --out sessions/[SESSION_ID] --format auto --strict`
- `spectra calibrate --session [SESSION_ID] --attach cal/*.json`
- `spectra features --glob sessions/[SESSION_ID]/**/processed/*.csv --out features.parquet`
- `spectra harmonize --dataset [DATASET_ID] --target-fwhm 6cm-1 --out views/`
- `spectra identify --dataset [DATASET_ID] --rubric rubrics/[DATE]/rubric.json --priors priors/*.json --out scorecards/`
- `spectra report --dataset [DATASET_ID] --out exports/ --bundle`

All commands support `--seed`, `--dry-run`, and `--json` for machine‑readable output.

---

## 5. Error handling & logging

- **Levels:** `DEBUG`, `INFO`, `WARN`, `ERROR`. Default: `INFO` in UI, `DEBUG` in logs.
- **Structured logs** (JSON lines) with keys: `ts`, `op`, `session`, `dataset`, `status`, `msg`, `exception`, `file`.
- **User messages** are short and actionable; link to docs (Ch. 13) and include the JSON pointer when schema validation fails.

---

## 6. Performance & memory

- Convolutions and cross‑correlations use FFTs with safe padding; cache kernels per FWHM.
- Avoid copies: memory‑map large arrays; use chunked IO for HDF5/Parquet.
- Vectorize peak picking and baseline ops; keep fallbacks for small arrays to avoid overhead.
- UI rendering uses virtualized traces; never draw millions of SVG points.

---

## 7. Testing & QA

- **Testing pyramid:** unit → integration → end‑to‑end. Golden fixtures live in `tests/fixtures/` with checksums.
- **Determinism tests:** run with pinned seeds and compare full JSON outputs and hashes.
- **Physics checks:** unit/axis conversions round‑trip; Raman shift math; LSF convolution identity on deltas (Ch. 5–6).
- **Library pinning tests:** `source_id@version` resolved and cached; warn on drift vs previously cached versions (Ch. 4).
- **UI accessibility tests:** keyboard paths, ARIA roles, contrast (Ch. 22).

---

## 8. Security & privacy

- **Offline mode** hard switch; adapters require explicit opt‑in to touch networks (Ch. 14).
- **No PII** in manifests by default; teaching exports anonymize operators; opt‑in initials only if policy permits.
- **Signed bundles:** export ZIPs contain `CHECKSUMS.txt` and optional signature. Verify at import.
- **Sandboxed notebook runner**: read‑only sessions, no network; transforms logged (Ch. 14).

---

## 9. Adapters and source registry

### 9.1 Adapter contract (TypeScript)
```ts
export interface SourceAdapter {
  readonly id: string;                // e.g., "HITRAN@2024.1"
  readonly license: string;           // SPDX or URL
  readonly formats: string[];         // e.g., ["csv","parquet","json"]
  resolve(query: SourceQuery): Promise<SourceResult>;
  toCanonical(result: SourceResult): CanonicalTable; // unit‑safe mapping
}
```
- Registered in `sources/registry.json` with cache location and checksum.
- Side‑by‑side comparator shows deltas between versions before adoption (Ch. 4).

---

## 10. Frontend components (contracts)

- `<SpectralViewer />` with synchronized cursors, unit badges, LSF banner (Ch. 22).
- `<EvidenceGraphPanel />` and `<RubricTable />` per Chapter 22 contracts.
- `<CalibrationTimeline />` plotting wavelength RMS, response stability, FWHM vs time (Ch. 6).
- `<SourceRegistryTable />` with `source_id@version` and license/DOI info (Ch. 4).

All components accept a `provenanceRef` and emit events logged to the transform ledger.

---

## 11. Configuration & environments

- **Config precedence:** CLI flags > env vars > `configs/*.json` > defaults.
- **Lockfiles:** Python (requirements lock), Node (lockfile). Capture both in exports.
- **Profiles:** `profiles/[USER]/settings.json` store UI preferences; recorded in provenance only when they affect exports (Ch. 20 §11).

---

## 12. Versioning & releases

- **SemVer** for app, schemas, and models. Breaking schema changes bump major.
- **Release bundle**: `docs/releases/[SEMVER]/` with change log, schema diffs, updated acceptance tests.
- **Determinism gate**: release blocked unless determinism test suite passes on fixtures.

---

## 13. Minimal code stubs

**Python: units and Raman shift**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Axis:
    unit: str  # 'nm'|'cm^-1'|'eV'
    medium: str  # 'air'|'vacuum'

HC_EV_NM = 1239.841984

def eV_from_nm(lambda_nm: float) -> float:
    return HC_EV_NM / lambda_nm

def raman_shift_cm1(lambda0_nm: float, lambdas_nm: float) -> float:
    return 1e7 * (1.0/lambda0_nm - 1.0/lambdas_nm)
```

**TypeScript: adapter registry**
```ts
type SourceId = `${string}@${string}`;

export interface RegistryEntry { id: SourceId; license: string; doi?: string; cachePath: string; checksum: string; }
export type Registry = Record<SourceId, RegistryEntry>;
```

---

## 14. Documentation links (Docs module, Ch. 13)

- Each public function/class has a docstring with examples and links to the relevant chapter sections.
- Docs are built into the app; clicking error tooltips jumps to the section explaining the rule and math.

---

## 15. Cross‑links

- Ch. 3 (evidence graph schema), Ch. 4 (source registry), Ch. 5 (units), Ch. 6 (LSF/response), Ch. 7 (identification), Ch. 8 (provenance), Ch. 9 (UI features), Ch. 11 (rubric), Ch. 12 (formats), Ch. 13 (Docs), Ch. 14 (App arch), Ch. 15–16 (comparisons + AI).

---

## 16. Reference anchors (full citations in Ch. 32)

- JSON Schema 2020‑12; RFC 8259 (JSON).
- HDF5 user guide; Apache Parquet format.
- NumPy/SciPy/Pandas, astropy docs.
- TypeScript handbook; React docs; Tailwind/shadcn component docs.
- FITS/WCS standards.
- PEP 8, PEP 484 (typing), PEP 518 (pyproject).

> All code must be deterministic, unit‑safe, and provenance‑rich. If you can’t reproduce an output bit‑for‑bit with pinned inputs, it doesn’t ship.

