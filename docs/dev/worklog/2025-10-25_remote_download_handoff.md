# Remote Download Issues - Agent Handoff (2025-10-25)

## Current State Summary

### Immediate Issues Observed

**Remote Download Path Problem**: The error `argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'tuple'` indicates that `RemoteDataService.download()` is returning a tuple instead of a proper `RemoteDownloadResult` in some code paths, causing `_RemoteDownloadWorker.run()` to fail when accessing `download.path`.

**Qt Threading Warnings**: `QObject: Cannot create children for a parent that is in a different thread` suggests that UI updates are being attempted from the worker thread instead of the main GUI thread, even though we've added `QueuedConnection` guards in `_on_remote_import()`.

### What Works

1. **Application Launch**: The app starts cleanly on Windows with no import errors.
2. **Local File Ingestion**: CSV/FITS/JCAMP importers work correctly via `DataIngestService`.
3. **Remote Search**: MAST/ExoSystems searches return results and populate the Remote Data table.
4. **Reference Overlays**: NIST line fetching, IR functional groups, and JWST quick-look targets render correctly in the Inspector.
5. **Plot Toolbar**: Unit switching, normalization modes, and LOD downsampling perform as expected.

### Recent Session Work (2025-10-25)

- Fixed IndentationError in `SpectraMainWindow.__init__` (app-local downloads directory setup)
- Changed default download location from AppData/Temp to `spectra-app-v2/downloads/`
- Added SPECTRA_STORE_DIR environment variable for custom download paths
- Made library dock display remote downloads even when persistence is disabled
- Removed deprecated Qt6 high-DPI attributes (AA_EnableHighDpiScaling, AA_UseHighDpiPixmaps)
- Updated worker to use `download.path` directly from RemoteDownloadResult
- Added explicit QueuedConnection for all worker signal connections
- Fixed test suite to handle empty library dock by seeding data

---

## Root Cause Analysis

### Download Path Tuple Issue

**Location**: `app/services/remote_data_service.py` → `download()` method (lines ~397-430)

**Hypothesis**: The `download()` method returns `RemoteDownloadResult` correctly, but the dataclass may be getting unpacked or the `cache_entry["stored_path"]` might still be a tuple in some provider implementations.

**Evidence**: 
- Worker code at line ~186 in `app/main.py` now uses `download.path` directly
- Error still occurs: "argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'tuple'"
- This suggests the `Path` object in `RemoteDownloadResult.path` may itself be malformed

**Fix Strategy**:
1. Check `LocalStore.record()` in `app/services/store.py` - ensure it returns proper path string in cache_entry
2. Verify `RemoteDownloadResult` construction in `download()` - ensure `path=Path(store_entry["stored_path"])` works
3. Add defensive `.resolve()` or explicit string conversion when constructing the Path
4. The issue may be that `store_entry["stored_path"]` is itself a tuple `(path, metadata)` from some code path

### Threading Warning

**Location**: `app/main.py` → `_on_remote_import()` signal handlers (lines ~1796-1887)

**Current State**: We've added explicit `QueuedConnection` to all worker signal connections:
```python
queued = getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection
worker.started.connect(_on_started, queued)
worker.record_ingested.connect(_on_progress, queued)
worker.record_failed.connect(_on_failure, queued)
worker.finished.connect(_on_finished, queued)
worker.failed.connect(_on_failed, queued)
worker.cancelled.connect(_on_cancelled, queued)
```

**Remaining Issue**: The `_on_failure` callback still triggers cross-thread warnings when calling `self._log()`, even though `_log()` itself uses `QMetaObject.invokeMethod()` to marshal to the GUI thread.

**Root Cause**: The signal connection might not be respecting the `QueuedConnection` parameter, or the slot is being invoked before the marshalling happens.

**Fix Strategy**:
1. Change `_on_failure` to use `QMetaObject.invokeMethod()` directly instead of calling `self._log()`
2. Or, make `_on_failure` queue a custom signal that the main window handles on the GUI thread
3. Verify the connection syntax is correct for PySide6 (parameter order may differ)

---

## Files Modified This Session (2025-10-25)

