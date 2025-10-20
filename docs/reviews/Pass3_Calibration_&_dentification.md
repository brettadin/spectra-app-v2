Pass 3 — Calibration & Identification
Goals (what “done” looks like)
	• Calibrate spectra with honest resolution (convolve-down to target LSF), explicit frames (air/vacuum; topocentric/heliocentric/barycentric), and deterministic math.
	• Show calibration state visibly in the UI (banner + badges) and serialize it into export bundles.
	• Provide explainable identification: peak matches, cross-correlation, and per-feature contributions — deterministic, unit-canon safe, and reproducible.

A) Calibration
A1. Service layout (new modules)
app/services/calibration_service.py
app/services/calibration/kernels.py         # Gaussian, Lorentzian, Voigt (FWHM↔sigma helpers)
app/services/calibration/lsf.py             # Target resolution selection, per-instrument defaults
app/services/calibration/frames.py          # Air↔Vacuum, radial velocity, helio/barycentric
app/services/calibration/resample.py        # High-quality resampling (Fourier-safe)
app/services/calibration/uncertainty.py     # Propagate σ through each step

Key data types
# app/services/calibration_service.py
from dataclasses import dataclass
from typing import Literal, List, Dict, Any, Optional
import numpy as np
KernelType = Literal["gaussian", "lorentzian", "voigt"]
FrameType  = Literal["topocentric", "heliocentric", "barycentric"]
MediumType = Literal["air", "vacuum"]
@dataclass(frozen=True)
class TransformStep:
    kind: Literal["lsf_convolve", "frame_shift", "airvac_convert", "velocity_shift"]
    params: Dict[str, Any]           # e.g., {"kernel":"gaussian","fwhm_nm":0.3}
    citation: Optional[str] = None   # Atlas/refs
@dataclass(frozen=True)
class CalibrationPlan:
    target_fwhm_nm: Optional[float] = None
    kernel: KernelType = "gaussian"
    medium: MediumType = "vacuum"
    frame: FrameType = "topocentric"
    radial_velocity_kms: float = 0.0
    convolve_down_only: bool = True   # never sharpen
    steps: List[TransformStep] = None
@dataclass(frozen=True)
class CalibrationResult:
    x_nm: np.ndarray
    y: np.ndarray
    sigma: Optional[np.ndarray]
    applied_steps: List[TransformStep]
Public API
class CalibrationService:
    def plan_from_ui(self, *, target_fwhm_nm: float|None, kernel: KernelType,
                     frame: FrameType, medium: MediumType,
                     rv_kms: float, convolve_down_only: bool) -> CalibrationPlan: ...
def apply(self, spec, plan: CalibrationPlan) -> CalibrationResult:
        """
        spec: Spectrum (canon nm; immutable x)
        1) air/vac conversion (if needed)
        2) radial-velocity / frame shift (Δλ/λ = v/c)
        3) convolve-down to target FWHM (if target < current && convolve_down_only)
        4) resample to canon x grid (never mutate canonical storage)
        Propagate σ, record steps for provenance.
        """
Implementation notes
	• Convolution: FFT-based (NumPy/Scipy), reflect padding, FWHM↔σ helpers. LSF honesty: only widen (never sharpen).
	• Velocity: Δλ/λ = v/c, sign conventions documented.
	• Frames: Air/vacuum conversion (index-of-refraction formula), helio/barycentric offset via provided RV (later you can compute RV from time/location).
	• Resampling: high-quality interpolation that conserves flux if you offer an option (for absorbance/reflectance, a simpler rule is OK; document mode).
	• Uncertainty:
		○ Convolution: σ_y → convolve with |kernel| (energy-conserving).
		○ Shifts/resample: linear propagation via local slopes or resampling of σ.
		○ If no σ provided, keep None but support adding later.

A2. UI — Calibration Manager Dock (new)
app/ui/calibration_dock.py
Controls
	• Target resolution: numeric FWHM (nm or cm⁻¹; UI shows both, stored in nm).
	• Kernel: Gaussian/Lorentzian/Voigt.
	• Convolve down only: checkbox (default on).
	• Medium: Air/Vacuum.
	• Reference frame: Topocentric / Heliocentric / Barycentric + RV (km/s).
	• Apply to: [Active trace] [Selected traces] [All traces].
	• Preview: show predicted broadening on a small inline plot (sampled segment).
	• Apply / Undo last / Reset.
