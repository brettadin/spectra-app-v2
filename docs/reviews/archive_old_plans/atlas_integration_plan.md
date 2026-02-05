# Atlas Integration Plan

_Last updated: 2025-11-04_

## Purpose

Make the Atlas a living, actionable knowledge base for the Spectra app, supporting both in-app help and documentation cross-linking. Enable agents and users to easily find, contribute, and reference domain knowledge, workflows, and technical details.

## Integration Strategy

1. **Anchor Mapping**
   - Assign unique, stable anchors to key Atlas entries (concepts, workflows, datasets, etc.).
   - Maintain an `anchors.yml` index for programmatic lookup and cross-linking.
   - Add anchor appendix and guidance to `docs/atlas/README.md`.

2. **Cross-Linking**
   - Add "Further reading" links from user guides and in-app help to relevant Atlas anchors.
   - Use a consistent link format for maintainability.
   - Encourage inline help (`?` icons) in the UI to point to Atlas anchors.

3. **Contribution Guidance**
   - Document how to add new Atlas entries and anchors.
   - Provide naming conventions and review process for new anchors.

4. **Actionable Tasks**
   - [ ] Finalize anchor mapping for all major Atlas entries.
   - [ ] Create `docs/atlas/anchors.yml` with anchor-to-entry mapping.
   - [ ] Update `docs/atlas/README.md` with anchor and contribution guidance.
   - [ ] Add/refresh "Further reading" links in user guides and in-app help.
   - [ ] Add inline UI `?` links to Atlas anchors where appropriate.
   - [ ] Add link-checker CI to validate cross-references.

## Next Steps

- Draft anchors.yml and update Atlas README.
- Begin mapping and cross-linking from user guides and app UI.
- Review and iterate with agent/maintainer feedback.