1. **`app/main.py`**
   - Fixed indentation in `__init__` for downloads directory setup (lines ~249-253)
   - Changed default store to `spectra-app-v2/downloads/` with SPECTRA_STORE_DIR override
   - Updated `_on_persistence_toggled()` to use app-local directory (lines ~833-843)
   - Modified `_refresh_library_view()` to show remote store when persistence disabled (lines ~877-881)
   - Updated `_RemoteDownloadWorker.run()` to use `download.path` directly (line ~183)
   - Added explicit QueuedConnection to all worker signals (lines ~1880-1885)
   - Removed deprecated high-DPI attributes from `main()` (lines ~1985-1995)

2. **`tests/test_smoke_workflow.py`**
   - Updated `test_library_dock_populates_and_previews()` to seed library when empty
   - Removed duplicate test definition

---

## Testing Evidence

### Test Results
- `test_main_import.py`: 3/3 passed
- `test_smoke_workflow.py`: 4/4 passed  
- `test_ingest.py`: 6/6 passed
- `test_remote_data_dialog.py`: 3/3 passed

### Runtime Behavior
- App launches cleanly (Exit Code: 0)
- Remote searches work (MAST/ExoSystems return results)
- Downloads start successfully (progress bars show)
- **FAILURE**: All imports fail with tuple path error
- **ISSUE**: Cross-thread QObject warnings persist

### Console Output Pattern
```
Downloading URL https://mast.stsci.edu/.../file.fits to C:\Users\brett\AppData\Local\Temp\tmp...\file.fits ...
|===================| 282k/282k (100.00%) 0s
[Remote Import] Failed to import file.fits: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'tuple'
QObject: Cannot create children for a parent that is in a different thread.
(Parent is QTextDocument(0x...), parent's thread is QThread(0x...), current thread is QThread(0x...))
```

**Key Observations**:
1. Files download successfully to temp directories (not to downloads/ yet - LocalStore not engaged?)
2. Tuple error occurs during ingest phase, not download phase
3. QTextDocument warning happens immediately after the log message

---

## Debugging Strategy for Next Agent

### Step 1: Inspect RemoteDownloadResult Construction

Add debug logging in `app/services/remote_data_service.py` around line 428:
```python
store_entry = self.store.record(
    fetch_path,
    x_unit=x_unit,
    y_unit=y_unit,
    source={"remote": remote_metadata},
    alias=record.suggested_filename(),
)
print(f"DEBUG: store_entry type: {type(store_entry)}")
print(f"DEBUG: stored_path type: {type(store_entry.get('stored_path'))}")
print(f"DEBUG: stored_path value: {store_entry.get('stored_path')}")

result_path = Path(store_entry["stored_path"])
print(f"DEBUG: result_path type: {type(result_path)}")
print(f"DEBUG: result_path value: {result_path}")

return RemoteDownloadResult(
    record=record,
    cache_entry=store_entry,
    path=result_path,
    cached=False,
)
```

### Step 2: Trace LocalStore.record() Return Value

Add debug logging in `app/services/store.py` around line 108:
```python
entry.update(
    {
        "sha256": checksum,
        "filename": stored_path.name,
        "stored_path": str(stored_path),  # <-- Ensure this is a string
        "original_path": str(source_path),
        "bytes": stored_path.stat().st_size,
        "units": {"x": x_unit, "y": y_unit},
        "source": merged_source,
        "created": created,
        "updated": self._timestamp(),
    }
)
print(f"DEBUG LocalStore: stored_path={entry['stored_path']}, type={type(entry['stored_path'])}")
items[checksum] = entry
self.save_index(index)
return entry  # <-- Ensure this is a dict, not a tuple
```

### Step 3: Check Worker Path Usage

Add debug logging in `app/main.py` around line 183:
```python
download = self._remote_service.download(record)
print(f"DEBUG Worker: download type: {type(download)}")
print(f"DEBUG Worker: download.path type: {type(download.path)}")
print(f"DEBUG Worker: download.path value: {download.path}")
file_path = download.path
print(f"DEBUG Worker: file_path after assignment: {type(file_path)}, {file_path}")
```

### Step 4: Fix Threading Warning

Replace the `_on_failure` callback in `app/main.py` (line ~1803):
```python
def _on_failure(record: Any, message: str) -> None:
    # Don't call _log() directly; marshal via invokeMethod to avoid QTextDocument warning
    identifier = getattr(record, 'identifier', '')
    log_line = f"[Remote Import] Failed to import {identifier}: {message}"
    try:
        QtCore.QMetaObject.invokeMethod(
            self,
            "_append_log_line",
            getattr(QtCore.Qt, "ConnectionType", QtCore.Qt).QueuedConnection,
            log_line,
        )
    except Exception:
        pass
```

