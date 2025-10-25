# Remote Download Tuple Path Issue

**Date:** 2025-10-25  
**Status:** ACTIVE - Critical blocker  
**Component:** Remote Data Import Pipeline  
**Affected Files:** `app/services/remote_data_service.py`, `app/services/store.py`, `app/main.py`

---

## Problem Statement

Remote spectral data downloads from MAST/ExoSystems complete successfully, but the subsequent ingest phase fails with:

```
[Remote Import] Failed to import <filename>: argument should be a str or an os.PathLike object where __fspath__ returns a str, not 'tuple'
```

This error occurs for **all** remote downloads, regardless of provider (MAST, NIST, ExoSystems) or file type (.fits, .gz, etc.), making remote data import completely non-functional.

---

## Technical Context

### Current Architecture

The remote download pipeline follows this flow:

```
User Selection → Worker Thread → RemoteDataService.download()
    ↓
LocalStore.record() → Cache Entry (dict)
    ↓
RemoteDownloadResult(record, cache_entry, path, cached)
    ↓
Worker accesses download.path → DataIngestService.ingest(path)
    ↓
ERROR: path is tuple, not Path
```

### Expected Behavior

1. `RemoteDataService.download()` returns `RemoteDownloadResult` dataclass
2. `RemoteDownloadResult.path` is a `pathlib.Path` object
3. `DataIngestService.ingest()` receives valid Path and loads file
4. Spectrum appears in Datasets dock

### Actual Behavior

1. `RemoteDataService.download()` appears to return correct structure
2. `RemoteDownloadResult.path` is somehow a tuple `(path_str, metadata)` or similar
3. `DataIngestService.ingest()` crashes when trying to use tuple as Path
4. No spectra ingested; all downloads wasted

---

## Root Cause Hypotheses

### Hypothesis 1: LocalStore.record() Returns Tuple

**Location:** `app/services/store.py`, lines 70-115

**Theory:** The `record()` method may have a code path that returns `(entry_dict, metadata)` instead of just `entry_dict`. When `RemoteDownloadResult` is constructed with `path=Path(store_entry["stored_path"])`, if `store_entry` is actually a tuple, the Path construction receives a tuple.

**Evidence:**
- Error message specifically mentions "tuple"
- `LocalStore.record()` is complex with multiple return paths (cached vs fresh)
- No explicit type hints enforce return type

**Test:**
```python
# Add to test_store.py
def test_record_returns_dict_not_tuple(tmp_path):
    store = LocalStore(base_dir=tmp_path)
    source = tmp_path / "test.csv"
    source.write_text("wavelength_nm,absorbance\n400,0.5\n")
    
    entry = store.record(source, x_unit="nm", y_unit="absorbance")
    
    assert isinstance(entry, dict), f"Expected dict, got {type(entry)}"
    assert "stored_path" in entry
    assert isinstance(entry["stored_path"], str)
```

### Hypothesis 2: RemoteDownloadResult.path Assignment Issue

**Location:** `app/services/remote_data_service.py`, lines 397-430

**Theory:** When constructing `RemoteDownloadResult`, the `path` parameter receives a tuple from somewhere upstream. The `cache_entry["stored_path"]` might already be a tuple.

**Evidence:**
- Worker code at line 183 expects `download.path` to be a Path
- If `store_entry["stored_path"]` is a tuple, `Path(tuple)` would fail differently
- More likely: `download.path` itself is being assigned a tuple

**Test:**
```python
# Add to test_remote_data_service.py
def test_download_result_has_path_object(tmp_path, monkeypatch):
    store = LocalStore(base_dir=tmp_path)
    service = RemoteDataService(store=store)
    
    record = RemoteRecord(
        provider="MAST",
        identifier="test",
        title="Test",
        download_url="http://example.com/test.fits",
        metadata={},
    )
    
    # Mock fetch to return local file
    test_file = tmp_path / "test.fits"
    test_file.write_bytes(b"SIMPLE  = T")
    monkeypatch.setattr(service, "_fetch_remote", lambda r: (test_file, True))
    
    result = service.download(record)
    
    assert isinstance(result, RemoteDownloadResult)
    assert isinstance(result.path, Path)
    assert not isinstance(result.path, tuple)
```

### Hypothesis 3: Worker Path Access Pattern

**Location:** `app/main.py`, lines 180-190

**Theory:** The worker might be doing something unusual when accessing `download.path`. Perhaps there's a tuple unpacking somewhere.

**Current Code:**
```python
download = self._remote_service.download(record)
file_path = download.path  # Line 183
non_spectral_extensions = {...}
if file_path.suffix.lower() in non_spectral_extensions:
    self.record_failed.emit(...)
    continue
ing_item = self._ingest_service.ingest(file_path)
```

**Evidence:**
- Code looks straightforward; no obvious unpacking
- Error occurs inside `ingest()`, suggesting file_path is wrong type
- If `download.path` were a tuple, the `.suffix` call would fail first

---

## Debugging Strategy

### Step 1: Add Defensive Logging

In `app/services/remote_data_service.py` at line 428:

```python
store_entry = self.store.record(
    fetch_path,
    x_unit=x_unit,
    y_unit=y_unit,
    source={"remote": remote_metadata},
    alias=record.suggested_filename(),
)

# DEBUG: Validate store_entry structure
assert isinstance(store_entry, dict), f"store.record() returned {type(store_entry)}"
assert "stored_path" in store_entry, f"Missing stored_path in {store_entry.keys()}"
stored_path_value = store_entry["stored_path"]
assert isinstance(stored_path_value, str), f"stored_path is {type(stored_path_value)}, expected str"

result_path = Path(stored_path_value)
assert isinstance(result_path, Path), f"Path() returned {type(result_path)}"

return RemoteDownloadResult(
    record=record,
    cache_entry=store_entry,
    path=result_path,
    cached=False,
)
```

