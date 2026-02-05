
Pass 2 — UI/UX behaviors & performance
What’s in place (good foundations)
	• Central Plot Pane (PyQtGraph) — app/ui/plot_pane.py
		○ Crosshair (visible by default) with horizontal/vertical guides and pointHovered signal.
		○ Legend management, per-trace style updates, add/remove visibility.
		○ LOD safeguards: app-level point cap with a peak-min/max downsampler (_downsample_peak) + pyqtgraph’s internal setDownsampling(mode="peak").
		○ Unit switching is idempotent at the viewer: map_nm_to_display() re-maps canon x (nm) → Å/µm/cm⁻¹ before plotting.
		○ Export PNG via pyqtgraph’s ImageExporter.
	• Performance & Persistence
		○ LOD point budget slider (defaults to 120k; hard caps 1k–1M) with persistence via QSettings("SpectraApp","DesktopPreview").
		○ Palette registry with high-contrast and color-blind-friendly sets; choice persisted in QSettings.
	• Main Window shell — app/main.py
		○ Toolbar: Unit picker (nm, Å, µm, cm⁻¹), cursor toggle, normalization (None/Max/Area), smoothing (Off/Savitzky–Golay), “Reset Plot”, “Export”.
		○ Docks: Datasets, Library (with search/filter + details), History (table + details). (These are built as dock widgets and wired up.)
		○ Tabs / Inspector: Info (alias, ranges, points), Math (ops log), Style (LOD + palette selection), Provenance, Reference (bundled line lists/IR/JWST quick-look), Docs (in-app docs viewer).
		○ Remote Data: Dialog with guarded inputs, caching via LocalStore, and tests around dialog logic.
		○ Hotkeys: e.g., Ctrl+O, Ctrl+Shift+R, Ctrl+Shift+A (Reset), F1 (docs).
	• Tests that touch UI behaviors
		○ Plot pane performance guard (test_plot_perf_stub.py) — verifies downsampling & crosshair toggle.
		○ Library and reference UI tests exist; headless Qt setup in UI tests.
Overall: you have a cohesive PySide6 shell with sensible defaults, point-budget controls, color palettes, an inspector layout, and basic interaction coverage. Nice work.

Where Atlas expects more (gaps vs Ch. 22 “Good UI Design”)
Atlas emphasizes “truth-first” visuals, deterministic interactions, and teaching-friendly affordances. The biggest misses are not architectural—they’re interaction polish and visibility of scientific state:
	1. LSF honesty & calibration visibility (Ch. 6 + Ch. 22)
		○ Missing: an explicit Calibration Manager UI with:
			§ “Convolve down to target resolution” banner (kernel + FWHM + justification),
			§ Velocity frame controls (air/vacuum, heliocentric/barycentric),
			§ A visible badge indicating current LSF and frame.
		○ Today you have line-shape previews and math helpers, but no user-facing manager that acts on active traces with provenance steps.
	2. Uncertainty ribbons
		○ Present for some reference previews, but not a first-class toggle for user datasets.
		○ Atlas requires default-on uncertainty (truth-first), with easy toggles and persisted preference.
	3. Peak/region tools
		○ Atlas calls for snap-to-peak, brush-to-mask, and synced cursors across linked views. Snap-to-peak is not implemented; brush interactions aren’t exposed.
	4. Accessibility & teaching mode
		○ Palettes are good, but there’s little global accessibility scaffolding:
			§ A “Teaching mode” preset (large fonts, high contrast, simplified controls),
			§ Tooltips/labels are sparse (I only see one tooltip string),
			§ Keyboard-first flows beyond menu accelerators (e.g., focus order, alt-shortcuts on inspector controls).
	5. State & persistence audit
		○ LOD and palette persist, but crosshair visibility, uncertainty toggle, normalization, smoothing may not persist. Atlas wants “pick up where you left off.”
	6. “Export what I see” parity
		○ You have PNG export and a strong provenance/export manifest; ensure the export bundle includes the current unit, normalization, smoothing, masks, and calibrated LSF details (Atlas: truth over pretty; exports must match the view).
	7. Discoverability
		○ Library is present and tested; make it a first-class discovery+provenance hub:
			§ “Open in viewer”, “Show manifest”, “Open knowledge-log summary”, “Rebuild view” buttons in the Library detail pane.

Concrete changes (component-level)
A) Plot Pane upgrades (app/ui/plot_pane.py)
	• Snap-to-peak mode
		○ Add set_snap_to_peak(enabled: bool) and snap radius (px or nm).
		○ On mouseMoveEvent, if enabled, map x to nearest local extremum within tolerance using a lightweight peak finder (windowed min/max on the already downsampled view array). Emit pointHovered with snapped coordinates.
		○ Visual: a small marker dot + caption (x, y, unit badge).
	• Brush-to-mask
		○ Add a rubber-band brush (left-drag + modifier) that fills a semi-transparent region and emits maskCreated(from_x, to_x); the main window can add/remove masks to a per-trace mask list (stored in provenance). Make it toggleable (“Mask tool”).
	• Uncertainty ribbons for any trace
		○ Extend add_trace(..., sigma: np.ndarray | None = None).
		○ If sigma present and UI toggle is on, render a filled region (±σ) in a light alpha of the trace color.
		○ Provide set_uncertainty_visible(key: str, visible: bool) and global toggle.
	• Adaptive LOD (viewport-aware)
		○ Keep the existing peak min/max routine, but apply it to the visible x-range before your fixed cap. For multi-trace overlays, split the point budget across visible traces (e.g., cap / N).
		○ Cache downsampled arrays per (key, max_points, x_range_hash) to avoid re-decimating on small pans/zooms.
	• State persistence from the pane
		○ Add a small PlotState object (crosshair on/off, uncertainty on/off, snap-to-peak on/off). Emit a stateChanged signal and let MainWindow persist it.