Visible truth
	• Plot banner (non-dismissable status):
LSF: gaussian FWHM=0.30 nm | Frame: heliocentric v=+12.4 km/s | Medium: vacuum | Applied: 3 traces
	• Badges per trace in legend tooltip: applied steps (hover to expand).
Persistence
	• All selections saved in QSettings; last plan restored on launch.

A3. Provenance
Extend your manifest with a calibration block per output spectrum:
"calibration": {
  "applied_steps":[
    {"kind": "airvac_convert", "params": {"to":"vacuum"}, "citation": "Edlén/Peck formula"},
    {"kind": "velocity_shift", "params": {"rv_kms": 12.4, "frame":"heliocentric"}},
    {"kind": "lsf_convolve", "params": {"kernel":"gaussian", "fwhm_nm": 0.30}}
  ],
  "engine": {"version":"app.version","seed": 314159},
  "notes": "Convolve-down only; no sharpening performed."
}
Also add these fields to the export view state (from Pass 2): current display unit, normalization, smoothing, masks, uncertainty toggle, palette, LOD budget.

A4. Tests (pytest)
	• FWHM target: synthetic Gaussian line (σ known) → after convolve-down to target FWHM, fitted width within tolerance (e.g., ±2%).
	• No sharpening: if plan requests target narrower than current and convolve_down_only=True, assert no change + warning.
	• Velocity shift: +30 km/s shift yields expected Δλ; undo returns to original.
	• Air/vac: round-trip within tolerance; never accumulate when toggling UI repeatedly (idempotent).
	• Uncertainty: σ propagates through convolution (L2 norm behaves), resampling preserves monotonicity.
	• Provenance: order of applied_steps == execution order; manifest validates against schema.
	• Performance: calibration on 1e6 points completes within budget (document a threshold).

B) Identification (Explainable)
B1. Service layout (new)
app/services/similarity_service.py
app/services/peak_service.py
app/services/scoring_service.py
Peak detection (deterministic)
@dataclass(frozen=True)
class Peak:
    x_nm: float
    y: float
    prominence: float
    width_nm: float
class PeakService:
    def detect(self, spec, *, min_prominence, min_distance_nm, smoothing=None, seed=13) -> list[Peak]:
        """Uses seeded smoothing (if any) and deterministic rules; returns Peaks"""
Catalog match & cross-correlation
@dataclass(frozen=True)
class LineMatch:
    catalog_x_nm: float
    obs_x_nm: float
    delta_kms: float
    score: float
    id: str     # catalog ID (e.g., H-alpha)
class SimilarityService:
    def match_lines(self, peaks: list[Peak], catalog_nm: np.ndarray,
                    *, tolerance_kms=20.0) -> list[LineMatch]:
        """Velocity-aware nearest-neighbor with tolerance & tie-breaking."""
def cross_correlate(self, spec, template, *,
                        rv_grid_kms: np.ndarray, bandpass=None) -> dict:
        """Returns best_rv, cc_curve, confidence"""
Scoring (explainable)
@dataclass(frozen=True)
class ScoreBreakdown:
    total: float           # 0..1
    weights: dict[str, float]   # {"peaks":0.5,"xcorr":0.4,"consistency":0.1}
    components: dict[str, float]  # {"peaks":0.73,"xcorr":0.81,"consistency":0.66}
    details: dict[str, Any]      # per-line contributions, mismatches, masked regions
    uncertainty: float           # aggregate σ on score
class ScoringService:
    def score(self, matches: list[LineMatch], xcorr, *,
              weights=None, priors=None, mask_intervals=None,
              seed=13) -> ScoreBreakdown:
        """
        - peaks: fraction matched × mean(prominence-weighted agreement)
        - xcorr: normalized peak CC around best_rv (confidence)
        - consistency: agreement across sub-bands & LSF-corrected widths
        Deterministic with a fixed seed where randomness is used (rare).
        """
Determinism
	• Seed once per session (store in manifest).
	• All peak finding uses fixed parameters; any randomness (e.g., bootstrap for σ) is seeded.

B2. UI — Identification Panel (new tab/dock)
Controls
	• Catalog: choose reference (e.g., NIST H, bundled IR functional groups, JWST template).
	• Bandpass: select region(s) for matching.
	• Detection params: min prominence, min distance, smoothing on/off.
	• Velocity search: grid from −300 → +300 km/s (step size configurable).
	• Run Identification.
