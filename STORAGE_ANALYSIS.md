# Storage Duplication Analysis
**Date**: 2025-11-12  
**Branch**: clean-up-v2

## 🔍 Current Situation

### Storage Usage Breakdown
| Location | Files | Size (MB) | Purpose |
|----------|-------|-----------|---------|
| `samples/solar_system/` | Many | 428.88 | Demo/test planetary data |
| `samples/laboratory/` | Many | 58.35 | Lab spectra for demos |
| `samples/fits data/` | Many | 41.37 | FITS test files |
| `downloads/files/` | 128 | 69.41 | **User-uploaded + fetched data (DUPLICATES)** |
| `exports/` | 32 | 7.84 | User export bundles |
| `samples/exoplanets/` | 7 | 0.10 | Exoplanet tables (small) |

**Total committed data**: ~536 MB in samples/  
**Total runtime data**: ~77 MB in downloads/ + exports/

---

## 🐛 The Duplication Problem

### How It Happens:

1. **User imports a file** (File → Open, or drag-drop)
   - `DataIngestService.ingest(path)` → reads the file
   - `LocalStore.record(path)` → **COPIES file to `downloads/files/`**
   - Result: Original file + duplicate in downloads/

2. **User fetches remote data** (MAST/NIST)
   - `RemoteDataService.download()` → saves to temp, then `downloads/files/`
   - This is CORRECT (we want cached remote data)

3. **User exports manifest**
   - `ProvenanceService.export_bundle()` → writes to `exports/`
   - This is CORRECT (user-initiated export location)

### The Issue:
`LocalStore._copy_into_store()` **always copies** every file, even local user files that don't need caching. This wastes disk space and confuses users who see their files duplicated.

### What Should Happen:
- **Remote fetched data**: Cache in `storage/cache/` ✅ (intentional)
- **Local user imports**: DON'T duplicate; just record metadata + path reference ✅ (proposed)
- **Exports**: User-controlled location, separate from cache ✅ (correct as-is)

---

## 💡 Proposed Solution

### Option A: Conditional Copying (Recommended)
**Change `LocalStore.record()` behavior**:
- Add a `copy_to_store: bool = False` parameter
- Only copy when explicitly requested (remote downloads, not local imports)
- Store original path + checksum in index for local files
- Update `DataIngestService` to pass `copy_to_store=False` for local files
- Update `RemoteDataService` to pass `copy_to_store=True` for remote files

**Pros**:
- Eliminates duplication for local imports
- Preserves caching for remote data
- Backward compatible (cache still works)
- Simple code change (~20 LOC)

**Cons**:
- Local files can be moved/deleted by user (breaks reference)
- Need to handle missing files gracefully in UI

### Option B: Separate LocalCache vs LocalStore
**Create two storage layers**:
- `LocalCache` for remote downloads (always copies)
- `LocalIndex` for local imports (metadata only, no copy)

**Pros**:
- Clearer separation of concerns
- No confusion about cache vs index behavior

**Cons**:
- More refactoring (~100 LOC)
- Need to migrate existing cache structure

### Option C: Smart Link Detection
**Use symbolic links or hardlinks when possible**:
- Check if source and target are on same filesystem
- Use hardlink instead of copy (saves space, same inode)
- Fall back to copy for cross-filesystem moves

**Pros**:
- Transparent to code
- Saves space automatically

**Cons**:
- Platform-specific behavior (Windows vs Unix)
- Complexity in handling symlink updates

---

## 🎯 Recommendation: **Option A**

### Implementation Steps:

1. **Update `LocalStore.record()` signature**:
   ```python
   def record(
       self,
       source_path: Path,
       *,
       x_unit: str,
       y_unit: str,
       copy_to_store: bool = False,  # NEW parameter
       source: Mapping[str, Any] | None = None,
       ...
   ) -> Dict[str, Any]:
   ```

2. **Modify `_copy_into_store()` logic**:
   ```python
   def _copy_into_store(self, source_path: Path, alias: str | None = None, copy: bool = True) -> Path:
       if not copy:
           # Return original path, don't copy
           return source_path
       # Existing copy logic...
   ```

3. **Update callers**:
   - `DataIngestService.ingest()` → `copy_to_store=False` for local files
   - `RemoteDataService.download()` → `copy_to_store=True` for remote data
   - `DataIngestService.ingest_bytes()` → `copy_to_store=True` (in-memory data needs persistence)

4. **Graceful missing-file handling**:
   - Add `LocalStore.verify_entry(sha256)` → checks if stored_path exists
   - UI shows warning if local file was moved/deleted
   - Library dock filters out broken references

5. **Migration path**:
   - Existing cached files remain in `downloads/files/` (no disruption)
   - New local imports don't duplicate
   - Users can manually clean `downloads/files/` if desired

---

## 📊 Expected Impact

### Space Savings:
- Before: Local import of 50MB file → 50MB original + 50MB copy = 100MB
- After: Local import of 50MB file → 50MB original + ~1KB metadata = 50MB
- **Savings**: ~50% for local imports, 0% for remote (still cached)

### User Experience:
- ✅ No duplicate files cluttering downloads/
- ✅ Remote data still cached and reusable
- ✅ Exports work exactly as before
- ⚠️ Warning if user moves/deletes imported file (acceptable tradeoff)

### Code Changes:
- `app/services/store.py`: ~15 LOC
- `app/services/data_ingest_service.py`: ~5 LOC
- `app/services/remote_data_service.py`: ~3 LOC
- `app/ui/main_window.py`: ~10 LOC (missing file warning)
- Tests: ~30 LOC (new test cases)
- **Total**: ~63 LOC (well under 300 LOC limit)

---

## 🔄 Migration Strategy

### Phase 2A: Storage Move + Fix Duplication
1. Move `downloads/` → `storage/cache/` (existing data)
2. Move `exports/` → `storage/exports/` (existing exports)
3. Implement conditional copy in `LocalStore`
4. Update all callers to specify `copy_to_store`
5. Test local import, remote fetch, export workflows
6. Document behavior in user guides

### Rollback Plan:
- Keep `copy_to_store=True` by default for backward compat
- Explicit `copy_to_store=False` opt-in for local files
- Original downloads/ preserved until verified working

---

## ✅ Acceptance Criteria

- [ ] Local file imports don't duplicate to cache
- [ ] Remote downloads still cached in storage/cache
- [ ] Exports write to storage/exports
- [ ] Missing local files show warning (don't crash)
- [ ] Library dock shows cached + referenced files
- [ ] All tests pass (including edge cases)
- [ ] User guides document new behavior
- [ ] Patch notes explain the change

---

**Next**: Get approval for Option A approach, then proceed with Phase 2A implementation.