B) Inspector / Toolbar polish (app/main.py)
	• Style tab additions
		○ Controls for Snap-to-peak (checkbox + radius), Uncertainty (global), Mask tool toggle, and a Teaching mode preset:
			§ Teaching mode sets: big fonts, high contrast palette, crosshair on, uncertainty on, snap radius larger, animations off.
		○ Persist all of these via QSettings.
	• Calibration Manager Dock (new)
		○ A dedicated dock with:
			§ Target resolution drop-down (convolve down); kernel (Gaussian/Lorentzian/Voigt); instrument LSF helper;
			§ Velocity frame selector (air/vac; topocentric/heliocentric/barycentric with radial velocity);
			§ Banner over the plot: “LSF = Gaussian FWHM=X; Frame = heliocentric v=+YY km/s; Applied to: N traces”;
			§ “Undo last calibration” (deterministic, logs to provenance).
		○ Hooked to a new CalibrationService that yields a new Spectrum + transform records.
	• Library detail actions
		○ Buttons: Load, View manifest, Open log entry, Re-export ‘what I see’, Add to knowledge-log (summary).
		○ Keep double-click to load; enrich the right-pane with clickable provenance keys.
	• Tooltips & focus
		○ Add tooltips to all toolbar/inspector controls: units, normalization, smoothing, LOD, palette, uncertainty, snap, mask, export.
		○ Ensure a predictable tab-order and mnemonic labels (Alt+key where reasonable).
C) Export parity
	• Extend export manifest (ProvenanceService) to record view state (unit, normalization, smoothing, LSF details, masks, uncertainty visibility, palette key, point budget).
	• Add an “Export what I see (bundle)” action on toolbar (PNG + CSV slice + manifest). Your current export path looks strong—just ensure UI state is serialized.

Performance notes (practical, measurable)
	• Viewport-aware decimation typically reduces per-frame work by 5–20× on deep zooms; pairing that with your existing min/max envelope is ideal.
	• Budget sharing across traces (cap/N) keeps worst-case redraws bounded as overlays stack up.
	• Downsample caching (keyed by rounded viewport bounds) cuts churn during small pans/zooms.
	• Avoid redundant conversions: you already map nm→display in one place—good. Keep canon arrays immutable and cache per-unit maps where safe.
Add/extend tests
	• test_plot_interactions.py:
		○ Snap-to-peak finds expected feature on a synthetic line forest.
		○ Brush-to-mask emits the correct interval; mask toggling updates rendering (smoke).
		○ Uncertainty ribbons render with and without toggle; persists across sessions.
		○ Teaching mode flips a bundle of preferences at once.
	• test_calibration_manager.py:
		○ Convolve-down changes FWHM to target within tolerance; provenance shows ordered steps.
		○ Velocity frame shift of +30 km/s yields expected Δλ/λ.

Accessibility & teaching
	• Teaching mode preset (Atlas): default to larger fonts (Qt app font +12–20%), high-contrast palette, crosshair on, uncertainty on, snap on. Persist it.
	• Contrast guard: run a tiny contrast check when setting palettes; if plot background is dark, ensure trace colors meet WCAG-ish contrast against the ribbon fill.
	• Docs discoverability: F1 already opens docs—good; add context-sensitive “?” buttons in Calibration Manager and Style tab that deep-link to the right doc section.

Small inconsistencies to clean up
	• Tooltips are sparse—fill them in (Atlas Ch. 22 asks for clarity and reversibility).
	• Persist more: crosshair, uncertainty, normalization, smoothing, mask tool, teaching mode.
	• Library dock extraction: you have tests but most UI is in main.py. Consider extracting library_dock.py for clarity (no behavior change).

Suggested task breakdown (UI/UX sprint)
	1. Plot interactions bundle
		○ Snap-to-peak, uncertainty ribbons, brush-to-mask, viewport-aware LOD & cache.
		○ Tests + docs (docs/user/plot_tools.md).
	2. Calibration Manager
		○ Dock + service, LSF banner & frame control, provenance steps.
		○ Tests + docs (docs/user/calibration.md).
	3. Teaching & accessibility
		○ Teaching preset, tooltips, contrast checks, persistence for all toggles.
		○ Docs (docs/user/accessibility.md).
	4. Export view parity
		○ Serialize view state into manifest; one-click “Export what I see (bundle)”.
		○ Regression tests.
	5. Library detail enhancements
		○ Buttons + deep-links to manifest/log; extract optional module for clarity.
		○ UI tests.

Quick “does this make sense as a whole?” check
	• Yes: The PySide6 shell + services + docs already form a coherent desktop tool. Atlas’ UI chapter asks for more visible scientific honesty (LSF/frame/uncertainty as first-class citizens) and stronger, teaching-friendly affordances (snap, mask, presets, tooltips).
	• Where we must be deliberate: Atlas’ later chapters describe a React/TypeScript front-end with an Engine API. Your current code is PySide6. This is a strategic decision—we’ll handle it via an RFC in a later pass (keep PySide6 now; extract Engine API seam; revisit after parity).
