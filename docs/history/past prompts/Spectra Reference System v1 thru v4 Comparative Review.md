# Spectra Reference System: v1–v4 Comparative Review

**Scope.** This review compares four internal iterations of the Spectra “reference” subsystem across data model, API surface, UI affordances, provenance, testing, and risk. It also lays out how to replace any synthetic or digitized values with verifiable upstream data from NIST and JWST/MAST.

**External sources used for the “no-synthetic data” plan**

* NIST Atomic Spectra Database (ASD) for hydrogen lines. ([NIST WebBook][1])
* NIST Chemistry WebBook for IR band ranges. ([Astroquery][2])
* MAST + astroquery for fetching JWST data programmatically. ([NIST][3])
* JWST field-of-regard/operations restrictions (context for “no Earth” entries). ([jwst-docs.stsci.edu][4])
* STScI JDAT/JWST analysis notebooks (tooling baseline). ([GitHub][5])

---

## Executive recommendation

**Start from v3.**
It has the most useful **UI (searchable Reference tab)**, a **clean JSON data layer** that’s easy to regenerate from real sources, and **tests** that touch both service and UI. Migrating v3 off synthetic/digitized snippets is straightforward: swap JSON payloads with data ingested from ASD/MAST via small build scripts, keep the same schema, and your UI just works. v4 is tidy but regresses the Reference UI to a status-bar count; v1 is menu-centric and tightly coupled; v2 keeps data in code, which makes provenance and updates clumsier.

---

## Side-by-side snapshot

| Dimension            | **v1: ReferenceCatalog**                                                                    | **v2: ReferenceLibrary (code-embedded)**                          | **v3: ReferenceLibrary (JSON assets + Reference tab)**                            | **v4: ReferenceDataService (typed modules)**                         |
| -------------------- | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| Storage              | Single JSON under `app/services/data/reference_catalog.json`                                | Data embedded in Python (dataclasses/constants)                   | Multiple JSONs under `app/data/reference/*.json` (hydrogen, IR, JWST, line-shape) | Python modules in `app/data/*.py` exporting dataclasses/tuples       |
| API                  | `ReferenceCatalog` creates loadable `Spectrum`s; menu-based loader                          | `ReferenceLibrary` returns structured rows for UI; no asset files | `ReferenceLibrary` loads JSON, returns dicts; filter helper                       | `ReferenceDataService` returns typed sequences; summary inventory    |
| UI surfacing         | New **Reference menu**; inspector metadata fields (units, resolution, instrument, citation) | Inspector gained a **Reference** view (tree/table)                | Full **Reference tab**: searchable table + citation pane; **Docs tab**            | Only status-bar inventory counts; no dedicated Reference tab         |
| Provenance/metadata  | Strong: original units, resolution, instrument, citation plumbed into inspector             | Good: series/IDs/notes present; less explicit about external URLs | Strong: metadata blocks per dataset; citations shown; rich JWST entry notes       | Good: per-dataset citations in code; fewer UI hooks by default       |
| JWST data            | Small downsampled snapshots; synthetic-ish                                                  | Embedded samples; likely synthetic-ish                            | JSON “quick-look” digitized points; “Earth: not_observed” entry                   | Embedded samples; Earth restriction noted                            |
| Hydrogen lines       | NIST-derived; decent fields                                                                 | NIST-derived in code; Rydberg constants referenced                | NIST JSON with wavelengths, wavenumbers, A-values, uncertainties                  | NIST in code, plus series metadata and energies                      |
| IR functional groups | Present; brief                                                                              | Present; brief                                                    | Present with ranges/intensity/modes                                               | Present with tidy dataclass ranges                                   |
| Tests                | `tests/test_reference_catalog.py` (service + metadata + units)                              | `tests/test_reference_library.py`                                 | `tests/test_reference_library.py` + UI smoke exercising Reference tab             | `tests/test_reference_data_service.py` (typed API + summary)         |
| Docs                 | Primer + data sources + catalog doc + patch notes                                           | Service notes + usage                                             | Rich user+dev docs; browser in-app; patch notes & workplan                        | Dev resources + user reference; patch/workplan; status bar mention   |
| Coupling             | Higher: service creates `Spectrum` objects directly                                         | Medium: service → UI                                              | Low: JSON assets decoupled; service is loader                                     | Low: typed data service, but no Reference tab UX                     |
| What it does well    | Inspector metadata, menu flow; explicit units                                               | Simple API; fewer moving parts                                    | Best UX for references; clean asset boundary; filter/search                       | Clean typing; small surface; status inventory                        |
| What it doesn’t      | No searchable Reference tab; catalog JSON lives under `services/`                           | Data trapped in code; refresh means code change                   | JWST values digitized; no fetchers; some duplicated per-row keys                  | Lost Reference tab; less discoverability; update requires code edits |
| Biggest risk         | Mixing “demo spikes” with real data in same path                                            | Harder provenance auditing; PRs become code diffs for data        | “Digitized quick-look” not audit-grade; data drift                                | UX regression; data churn requires release not content update        |