---

## Recommended Immediate Actions

### Priority 1: Fix Tuple Path Error

**Hypothesis**: `LocalStore.record()` is returning a tuple instead of a dict in some code path.

**Test**:
```python
# In test_remote_data_service.py
def test_download_returns_proper_path(tmp_path, monkeypatch):
    store = LocalStore(base_dir=tmp_path)
    service = RemoteDataService(store=store)
    
    # Create a mock record
    record = RemoteRecord(
        provider="MAST",
        identifier="test123",
        title="Test",
        download_url="http://example.com/file.fits",
        metadata={},
    )
    
    # Mock the fetch to return a local file
    test_file = tmp_path / "test.fits"
    test_file.write_bytes(b"SIMPLE  = T")
    
    def mock_fetch(rec):
        return test_file, True
    
    monkeypatch.setattr(service, "_fetch_remote", mock_fetch)
    
    # Call download
    result = service.download(record)
    
    # Assertions
    assert isinstance(result, RemoteDownloadResult)
    assert isinstance(result.path, Path)
    assert result.path.exists()
    assert str(result.path).startswith(str(tmp_path))
```

### Priority 2: Validate Signal Connection Syntax

Check if PySide6 requires different connection syntax:
```python
# Current (may not work):
worker.record_failed.connect(_on_failure, queued)

# Try explicit connection type in connect call:
worker.record_failed.connect(_on_failure, type=queued)

# Or use decorator on the slot:
@QtCore.Slot(object, str)
def _on_failure(record: Any, message: str) -> None:
    # ...
```

### Priority 3: Add Type Hints

Add explicit return type to `download()` in `remote_data_service.py`:
```python
def download(self, record: RemoteRecord, *, force: bool = False) -> RemoteDownloadResult:
    # existing code...
    return RemoteDownloadResult(...)  # IDE will now warn if returning wrong type
```

---

## Knowledge Preservation

### Key Files for Next Session

1. **`app/services/store.py`** (lines 70-115) - `record()` method that returns cache entry
2. **`app/services/remote_data_service.py`** (lines 397-430) - `download()` method
3. **`app/main.py`** (lines 158-208) - `_RemoteDownloadWorker.run()` 
4. **`app/main.py`** (lines 1796-1887) - `_on_remote_import()` signal handlers

### Configuration State

- **Default Downloads Path**: `spectra-app-v2/downloads/`
- **Override Env Var**: `SPECTRA_STORE_DIR`
- **Persistence Toggle**: Works, but remote downloads use app-local dir regardless
- **Library Dock**: Shows remote store entries when main persistence disabled

### Test Coverage Gaps

- No test for `RemoteDataService.download()` return type validation
- No test for `LocalStore.record()` return structure
- No test for worker thread → GUI thread signal marshalling
- No test for bulk import of 10+ files

---

## Agent Handoff Checklist

- [x] Date corrected to 2025-10-25 throughout
- [x] Detailed error reproduction steps documented
- [x] Debug logging strategy provided for tuple issue
- [x] Threading warning fix strategy outlined
- [x] Key file locations and line numbers specified
- [x] Test gaps identified
- [x] Runtime behavior characterized
- [ ] **Next Agent TODO**: Add debug logging and rerun to identify tuple source
- [ ] **Next Agent TODO**: Implement threading fix for `_on_failure` callback
- [ ] **Next Agent TODO**: Add regression tests for download return types

**Stability Note**: The application is **stable for local workflows**. Remote download is the only critical blocker. The tuple path error and threading warnings are the two remaining issues to resolve before remote data import is fully functional.

---

## Success Criteria

When fixed, the following should work end-to-end:
1. Search MAST ExoSystems for "Jupiter"
2. Select 5+ records from results
3. Click "Download & Import"
4. **Expected**: Progress bar completes, files appear in Datasets dock, no console errors
5. **Expected**: Files persisted to `spectra-app-v2/downloads/files/<hash>/`
6. **Expected**: Library dock shows new cached entries with metadata
7. **Expected**: Clicking a dataset in tree view plots it correctly

Last updated: 2025-10-25
