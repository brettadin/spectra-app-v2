# Project Roadmap and Milestones

The Spectra desktop reboot has cleared its core PySide6 milestones and now tracks progress against the active workplan batches.
This roadmap summarises what is already in production, highlights the near-term documentation and UX pushes, and captures the
strategic initiatives that remain on the horizon. Use the embedded cross-links to jump straight to the owning tasks inside the
[Batch 13 workplan](../docs/reviews/workplan.md#workplan--batch-13-2025-10-15) and the
[Batch 10 backlog](../docs/reviews/workplan.md#workplan--batch-10-backlog).

## Delivered Platform Milestones

Recent development cycles focused on stabilising the Inspector workspace, toolbar controls, and reference overlays. These items
are complete and provide the foundation for ongoing UX and documentation work.

- **PySide6 dock layout refresh.** The Inspector pane now restores reliably with deduplicated docks, eliminating the Windows
  startup glitches tracked in [Batch 13](../docs/reviews/workplan.md#workplan--batch-13-2025-10-15). The docking model keeps
  overlay previews, importer summaries, and documentation tabs in a predictable layout for operators.
- **Persistent plot toolbar.** The normalisation/unit controls are exposed through the plot toolbar toggle and View menu, with
  state persistence between sessions. This shipped alongside regression coverage and documentation hooks closed out in
  [Batch 13](../docs/reviews/workplan.md#workplan--batch-13-2025-10-15) and [Batch 11](../docs/reviews/workplan.md#workplan--batch-11-2025-10-15).
- **Reference overlay system.** Hydrogen lines, IR functional groups, and JWST quick-look spectra can be previewed inside the
  Reference tab and synchronised with the main plot. These overlays were delivered through
  [Batch 8](../docs/reviews/workplan.md#workplan--batch-8-2025-10-15),
  [Batch 9](../docs/reviews/workplan.md#workplan--batch-9-2025-10-15), and
  [Batch 11](../docs/reviews/workplan.md#workplan--batch-11-2025-10-15).

Together these milestones unblock importer hardening, reference provenance tracking, and UX polish for upcoming releases.

## Near-Term Documentation and UX Focus

The next several sprints emphasise documentation catch-up and operator experience refinements. Each item lines up with open
checkboxes in [Batch 13](../docs/reviews/workplan.md#workplan--batch-13-2025-10-15).

- **Importer heuristics documentation.** Capture the CSV/TXT/FITS axis-detection logic, noisy QA dataset fixtures, and heuristics
  rationale in the importer guides. Ensure the content is referenced from the Knowledge Log and importer metadata notes.
- **Multi-file overlay walkthroughs.** Expand `docs/user/reference_data.md` with the combined ingest + overlay workflow so QA can
  validate hydrogen, IR, and JWST overlays after loading multiple samples.
- **Knowledge Log backfill.** Record the Inspector, toolbar, and overlay fixes in `docs/history/KNOWLEDGE_LOG.md` to maintain
  traceability for release sign-off.
- **Overlay polish and accessibility.** Tighten legend callouts, tooltip contrast, and screenshot updates across the user guides
  to reflect the refreshed PySide6 layout. This encompasses the documentation refresh tasks in Batch 13 and feeds future QA runs.
- **Qt-enabled CI guidance.** Draft the documented recipe (or CI configuration) for running the Qt-dependent UI tests without
  skips, improving confidence before the next release candidate.

## Strategic Horizons

Longer-term initiatives remain tracked in the [Batch 10 backlog](../docs/reviews/workplan.md#workplan--batch-10-backlog) and will
re-enter the active queue once the documentation/UX push wraps.

- **Physics-aware line-shape modelling.** Introduce Doppler, pressure, and Stark broadening parameters into the overlay service so
  users can compare physical models against imported spectra. Document default coefficients and extend regression coverage for
  canonical scenarios.
- **JWST pipeline ingestion.** Replace the digitised quick-look tables with calibrated FITS retrievals tied to the official JWST
  pipeline, preserving provenance metadata and automating updates when new releases land.
- **Expanded reference catalogues.** Broaden beyond hydrogen to include helium, oxygen, and iron lines, plus richer IR functional
  group definitions. Align catalogue growth with importer safeguards (netCDF/HDF5) and documentation updates.

These goals depend on the stability work above and will be prioritised once Batch 13 is fully closed out.
