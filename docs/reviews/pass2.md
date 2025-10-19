# Pass 2 — UI & Workflow Review (2025-10-17T00:10:00Z)

Focuses on interaction quality, accessibility, and workflow parity with Atlas
Chapter 22.

## Confirmed Strengths
- PySide6 shell with responsive plot controls and persistent settings.
- Library caching keeps ingest snappy across sessions.
- Remote Data dialog surfaces spectroscopy hints when dependencies available.

## Required Upgrades
1. **Calibration Manager UI** — Pair with service to expose kernel/RV controls.
2. **Uncertainty Ribbons** — Visualise propagated σ alongside traces.
3. **Snap-to-Peak & Masking** — Keyboard-accessible controls with persisted
   toggles.
4. **Accessibility Presets** — Theme + palette combinations for teaching mode.
5. **Persistence Audit** — Ensure Library, History, Knowledge Log honour
   workspaces.
6. **Export Parity** — Add manifest-aware view exports for PNG/CSV.
7. **Library Actions** — Inspect, open manifest/log, re-export view state.

## Testing Implications
- Expand Qt smoke tests for new controls.
- Add regression coverage for accessibility toggles.

## References
- `docs/user/remote_data.md`
- `docs/user/plot_tools.md`
- `docs/developer_notes.md`