### Step 2: Add Worker-Side Logging

In `app/main.py` at line 183:

```python
download = self._remote_service.download(record)

# DEBUG: Validate download structure
print(f"DEBUG: download type={type(download)}")
print(f"DEBUG: download.path type={type(download.path)}")
print(f"DEBUG: download.path value={download.path}")

if not isinstance(download.path, Path):
    error_msg = f"download.path is {type(download.path)}, expected Path. Value: {download.path}"
    self.record_failed.emit(record, error_msg)
    continue

file_path = download.path
```

### Step 3: Check LocalStore Internals

In `app/services/store.py` at line 115:

```python
items[checksum] = entry
self.save_index(index)

# DEBUG: Validate return value
assert isinstance(entry, dict), f"LocalStore.record() returning {type(entry)}"
assert "stored_path" in entry
assert isinstance(entry["stored_path"], str)

return entry  # Ensure we're not returning (entry, metadata) anywhere
```

### Step 4: Runtime Inspection

Add a breakpoint or print statement at the exact failure point in `DataIngestService.ingest()`:

```python
def ingest(self, path: Path | str) -> list[Spectrum]:
    print(f"DEBUG ingest: received path type={type(path)}, value={path}")
    if isinstance(path, tuple):
        print(f"DEBUG ingest: path is tuple with {len(path)} elements")
        for i, elem in enumerate(path):
            print(f"  Element {i}: type={type(elem)}, value={elem}")
        raise TypeError(f"ingest() received tuple instead of Path: {path}")
    
    path = Path(path)  # This line would fail if path is a tuple
    # ... rest of ingest logic
```

---

## Proposed Fixes

### Fix 1: Add Explicit Type Hints

```python
# In remote_data_service.py
def download(self, record: RemoteRecord, *, force: bool = False) -> RemoteDownloadResult:
    # Type checker will now warn if we return wrong type
    ...

# In store.py
def record(
    self,
    source_path: Path,
    *,
    x_unit: str,
    y_unit: str,
    source: Mapping[str, Any] | None = None,
    manifest_path: Path | None = None,
    alias: str | None = None,
) -> Dict[str, Any]:  # Explicit return type
    # Type checker ensures we return dict
    ...
```

### Fix 2: Add Runtime Assertions

At every critical boundary, assert the expected type:

```python
# In download() before returning
assert isinstance(result_path, Path)
result = RemoteDownloadResult(record=record, cache_entry=store_entry, path=result_path, cached=False)
assert isinstance(result.path, Path)  # Verify dataclass construction
return result
```

### Fix 3: Defensive Path Coercion

If the tuple pattern is coming from a third-party library, add defensive handling:

```python
# In worker at line 183
download = self._remote_service.download(record)

# Defensive: handle case where path might be tuple
file_path = download.path
if isinstance(file_path, (tuple, list)):
    # Some providers return (path, metadata); take first element
    file_path = Path(file_path[0]) if file_path else None
    if not file_path or not file_path.exists():
        self.record_failed.emit(record, "Invalid path from provider")
        continue
elif not isinstance(file_path, Path):
    file_path = Path(file_path)

# Now file_path is guaranteed to be a Path object
```

---

## Testing Plan

### Unit Tests

1. **Test LocalStore.record() Return Type**
   ```python
   def test_store_record_returns_dict_with_string_path(tmp_path):
       # Verify record() always returns dict with str stored_path
   ```

2. **Test RemoteDataService.download() Return Type**
   ```python
   def test_download_returns_dataclass_with_path(tmp_path, monkeypatch):
       # Mock providers, verify RemoteDownloadResult.path is Path
   ```

3. **Test Worker Path Handling**
   ```python
   def test_worker_handles_download_path_correctly(tmp_path, monkeypatch):
       # Mock download, verify worker can ingest from result.path
   ```

### Integration Tests

1. **End-to-End Remote Download**
   ```python
   @pytest.mark.integration
   def test_mast_download_and_ingest(tmp_path):
       # Real download from MAST (or mocked), verify full pipeline
   ```

2. **Bulk Import Test**
   ```python
   def test_bulk_remote_import_10_files(tmp_path):
       # Stress test worker with multiple files
   ```

---

## Success Criteria

When fixed:
1. ✅ Search MAST ExoSystems for "Jupiter"
2. ✅ Select 5+ records
3. ✅ Click "Download & Import"
4. ✅ All downloads complete without tuple errors
5. ✅ Spectra appear in Datasets dock with correct names
6. ✅ Files persisted to `downloads/files/<hash>/`
7. ✅ Library dock shows new entries
8. ✅ Plotting downloaded spectra works correctly

---

## Related Issues

- **Threading Warning**: Cross-thread QObject access when logging failures (see `_on_failure` callback)
- **Downloads Path**: Files currently go to temp dirs; should use `downloads/` after LocalStore engaged
- **Error Surfacing**: Failures only appear in console; need UI status updates

---

## References

- Main handoff doc: `docs/dev/worklog/2025-10-25_remote_download_handoff.md`
- Bug report: `reports/bugs_and_issues.md` (Issue #7)
- Remote pipeline design: `docs/brains/remote_data_pipeline.md`
- MAST download fallback: `docs/brains/mast_download_fallback.md`

**Last Updated:** 2025-10-25  
**Next Steps:** Add debug logging per Step 1-4, rerun download, examine console output to identify tuple source
