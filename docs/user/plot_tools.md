# Plot Interaction Tools & LOD Behaviour

The Spectra plot pane is powered by PyQtGraph and optimised for working with large spectral traces. This guide covers the day-to-day tools available for inspecting data, plus what to expect from the built-in level-of-detail (LOD) safeguards that preserve interactivity on dense datasets.

## Quick reference: mouse & keyboard gestures

| Action | Gesture | Notes |
| --- | --- | --- |
| Pan | Left mouse drag | Holds the current zoom level while moving the view. |
| Box zoom | Right mouse drag or hold `Ctrl` while dragging left | Draws a rectangle to focus on a specific wavelength span. |
| Wheel zoom | Scroll wheel (focus follows cursor) | Zooms towards the pointer so you can dive into narrow features quickly. |
| Reset view | Press `Ctrl+Shift+A` or click **View → Reset Plot** | Re-applies auto-range to every visible trace. |
| Toggle crosshair | Toolbar **Cursor** button | When enabled, the vertical/horizontal guides follow the pointer and update the status bar readout. |
| Snapshot | **File → Export → Manifest** | Captures a PNG of the current view alongside provenance assets. |

> **Tip**: The datasets dock includes a visibility checkbox for every trace. Hiding derived overlays before zooming on faint features reduces clutter and keeps the legend focused.

## Reading the status bar and inspector

Moving the mouse over the plot updates the status bar with the current cursor coordinates in the active display units. When the Inspector dock is visible, the **Info** tab also highlights the selected trace's sample count, value range, and original units so you can confirm whether a spike is physical or an artefact.

The **Cursor** toolbar toggle controls whether the crosshair guides are visible. Leave it enabled when measuring peaks; turn it off if you need an unobstructed screenshot.

## Legend & trace management

Every trace that remains visible has a matching entry in the floating legend anchored to the top-left corner of the plot. Rename a dataset from the Inspector's alias field to update the legend label in real time. To declutter dense overlays, uncheck the visibility toggle in the Datasets dock—the trace disappears from the canvas and the legend until you re-enable it.

> **Remote catalogue tip**: Imports triggered from **File → Fetch Remote Data…** behave just like local files. The spectra land in the Datasets dock with their remote provenance already cached, so you can toggle overlays, rename aliases, and compute ratios without any manual copying.

## Normalisation toolbar modes

The top-of-window plot toolbar hosts the **Normalize** combo box alongside the unit selector. If the toolbar is hidden, restore it via **View → Plot Toolbar**—Spectra now draws every trace in the source intensity units reported by the importer (for example `%T` for percent transmittance). The y-axis label and data table adapt to those units so you see raw amplitudes first, then optionally apply scaling.

Use the control to adjust every visible trace without mutating the underlying data:

- **None** keeps the source-unit scale exactly as ingested.
- **Max** divides each series by its maximum absolute value, preserving relative peak heights while pinning the tallest feature to 1.0 in the current units.
- **Area** scales the curve so the absolute area under the graph equals 1.0, helping you compare broad features without flattening local structure.

The data table and provenance metadata mirror the active normalisation, and the plot toolbar’s left-axis label calls out both the unit (e.g. `%T`) and the selected normalisation mode for downstream auditing.

## Overlay alignment and troubleshooting

Reference overlays adopt the scaling of the active plot so annotations land where you expect them. The IR functional-group lanes, for example, now anchor their filled band to the visible y-axis span and assign each label to its own vertical slot. When you normalise a trace or zoom the view, the overlay recalculates those slots to keep the stacked annotations readable. If labels ever drift out of band after switching datasets:

- Toggle **Overlay on plot** off and back on to rebuild the payload against the new scale.
- Use **View → Reset Plot** to reapply auto-range—the overlay matches the recomputed intensity span.
- Confirm no hidden traces define the axis limits; even invisible datasets can contribute to the active span if their visibility checkbox remains enabled.

The Reference inspector now keeps a single source of truth for overlay bookkeeping, so toggling the checkbox reuses the existing
payload and annotations rather than rebuilding empty containers. That means manual labels and band settings persist between
clears until you load a different dataset or regenerate the payload from the inspector table.

Automated coverage in `tests/test_reference_ui.py::test_ir_overlay_labels_stack_inside_band` protects the label-spacing logic, so overlap usually signals that the active axis is extremely compressed. Widening the y-range or temporarily disabling normalisation restores the expected layout.

## Level-of-detail safeguards

High-resolution spectra can contain millions of samples. Rendering every point would make panning and zooming sluggish, so the plot pane automatically enforces a peak-envelope LOD cap. The default budget renders up to **120,000** points per trace exactly as provided, but you can tailor the threshold under **Inspector → Style → LOD point budget**. The spinner ranges from 1,000 to 1,000,000 samples so dense imports stay interactive on modest GPUs.

- Up to the configured cap render exactly as provided.
- Above that threshold, the x-axis is segmented and each block collapses into alternating min/max samples that preserve peaks.
- The tail of a trace that does not align perfectly with the segmentation is appended without modification so you never lose edge information.

This process is entirely view-layer only—no data is mutated or discarded. Exports (CSV and manifest bundles) always include the full-resolution series, and unit conversions continue to operate on the canonical nanometre axis. If you need to inspect individual samples, open the **View → Show Data Table** panel to browse the raw numbers alongside the plot.

## Performance best practices

- Prefer hiding traces you are not actively comparing; fewer visible overlays result in shallower legend hierarchies and less work for the renderer.
- Use wheel zoom to home in on features before switching units—wavenumber axes invert the direction of increasing values, and staying zoomed keeps orientation consistent.
- For extremely dense imported files, let the initial draw settle for a second before interacting; once cached, subsequent pans and zooms reuse the downsampled envelope.

Following these practices keeps the UI responsive even with multi-megabyte spectral stacks, while the provenance export pipeline continues to capture the unmodified data stream.
