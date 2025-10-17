# Spectroscopy Reference Link Collection

This index highlights the external catalogues, standards, and in-repo guides
that future agents should consult while extending the Spectra desktop preview.
Each entry includes a short note describing when it is relevant.

## Core astrophysical catalogues

| Resource | URL | Notes |
| --- | --- | --- |
| NIST Atomic Spectra Database | https://physics.nist.gov/PhysRefData/ASD/lines_form.html | Ground-truth oscillator strengths, energy levels, and line classifications used by the bundled hydrogen lists and any future species builds. |
| MAST Portal (Barbara A. Mikulski Archive for Space Telescopes) | https://mast.stsci.edu/portal/Mashup/Clients/Mast/Portal.html | Source for JWST calibrated spectra and other mission products; cross-reference with `tools/reference_build/jwst_targets_template.json`. |
| NASA Exoplanet Archive | https://exoplanetarchive.ipac.caltech.edu/ | Transit spectra, stellar parameters, and reference metadata useful when expanding target catalogues or validating atmospheric retrievals. |
| ESO Science Archive | https://archive.eso.org/ | Ground-based spectra (UVES, HARPS, etc.) for comparative analysis against laboratory baselines. |

## Laboratory technique primers

| Technique | Primer | Why it matters |
| --- | --- | --- |
| UV-Vis Spectroscopy | https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Supplemental_Modules_(Analytical_Chemistry)/Instrumental_Analysis/Spectroscopic_Methods/Ultraviolet-Visible_Spectroscopy/Principles_of_UV-Visible_Spectroscopy | Guides axis conventions and absorbance vs. transmittance conversions when ingesting lab data. |
| Infrared Spectroscopy | https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Supplemental_Modules_(Analytical_Chemistry)/Instrumental_Analysis/Spectroscopic_Methods/Infrared_Spectroscopy | Supports the IR functional-group heuristics used during CSV imports. |
| Mass Spectrometry | https://chem.libretexts.org/Bookshelves/Analytical_Chemistry/Supplemental_Modules_(Analytical_Chemistry)/Instrumental_Analysis/Mass_Spectrometry | Future roadmap item for integrating mass-spec peak picking alongside optical spectra. |
| ICP-MS Fundamentals | https://www.thermofisher.com/blog/analytical/fundamentals-of-icp-ms/ | Reference for elemental abundance workflows once plasma/ionisation data products are introduced. |

## Internal project wayfinding

- `START_HERE.md` — Onboarding sequence linking to build/run instructions and the primary architecture overviews.
- `docs/atlas/` — Component-level diagrams (UI wiring, services, data flows) that pair with `docs/brains/` deep dives.
- `docs/user/` — User-facing guides including importing, remote data, reference library usage, and in-app documentation.
- `docs/dev/reference_build.md` — Provenance and regeneration steps for curated datasets (JWST quick look, IR bands, etc.).
- `docs/history/KNOWLEDGE_LOG.md` — Narrative changelog for significant insights; now reserved for summarising major features rather than routine imports.
- `docs/reviews/workplan.md` — Current roadmap, batching plan, and QA checkpoints; update this as tasks are completed.
- `tools/reference_build/` — Scripts for refreshing catalogues; review before adding new species or regenerating JWST assets.

## Usage tips for agents

1. Review `docs/link_collection.md` (this file) alongside `docs/history/PATCH_NOTES.md` before picking up a task to maintain continuity.
2. When working on remote data features, consult `docs/user/remote_data.md` for UI expectations and `app/services/remote_data_service.py` for dependency guards.
3. Keep the Knowledge Log focused on high-level learnings; routine imports should surface through the Library dock instead.
4. Log new resources or major process changes here so the next agent inherits an up-to-date research trail.
