# Housekeeping Implementation Plan

**Date**: October 22, 2025  
**Priority**: High — UI improvements and data management

## Changes Completed ✅

### 1. Removed Default Sample Loading
**File**: `app/main.py` line 144  
**Change**: Commented out `self._load_default_samples()`  
**Impact**: App now launches with empty workspace instead of loading `sample_*.csv` files  
**Rationale**: User preference for clean startup

---

## Changes In Progress ⏳

### 2. Add Dataset Removal UI
**Files**: `app/main.py`  
**Implementation**:
1. Add toolbar buttons to dataset dock:
   - "Remove Selected" (Del key shortcut)
   - "Clear All" (with confirmation)
2. Add methods:
   ```python
   def remove_selected_datasets(self) -> None:
       # Get selected items from dataset_tree
       # Confirm if multiple
       # Call overlay_service.remove() for each
       # Remove from dataset_model
       # Refresh overlay
  
   def clear_all_datasets(self) -> None:
       # Confirm with dialog
       # Call overlay_service.clear()
       # Clear dataset_model
       # Reset UI state
   ```

### 3. Move Remote Data to Inspector Tab
**Files**: `app/ui/remote_data_tab.py` (new), `app/main.py`  
**Implementation**:
1. Create `RemoteDataTab` widget class:
   - Embed provider combo, search field, quick-pick button
   - Simplified results table
   - Download button
   - Wire to existing `RemoteDataService`
2. Add tab in `_build_inspector_tabs()`:
   ```python
   self.tab_remote = RemoteDataTab(
       remote_service=self.remote_data_service,
       ingest_service=self.ingest_service
   )
   self.inspector_tabs.addTab(self.tab_remote, "Remote Data")
   ```
3. Remove from File menu (line 160-165)
4. Keep Ctrl+Shift+R shortcut, point to inspector tab

---

## Changes Planned 📋

### 4. Expand Telescope Searches
**File**: `app/services/remote_data_service.py`  
**Changes**:
- Update MAST queries to include:
  - **HST**: STIS (UV/Optical spectra), COS (FUV/NUV), WFC3 (IR grism)
  - **Spitzer**: IRS (MIR spectra 5-40µm)
  - **Chandra**: HETG/LETG (X-ray spectra) — if useful
  - **Ground**: Apache Point, Keck/ESI (optical spectra from archives)
- Remove JWST-specific product filtering
- Keep spectroscopic product type filters:
  ```python
  'dataproduct_type': 'spectrum',
  'intentType': 'science'
  ```
- Limit results per query (default 100, max 500)

### 5. Palette UI Enhancement
**Status**: ✅ **Already implemented** (line 809-817)  
**Location**: Style tab in Inspector → "Trace colouring" combo box  
**Options**:
- High-contrast palette (default)
- Colour-blind friendly
- Light-on-dark
- Uniform (single colour)

**Verification needed**: Ensure dropdown is visible and functional

---

## Deprecated Files Audit 🗑️

### Files to Keep (Marked Deprecated but Functional)
1. **`app/data/reference/jwst_targets.json`**
   - Status: `"DEPRECATED - Example data only"`
   - Usage: Still loaded by `ReferenceLibrary.jwst_targets()`
   - Decision: **KEEP** — provides example data for offline work
   - Action: Ensure UI shows deprecation warning

### Files to Check
1. **`patch.patch`** (root directory)
   - Historical patch sample
   - Status: removed from repository (archived references only)
   - Action: ensure no lingering doc references

2. **`docs/history/past prompts/`** directory
   - Old conversation logs
   - Not referenced by code
   - **Candidate for archiving/deletion**

3. **Test stub files**:
   - `tests/test_roundtrip_stub.py` — has placeholder, needs real test
   - `tests/test_ui_contract_stub.py` — has placeholder, needs real test
   - **Action**: Either implement or document as TODO

### Files Definitely NOT Deprecated
- All `samples/*.csv` files — used for manual testing
- All `app/data/reference/*.json` files — actively loaded by ReferenceLibrary
- All spec/doc files — documentation

---

## UI Quality of Life Improvements 🎨

### High Priority
1. ✅ **Color Palette** — Already implemented in Style tab
2. **Dataset Management** — Add remove/clear buttons (in progress)
3. **Remote Data Tab** — Move from menu to inspector (planned)
4. **Keyboard Shortcuts**:
   - Del: Remove selected datasets
   - Ctrl+Shift+C: Clear all datasets (with confirmation)
   - Ctrl+Shift+R: Focus Remote Data tab (existing)

### Medium Priority
5. **Progress Indicators**:
   - Show progress bar for multi-file imports
   - Show download progress for remote data
   - Already exists for search/download workers

6. **Dataset Icons**:
   - Color squares already shown in tree view
   - Consider adding icons for data type (spectrum vs derived)

7. **Tooltips**:
   - Add to all toolbar buttons
   - Show full spectrum name on hover in tree

### Low Priority
8. **Context Menu** (right-click on dataset):
   - Rename
   - Change color
   - Export selected
   - **Note**: User wants these in main UI, not just context menu

---

## Implementation Order

### Phase 1: Quick Wins (30 min)
1. ✅ Remove default sample loading
2. ✅ Verify palette UI is accessible
3. Add dataset removal buttons to dock toolbar

### Phase 2: Core Functionality (2 hours)
4. Implement `remove_selected_datasets()` method
5. Implement `clear_all_datasets()` method
6. Add keyboard shortcuts (Del, Ctrl+Shift+C)
7. Test dataset removal with overlay updates

### Phase 3: Remote Data Migration (3 hours)
8. Create `RemoteDataTab` widget class
9. Add tab to inspector dock
10. Remove from File menu, keep shortcut
11. Test full remote data workflow

### Phase 4: Telescope Expansion (1 hour)
12. Update `RemoteDataService` MAST queries
13. Add HST/Spitzer instrument filters
14. Test with real archive queries
15. Document available telescopes/instruments

### Phase 5: Documentation (30 min)
16. Update user guide for remote data tab location
17. Update keyboard shortcut documentation
18. Update AUDIT_REPORT.md with changes

---

## Testing Checklist

- [ ] App launches with empty workspace (no sample spectra)
- [ ] Can import CSV/FITS files normally
- [ ] Can remove individual datasets (Del key)
- [ ] Can remove multiple selected datasets
- [ ] Can clear all datasets with confirmation
- [ ] Overlay updates correctly after removal
- [ ] Remote Data tab accessible in inspector
- [ ] Ctrl+Shift+R opens/focuses Remote Data tab
- [ ] Can search HST/Spitzer/JWST missions
- [ ] Palette switcher works (Style tab)
- [ ] All shortcuts documented in Help menu

---

## Risk Assessment

**Low Risk**:
- Removing default sample loading ✅
- Adding dataset removal buttons
- Palette UI (already exists)

**Medium Risk**:
- Remote Data tab migration (complex UI refactor)
- Dataset removal logic (must update overlay correctly)

**High Risk**:
- Telescope search expansion (depends on MAST API)
- Must not break existing JWST queries

**Mitigation**:
- Test each change incrementally
- Run full test suite after each phase
- Keep File menu remote data as fallback during migration
- Document all changes in AUDIT_REPORT.md

---

## Questions for User

1. **Color picking**: Do you want a color picker dialog for changing dataset colors, or keep automatic assignment?
2. **Export location**: Should "Export Selected" be in toolbar, menu, or both?
3. **Remote data**: Keep File menu entry as fallback during migration, or remove immediately?
4. **Deprecation warnings**: How prominent should JWST targets deprecation warning be (tooltip, label, dialog)?