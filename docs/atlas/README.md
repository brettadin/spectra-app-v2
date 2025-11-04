## Atlas

This directory hosts curated narratives and references that provide the domain context for Spectra (spectroscopy, instrumentation,
workflows, provenance). Treat it as deeper reading that informs user guides and design decisions.

Notes:
- Content evolves; it may contain inaccuracies. Improve entries as you work and cross-link changes to specs/user guides.
- Reference Atlas entries in code comments and docs when they provide important context.
- When you spot issues, flag them in the file and add an item to `docs/reviews/inbox.md` for triage.

### Anchor naming and cross-linking

To make Atlas discoverable from the app and user guides, add stable anchors to relevant sections.

- Use lower-kebab-case slugs, scoped by topic. Examples:
	- `#units-signed-log-transform`
	- `#calibration-fwhm-kernels`
	- `#identification-peak-scoring`
- Prefer short one-line section headings with meaningful slugs.
- Maintain a short anchor appendix here for link checking (add more as needed):

Anchors (seed list):
- Units and conversions — `#units-signed-log-transform`
- Normalization — `#normalization-global-vs-per-spectrum`
- Calibration — `#calibration-fwhm-kernels`
- Overlays — `#overlays-nist-anchoring-and-scaling`

### Contribution & anchor workflow

To keep links stable and discoverable from the app and guides:

1. Add or update a short section with a meaningful heading; keep it concise.
2. Ensure the heading slug matches the lower-kebab-case convention (see above).
3. Register the anchor in `docs/atlas/anchors.yml` with a short description and file path.
4. Cross-link from user guides and UI inline help (`?`) using the registered anchor.
5. When moving or renaming sections, update `anchors.yml` and run the link checker (planned) before merging.

### Suggested contributions
- Add “Further reading” targets for user guides (units, normalization, calibration, overlays, identification).
- Cite primary sources (DOIs/URLs) in Atlas chapters when theory or data choices are discussed.
- Keep Atlas entries concise; move procedural details to user guides and stable contracts to `docs/specs/`.

### Recent architectural note

See `docs/brains/2025-10-18T0924-remote-data-ux.md` for a short design note
about remote-data provider availability, optional dependencies, and the
resulting UI decisions (provider annotations and knowledge-log hygiene).
