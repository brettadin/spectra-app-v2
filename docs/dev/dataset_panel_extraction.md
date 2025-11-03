# Dataset Panel Extraction Plan

Goal: Extract the dataset tree/list and related controls from `app/ui/main_window.py` into a dedicated, testable `DatasetPanel` widget under `app/ui/dataset_panel.py`, keeping `SpectraMainWindow` thin (coordination only).

## Scope
- Move dataset view UI (tree/table), model, search/filter box, visibility toggles, and selection handling into `DatasetPanel`.
- Keep plotting, overlay management, and merge panel logic in main window (for now), but have the panel emit signals for these actions.

## Proposed file
- `app/ui/dataset_panel.py`
  - Class: `DatasetPanel(QtWidgets.QWidget)`
  - Inputs (constructor):
    - `overlay_service` (for read-only queries, no mutation)
    - possibly a small adapter to fetch spectra metadata (names, ids, visibility)
  - Signals:
    - `selection_changed(list[str])` — ordered list of selected spectrum ids
    - `visibility_toggled(str, bool)` — spectrum id and new visibility state
    - `filter_changed(str)` — text filter updates (debounced)
  - Public methods:
    - `refresh(data: list[tuple[str, str, bool]])` — (id, alias/name, visible)
    - `focus()` — focus filter or panel

## Contract (tiny)
- Inputs:
  - `refresh([...])` fully redraws rows. Caller controls ordering and visibility state.
- Outputs (signals):
  - `selection_changed(ids)` whenever selection changes.
  - `visibility_toggled(id, visible)` when user toggles a checkbox.
  - `filter_changed(text)` when user types.
- Error modes:
  - No crash when list is empty; selection signals not emitted.
  - Ignore unknown ids on refresh.
- Success criteria:
  - Main window can subscribe to signals to update overlay and downstream UI.

## Integration into main window
- Replace dataset view creation with:
  ```python
  self.dataset_panel = DatasetPanel(self.overlay_service, self)
  self.dataset_panel.selection_changed.connect(self._on_dataset_selection_changed)
  self.dataset_panel.visibility_toggled.connect(self._on_dataset_visibility_toggled)
  self.dataset_panel.filter_changed.connect(self._on_dataset_filter_changed)
  self.data_tabs.addTab(self.dataset_panel, "Datasets")
  ```
- Implement handlers in `SpectraMainWindow`:
  - `_on_dataset_selection_changed(ids: list[str])`
  - `_on_dataset_visibility_toggled(id: str, visible: bool)`
  - `_on_dataset_filter_changed(text: str)` (update model filter or query and call `refresh`)
- Replace internal direct UI access (`dataset_view`, `dataset_model`, etc.) with calls to `dataset_panel.refresh(...)`.

## Extraction steps
1. Identify dataset UI block(s) in `main_window.py` (tree/model setup, filter box, signals, selection listener).
2. Create `DatasetPanel` with equivalent UI and internal model.
3. Move selection/visibility handlers into panel; emit signals to the main window.
4. Replace main window’s direct UI manipulations with `refresh` calls.
5. Remove now-obsolete dataset UI fields from main window.
6. Run tests; fix wiring and minor regressions.

## Minimal first PR (safe)
- Create `DatasetPanel` with UI + signals, but keep main window as the data source.
- Wire signals, implement `refresh`, and swap tab content.
- Do not change behavior or data model yet; just move UI plumbing.

## Edge cases to watch
- Very large datasets (performance: virtualized view or capping rows if needed).
- Empty selection and visibility tri-state logic.
- Filter interactions with selection.

## Acceptance criteria
- App launches and datasets tab shows the same content and behavior as before.
- Selection, visibility, and filtering still work and trigger plot updates.
- Tests remain green.
