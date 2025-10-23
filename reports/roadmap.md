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

1. **Remote Data reliability + Quick Plot**
   - Keep astroquery MAST path, but add fallback via MAST Download API when needed (done). Wire a "Quick Plot" button using new in-memory ingest.
   - Expand curated ExoSystems targets and grouping by mission/instrument/target; visualize wavelength coverage.
2. **Importer breadth (FITS/JCAMP)**
   - Multi-extension FITS selection; broaden column aliases (STIS/IUE/NICMOS/JWST); WCS spectral axis detection where available.
   - Improve error messages with available column lists (done) and unit preservation.
3. **Provenance and citations**
   - Auto-extract citations from remote metadata into manifests; surface inline in preview and provenance UI.
4. **Documentation sweep**
   - Keep `docs/dev/worklog` (daily narratives) and `docs/reviews/workplan.md` (batch tracker) up to date; maintain neurons in `docs/brains`; extend `docs/atlas/*` where new flows are added.

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
