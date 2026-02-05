# Pass 1 — Atlas vs Code Alignment (2025-10-17T00:00:00Z)

This pass compares the Atlas expectations with the current codebase to surface
capability gaps and quick wins.

## Strengths Observed
- Unit canon respected across ingest/export services.
- Importers cover CSV/TXT, FITS, JCAMP-DX with provenance capture.
- Remote catalogue scaffolding exists for NIST ASD and MAST.
- Plot LOD and palette controls maintain responsiveness.

## Gaps & Actions
1. **Calibration Manager** — Build a dedicated service + UI for LSF/frames/RV.
2. **Uncertainty Ribbons** — Propagate σ through transforms and plot ribbons.
3. **Explainable Scoring** — Deterministic peak/line matching with weighted
   scores.
4. **Engine API Seam** — Prepare for potential native/remote clients.
5. **ML Tagging** — Optional, document-only exploration for spectrum labelling.
6. **Packaging Hygiene** — Audit installers, manifests, and dependency pins.

## Quick Wins
- Regroup Inspector controls to surface spectroscopy-first tasks.
- Produce a documentation map linking atlas → brains → knowledge log.

## References
- `docs/atlas/0_index_stec_master_canvas_index_numbered.md`
- `docs/brains/README.md`
- `docs/history/KNOWLEDGE_LOG.md`