---

## Per-version deeper read

### v1

* **Applies:** Bundled NIST/JWST/IR; Reference menu; inspector exposes original units, resolution, instrument, citation; Spectrum factory now accepts explicit `x_unit`, `y_unit`; tests cover catalog creation and metadata.
* **Doesn’t apply:** No searchable Reference tab; data and code cohabitate under `services`, which muddies layering.
* **Does well:** End-to-end flow from menu → overlay → inspector, with good provenance fields.
* **Issues:** JWST snippets are downsampled and likely not traceable to an upstream artifact; catalog file path under `services/` is awkward; coupling to `Spectrum.create` makes stubbing harder.
* **Improve:** Move assets out of `services` into `app/data/…`; add a Reference tab; introduce fetch/build scripts; split demo spikes from authoritative references.

### v2

* **Applies:** Introduces a `ReferenceLibrary` with data embedded in Python dataclasses; inspector has a Reference view; tests validate hydrogen and IR content.
* **Doesn’t apply:** No externalized assets; updates require code diffs; limited JWST coverage; fewer UI affordances than v3.
* **Does well:** Minimal dependencies; fast import; simple unit testing.
* **Issues:** Hard provenance story because data lives in code; PR review diffs are noisy; ramp to non-synthetic data is higher.
* **Improve:** Externalize data; attach URLs/DOIs; add a loader abstraction so embedded data can be replaced by asset files.

### v3

* **Applies:** Splits data into **JSON assets** for hydrogen, IR groups, JWST quick-look spectra, and line-shape placeholders; builds a **searchable Reference tab** with filter and citation pane; extends in-app docs; adds UI smoke asserting the Reference tab renders; keeps tests for dataset semantics.
* **Doesn’t apply:** No ingestion scripts from real sources; JWST numbers are still digitized quick-look values rather than archive-grade FITS traces.
* **Does well:** Best user experience and separation of concerns; JSON is easy to regenerate; strong metadata, including “not_observed” Earth entry for clarity.
* **Issues:** “Digitized for reference” is not great for science or reproducibility; ensuring value drift over time requires a build step.
* **Improve:** Add build scripts to generate JSON from ASD/MAST and publish the scripts plus checksums; enrich JSON schema with DOIs and processing notes.

### v4

* **Applies:** Refactors to **typed Python modules** (`app/data/*.py`) and a `ReferenceDataService`; shows **status-bar inventory**; docs and tests updated.
* **Doesn’t apply:** Drops the rich Reference tab from v3; doesn’t ship fetchers; still uses curated samples in code.
* **Does well:** Clean typing; centralized service; simple summary for diagnostics.
* **Issues:** Discoverability regression; editing data requires code change; still no authoritative fetch path.
* **Improve:** Re-introduce the v3 Reference tab on top of v4’s service, or keep v3’s JSON boundary and layer typing during load.

---

## Where synthetic or digitized data lurk and why that bites

* **JWST “quick-look” points**: values were digitized from press graphics. They’re fine for demos, but not for reproducible analysis. Replace with **calibrated products from MAST**; the astroquery MAST client and JDAT tooling exist for this exact purpose. ([NIST][3])
* **IR ranges**: qualitative ranges are acceptable if directly cited, but they should match a stable reference like the **NIST Chemistry WebBook** or a standard handbook and carry explicit citation text and retrieval date. ([Astroquery][2])
* **“Earth” placeholder**: keep the entry, but back it with a citation to JWST operations restrictions/field of regard to avoid confusion. ([jwst-docs.stsci.edu][4])
* **Hydrogen lines**: use ASD wavelengths, wavenumbers, A-values straight from **NIST ASD** with the exact version string and link in the metadata. ([NIST WebBook][1])

---

## Concrete path to “no synthetic data” (keep v3 as base)

1. **Add build scripts** under `tools/reference_build/`:

   * `build_hydrogen_asd.py`: query/download NIST ASD hydrogen lines, export to `app/data/reference/nist_hydrogen_lines.json` with full citation, version, and retrieval UTC. ([NIST WebBook][1])
   * `build_ir_bands.py`: scrape or transcribe from NIST WebBook or a citable handbook; store ranges with references and notes to uncertainty. ([Astroquery][2])
   * `build_jwst_quicklook.py`: use `astroquery.mast.Observations` to find the program/product IDs, download a small calibrated FITS (or extract a narrow spectral segment), resample to a handful of points for UI, and write `app/data/reference/jwst_targets.json` with `provenance` fields (program, instrument, pipeline version, product URI). ([Astroquery][6])
2. **Schema upgrades** to v3 JSON:

   * Add `provenance`: `{ doi?, mast_product_uri?, mast_obsid?, pipeline_version?, processing_date?, sha256? }`
   * Add `source.license` when available.
   * Keep per-point units and uncertainty keys untouched so the existing Reference tab renders without code changes.
