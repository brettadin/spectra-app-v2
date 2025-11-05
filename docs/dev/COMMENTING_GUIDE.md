# Commenting & Docstrings Guide (Spectra)

A consistent commenting style makes this repo easier to navigate and maintain. This guide defines what to document and how, with
examples tailored to our PySide6 + services architecture.

---

## Principles
- Explain intent and contract, not obvious mechanics. Focus on inputs/outputs, invariants, and edge cases.
- Keep public APIs and cross-module entry points fully documented; private helpers get brief comments where non-obvious.
- Document units, normalization state, and provenance-impacting behavior explicitly.
- Avoid duplicating business logic in comments; prefer linkbacks to specs or docs.

## Module headers
Each Python module should start with a short docstring:
- What the module provides (1–3 sentences)
- Contracts or invariants (bulleted)
- Any side effects or environment dependencies
- Pointers to relevant specs/docs

Example:
"""Display-time pipeline for the plot: calibration → normalization → Y-scale.
Invariants:
- X is canonical nm internally; conversions applied at the edges.
- Normalization scales ignore NaN/Inf when computing factors.
Refs: docs/specs/units_and_conversions.md, docs/user/plot_tools.md
"""

## Class docstrings
Include:
- Purpose and role in the app
- Key configuration options and defaults
- Signals/slots (for Qt classes)
- Threading/async notes (if applicable)

## Function/method docstrings
Use a concise one-liner + args/returns. Call out:
- Units of all values (nm, Å, µm, cm⁻¹; raw vs normalized y)
- Error modes (raises vs returns None/flags)
- Performance considerations (vectorized, large-N safeguards)

Example:

def apply_y_scale(y: np.ndarray) -> np.ndarray:
    """Apply current Y-scale transform (Linear|Log10|Asinh) to normalized y.
    Args:
        y: 1D array of post-normalization values (NaN-preserving)
    Returns:
        Transformed array suitable for display (shape=y.shape).
    Notes:
        Do not mutate the input; keep transforms monotonic and invertible where possible.
    """

## Inline comments
- Use sparingly to explain why a non-obvious step exists (workaround, perf guard, domain nuance).
- Prefix with TODO: for planned improvements tied to backlog links.
- For temporary hacks during cleanup, add a removal condition and workplan reference.

Example:
# TODO(workplan_backlog.md#live-readout-enhancements): add pre-scale y alongside transformed value when non-linear

## Cross-references
- Link to `docs/specs/*` for contracts and `docs/reviews/*` for orchestration.
- When behavior changes, update the relevant guide and add a patch note.

## Tests as docs
- For algorithms (peak finders, centroid/FWHM/EW), write small gold tests. Reference test names in docstrings where helpful.

## Linting/CI
- Prefer ruff or pydocstyle-compatible docstrings (no hard enforcement yet). Keep lines reasonably short and readable.

---

Adopt this guide gradually. When you touch a file, leave it better documented than you found it.