Outputs (truth-first)
	• Score card: Total score (0–1) with weights visible; green/yellow/red bands.
	• Breakdown table: per-feature contributions (peaks/xcorr/consistency) with σ.
	• Line table: catalog λ, observed λ, Δv (km/s), residual, confidence; click to highlight on plot (snap + marker).
	• Explanations: masked regions and their effect on score; LSF note.
	• Export: identification_report.json + CSV tables inside the main export bundle.
Discoverability
	• “?” buttons that deep-link to user docs Identification & Scoring rubric.

B3. Provenance
Extend manifest with an identification block per run:
"identification": {
  "catalog": {"name":"NIST H lines","version":"2025-10-01","hash":"..."},
  "bandpass_nm": [400.0, 700.0],
  "peak_params": {"min_prom":0.02, "min_dist_nm":0.1, "smoothing":"sg-7"},
  "rv_grid": {"min_kms":-300,"max_kms":300,"step":5},
  "weights": {"peaks":0.5,"xcorr":0.4,"consistency":0.1},
  "score": 0.82,
  "components": {"peaks":0.76,"xcorr":0.88,"consistency":0.71},
  "uncertainty": 0.05,
  "best_rv_kms": 18.7,
  "seed": 13
}

B4. Tests (pytest)
	• Peak detection: synthetic spectra with known peaks → correctness (positions, widths) + determinism with seed.
	• Line matching: jittered peaks vs catalog with known RV; matches within tolerance; Δv signs consistent.
	• Cross-correlation: template vs shifted observation — best RV equals injected shift ± step/2; confidence monotonic around best.
	• Scoring: controlled cases (perfect match, partial mask, wrong catalog) → expected ordering: perfect > partial > wrong.
	• Explainability: components sum (with weights) to total ± ε; per-feature tables non-empty; masked regions reduce score predictably.
	• Performance: 1e6 points → peak detect + xcorr finish under documented budget with LOD active.
	• Provenance: all inputs/params/seed serialized; JSON schema validates.

C) Functional-Group Prediction (IR) — link to Identification
You already show IR functional-group overlays. Wire an optional predictor behind a feature flag:
	• Service: app/services/ml_service.py
		○ predict_functional_groups(spec, bandpass=None) -> list[Annotation] (each with center, span, label, confidence, model/version/hash).
	• UI: “Identify functional groups” checkbox in the Identification panel. Adds annotations and a short table to the breakdown.
	• Provenance: include model metadata & commit/weights hash.
	• Tests: deterministic mock model; thresholding + annotation count stable.

D) Docs to add/update
	• docs/user/calibration.md — step-by-step with screenshots; LSF banner explained.
	• docs/user/identification.md — how scores are built; how to interpret Δv, masks, uncertainty ribbons.
	• docs/dev/calibration.md — kernel math, propagation rules, test oracles.
	• docs/dev/identification.md — algorithm choices, edge cases, determinism guarantees.
	• docs/specs/provenance_schema.json — updated with calibration and identification blocks.
	• Update Atlas chapters references at the bottom of each doc section you touch (so future agents ricochet back to the canon).

E) Performance & safety
	• Prefer FFT convolution with reflect padding; optional pyFFTW if available.
	• Use viewport-aware decimation from Pass 2 so scoring & xcorr can operate on reduced representations when appropriate (but always fall back to full-res for export or when the user requests exact).
	• Guard optional dependencies; never crash. Provide clear error strings & remediation.

F) Suggested sprint plan
	1. Calibration foundation
		○ Implement services + UI dock + provenance serialization + tests.
		○ Deliver visible LSF banner + frame badge.
	2. Identification v1
		○ Peaks + line match + xcorr + scoring + explain panel + provenance.
		○ Minimal IR predictor hook (feature-flagged).
	3. Docs & schema
		○ User + dev docs, schema update, in-app help links.
		○ Teaching examples (Atlas campus datasets).
	4. Perf & polish
		○ Cache decimated segments for xcorr; tune RV grid step; finalize budgets.

Open choice that needs an RFC (later)
	• Engine API seam (so a future React/Tauri UI could call the calibration & identification services). Extracting a thin app/engine/api.py will de-risk any future UI decision without changing the current desktop experience.