3. **CI checks**:

   * Validate that JSONs were generated by the scripts by re-computing `sha256` of the source FITS segment and matching embedded digests.
   * Assert ASD version string and retrieval timestamp are present for hydrogen.
4. **Tests**:

   * Replace any tests that key off synthetic values with tolerances against the sampled real data.
   * Keep UI smoke test from v3 to ensure the Reference tab still loads tables and citations.
5. **Docs**:

   * In `docs/user/reference_data.md`, replace “digitized” language with “resampled from calibrated MAST product,” include program IDs and links, and note resampling method.
6. **Keep the “Earth” row** with a direct link to the JWST operations restriction docs for clarity. ([NIST][7])

> Why v3 and not v4?
> v3 already externalizes content as JSON and ships a working Reference browser. The swap from digitized to resampled real data is a **data rebuild**, not a **code refactor**. With v4, you’d either re-introduce a Reference tab or keep stuffing data into code. Pick the path of least drama.

---

## Risk register and mitigations

* **Data drift (MAST reprocessing)**: pipeline versions change. Embed `pipeline_version` and `productID` from MAST; pin tests to specific product URIs. ([NIST][3])
* **Licensing/redistribution**: many JWST products are public; still include upstream links/attribution and avoid re-hosting large files. Keep only small resampled tables.
* **Unit confusion**: JWST products vary in units. Persist `data_units` and original FITS header keywords in metadata; show in the Reference tab. JDAT guidelines help here. ([jwst-docs.stsci.edu][8])
* **Hydrogen constants**: don’t hand-roll constants; cite ASD and record version/date. ([NIST WebBook][1])
* **IR ranges variability**: ranges are context-dependent. Mark them as heuristic with source and add uncertainty notes. ([Astroquery][2])

---

## Minimal migration plan (v3 → v3-real)

1. Keep **all v3 UI and service code**.
2. Add the `tools/reference_build/*` scripts and run them to regenerate JSON.
3. Commit regenerated JSON + checksums.
4. Update docs to remove “digitized/demo” language and add citations and DOIs.
5. Extend tests to assert presence of `provenance` keys and non-zero uncertainties where expected.

---

## Appendix: Quick capability matrix

* **Searchable reference browser:** v3 ✅, v1/v2 partial, v4 ❌
* **Clean data boundary:** v3 ✅ (JSON), v4 ⚠️ (code), v1 ⚠️ (JSON under services), v2 ❌ (code)
* **Provenance fidelity:** v3 ≥ v1 > v4 ≥ v2
* **Ease of swapping in real data:** v3 ✅, v1 ⚠️, v4 ⚠️, v2 ❌

---

## References

* NIST Atomic Spectra Database (ASD) hydrogen lines and metadata. ([NIST WebBook][1])
* NIST Chemistry WebBook IR bands and functional group ranges. ([Astroquery][2])
* MAST archive docs and astroquery MAST API for reproducible JWST access. ([NIST][3])
* JWST field-of-regard and operations restrictions (why Earth isn’t available). ([jwst-docs.stsci.edu][4])
* STScI JDAT notebooks and tooling overview for post-pipeline analysis. ([GitHub][5])

---

### Final pick

Proceed with **v3 as the base** and execute the “no-synthetic data” plan above. You keep the good UI and the clean data boundary, and you swap the contents for traceable, citable, reproducible upstream data. Everyone wins, including your conscience.

[1]: https://webbook.nist.gov/?utm_source=chatgpt.com "Welcome to the NIST WebBook"
[2]: https://astroquery.readthedocs.io/en/latest/mast/mast.html?utm_source=chatgpt.com "MAST Queries (astroquery.mast) - Read the Docs"
[3]: https://www.physics.nist.gov/PhysRefData/ASD/Html/verhist.shtml?utm_source=chatgpt.com "Atomic Spectra Database - Version History - NIST"
[4]: https://jwst-docs.stsci.edu/methods-and-roadmaps/jwst-moving-target-observations/jwst-moving-target-supporting-technical-information/moving-target-field-of-regard?utm_source=chatgpt.com "Moving Target Field of Regard - JWST User Documentation"
[5]: https://github.com/spacetelescope/jdat_notebooks?utm_source=chatgpt.com "JWST Data Analysis Tools Notebooks"
[6]: https://astroquery.readthedocs.io/en/latest/api/astroquery.mast.ObservationsClass.html?utm_source=chatgpt.com "ObservationsClass — astroquery v0.4.12.dev235"
[7]: https://physics.nist.gov/PhysRefData/ASD/lines_form.html?utm_source=chatgpt.com "NIST: Atomic Spectra Database Lines Form"
[8]: https://jwst-docs.stsci.edu/jwst-post-pipeline-data-analysis?utm_source=chatgpt.com "JWST Post-Pipeline Data Analysis"
