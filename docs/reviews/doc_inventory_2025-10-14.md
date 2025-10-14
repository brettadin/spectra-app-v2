# Documentation Inventory — 2025-10-14

## Purpose

This inventory captures the documentation gaps that remain before the next
feature sprint. It compares the requirements from the master product prompt
with the current contents of `docs/` and identifies concrete follow-up tasks.

## Summary of Required Deltas

- Establish a **user handbook set** covering units/conversions, plot tools,
  and provenance/export workflows.
- Flesh out the **developer knowledge base** with provenance schema details,
  testing workflow guidance, and feature flag conventions.
- Expand **history/process artifacts** so recurring workplans and release
  cadence are traceable from the repository alone.

## User-Facing Documentation

| Theme | Gap | Suggested Artifact |
| --- | --- | --- |
| Units & conversions | No dedicated user walkthrough for nm/Å/µm/cm⁻¹ toggles or idempotent behaviour expectations. | `docs/user/units_and_conversions.md` outlining the toggle UI, mathematical relationships, and troubleshooting. |
| Plot interaction | Lack of instructions for LOD behaviour, crosshair usage, and export snapshots. | `docs/user/plot_tools.md` describing interactive controls, performance tips, and limitations (e.g., anti-alias defaults). |
| Provenance exports | Existing importing guide does not explain manifest bundle contents or citation expectations. | Section or standalone page (e.g., `docs/user/provenance.md`) covering export manifests, citation formats, and how raw files are preserved. |

## Developer Documentation

| Theme | Gap | Suggested Artifact |
| --- | --- | --- |
| Provenance schema | No developer-facing specification for the manifest JSON structure or expected metadata fields. | `docs/dev/provenance_schema.md` documenting keys, sample payloads, and extension rules. |
| Feature flags | Lacking guidance on introducing gated providers/services and their default-off expectations. | Add section to `docs/dev/ingest_pipeline.md` or a new `docs/dev/feature_flags.md`. |
| Test strategy | Current CI guide lists commands but not fixtures, random seeds, or coverage expectations. | Expand `docs/dev/ci_gates.md` with deterministic-testing practices and coverage requirements. |
| Data fixtures | No canonical location policy for generated FITS/JCAMP fixtures or runtime generation helpers. | Brief note in `docs/dev/testing_fixtures.md` describing fixture strategy and generation at runtime. |

## History & Process Artifacts

- **Workplan hygiene**: Continue appending batches in `docs/reviews/workplan.md`
  with completion notes and link them back to inventories like this document.
- **Patch cadence**: Ensure `docs/history/PATCH_NOTES.md` receives an entry for
  each working day summarising both code and documentation deltas.
- **AI/dev logs**: Resume updates to `docs/history/KNOWLEDGE_LOG.md` or
  `docs/ai_log/` so rationale for documentation priorities is recorded.

## Next Steps

1. Prioritise authoring the user-facing unit/plot/provenance guides so the
   application UI contract is discoverable without reading source code.
2. Draft the provenance schema reference in tandem with any upcoming exporter
   enhancements to keep the manifest authoritative.
3. Backfill test and fixture documentation before adding new ingest or fetch
   providers, ensuring contributors understand runtime-generated data
   expectations.

