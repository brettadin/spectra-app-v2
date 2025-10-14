# Documentation Inventory — 2025-10-14

This survey captures the documentation gaps that must be closed before the next feature batch. Each item notes the owning doc set, the missing coverage, and the expected deliverable so that the team can schedule writing work alongside feature development.

Quick links:

- [User Quickstart (placeholder)](../user/quickstart.md)
- [Provenance Schema (placeholder)](../dev/provenance_schema.md)
- [Documentation roadmap](../../README.md#documentation-roadmap)

## User Documentation Gaps

1. **Quickstart walkthrough**  
   - *Current state*: `docs/user/` only contains `importing.md` describing the ingest dialog.  
   - *Needed*: End-to-end quickstart covering application launch, loading bundled sample data, toggling units, adjusting plot view, and exporting provenance. Should include annotated screenshots and callouts to default directories.  
   - *Output*: New `docs/user/quickstart.md` referenced from README and in-app help menu.

2. **Units & conversions reference**  
   - *Current state*: Conversion guarantees live in tests and developer docs; users lack a canonical explanation of nm/Å/µm/cm⁻¹ behaviour.  
   - *Needed*: A conceptual explainer describing how unit toggles operate, idempotency promises, and tips for interpreting wavenumber axes.  
   - *Output*: `docs/user/units_and_conversions.md` plus cross-links from importing and quickstart guides.

3. **Plot interaction guide**  
   - *Current state*: No documentation on zooming, crosshair usage, legend management, or LOD behaviour.  
   - *Needed*: Instructions for pan/zoom gestures, resetting view, reading the metadata panel, and understanding downsampling when >120k points.  
   - *Output*: Section within an expanded `docs/user/plot_tools.md` (new file) that references performance guardrails.

4. **Data provenance & export explanation**  
   - *Current state*: Provenance export is mentioned in `importing.md` but without manifest breakdown.  
   - *Needed*: Step-by-step instructions for exporting, sample manifest snippet, and guidance on how to cite data sources when sharing bundles.  
   - *Output*: Update `docs/user/importing.md` with a dedicated export subsection and add appendices linking to developer provenance docs.

## Developer Documentation Gaps

1. **UnitsService contract**  
   - Document the conversion API (`convert_axis`, `convert_flux`), assumptions about canonical units, and extension guidelines for new unit systems.  
   - Add diagrams tying unit conversion tests (`tests/test_units_roundtrip.py`) to service behaviour.

2. **ProvenanceService schema**  
   - Expand existing material to include manifest JSON schema, bundle layout, and logging hooks, referencing the automated smoke test.  
   - Provide instructions for verifying provenance integrity in CI and offline review.

3. **LocalStore architecture**  
   - Outline cache indexing, SHA256 deduplication, and storage directory conventions. Include troubleshooting steps for corrupted cache entries.

4. **Testing playbook**  
   - Consolidate current scattered notes into a guide covering pytest markers, fixture generation, and how to run smoke tests headlessly on Windows/Ubuntu. Should mention coverage expectations once `pytest-cov` is reinstated.

## Historical & Meta Documentation

1. **Patch notes cadence**  
   - Ensure every feature batch adds an entry to `docs/history/PATCH_NOTES.md` with linked documentation updates.  
   - Create a template snippet for future entries to keep format consistent.

2. **AI development log**  
   - `docs/history/KNOWLEDGE_LOG.md` has not been updated in recent batches. Capture rationale for doc work and tie it to planned features.  
   - Add cross-reference to new inventory document for traceability.

3. **README alignment**  
   - Sync the README feature list with current capabilities (e.g., unit toggles, provenance export, smoke tests).  
   - Link out to user/developer docs so new contributors can discover the expanded documentation set.

## Action Plan

- Schedule the above deliverables for Batch 3 documentation sprint.  
- Update `docs/reviews/workplan.md` with owners and deadlines once assignments are made.  
- Track completion status via checkboxes in the workplan and reference this inventory when filing RFCs for doc-heavy features.
