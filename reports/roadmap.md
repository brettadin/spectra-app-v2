# Project Roadmap and Milestones

The original four-week reboot plan has been retired now that `spectra-app-beta` ships hardened importer
heuristics, reference overlays, and a growing documentation suite. This roadmap captures the refreshed
priorities that build on today’s feature baseline while tracking strategic research targets for the next
iterations.

## Current Snapshot (October 2025)

- CSV/TXT ingestion handles axis heuristics, normalization, and caching regressions with regression tests in
  place, while FITS/JCAMP and remote fetchers remain backlog items.
- Reference overlays span NIST hydrogen lines, IR functional groups with anchored bands, and digitised JWST
  quick-look spectra, backed by provenance-rich JSON assets and UI regression coverage.
- User documentation covers quickstart flows, unit conversions, importing, plot tooling, and in-app reference
  usage, with patch notes capturing major behavioural changes.

## Near-Term Priorities (Next 1–2 Sprints)

1. **Importer expansion**
   - Implement FITS and JCAMP parsers with unit preservation and provenance capture, guided by the historic
     launch-debugging checklist.
   - Extend the layout cache validation and heuristics to reuse IR functional-group knowledge for axis scoring.
2. **Remote archive integration**
   - Stand up a "Remote Data" dialog that fronts NIST, ESO, SDSS, and planned JWST/MIRI fetchers with dependency
     guards and local caching.
   - Record provenance for remote downloads (checksums, timestamps, source URLs) alongside imported spectra.
3. **Inspector enrichment**
   - Populate metadata/provenance tabs with transformation logs, add math operations (difference/ratio) with
     shared-grid resampling, and expose style controls for smoothing and normalization.
4. **Documentation sweep**
   - Refresh screenshots and guidance for the anchored IR overlays, importer safeguards, and remote-download
     workflows as they land.

## Documentation & Knowledge Sharing

- Maintain the Batch workplan as the canonical tactical backlog, cross-linking tasks to regression tests and
  updated documentation.
- Transcribe historic PDF reviews and QA notes into searchable Markdown (e.g., the launch-debugging summary) so
  agents can cite original expectations when planning feature work.
- Keep patch notes current for user-visible changes and tie each entry to the updated guides to minimise drift.

## Future Horizons (Post-1.0 Research Track)

- **Calibrated JWST ingestion:** Replace digitised overlays with automated MAST retrieval pipelines, storing the
  provenance and regenerating reference assets in CI.
- **Physics-aware overlays:** Implement Doppler, pressure, and Stark broadening models using the placeholder
  scaffolding and extend importer heuristics to exploit the new metadata.
- **Catalogue expansion:** Broaden the reference library beyond hydrogen (e.g., He I, O III, Fe II) and integrate
  IR functional-group heuristics into importer validation to improve axis selection across new datasets.
- **Advanced analytics:** Revisit similarity search, machine-learning assisted classification, plugin ecosystems,
  and accessibility improvements once the ingestion and provenance foundations solidify.

## Measuring Progress

- Continue running the pytest regression suite locally for each batch and expand with targeted GUI tests when new
  plot interactions or importer pathways are introduced.
- Track documentation updates alongside code changes in the workplan so releases always ship with aligned guides,
  screenshots, and patch notes.
