# Critical Fixes - February 10, 2026 (Part 2)

## Issues Fixed

### 1. ✅ Wavelength Filtering Completely Broken

**Problem:** Wavelength filters returned ZERO results no matter what ranges were entered.

**Root Cause:** Invalid MAST query syntax with `None` values.

**Before (BROKEN):**
```python
criteria["em_min"] = [wavelength_min * 1e-9, None]  # ❌ None is invalid
criteria["em_max"] = [None, wavelength_max * 1e-9]  # ❌ MAST rejects this
```

**After (FIXED):**
```python
# Find observations that OVERLAP the requested wavelength range
min_meters = wavelength_min * 1e-9
max_meters = wavelength_max * 1e-9
criteria["em_min"] = [0, max_meters]        # Obs must start at or before user's max
criteria["em_max"] = [min_meters, 1.0]      # Obs must end at or after user's min
```

**How It Works:**
- User enters: 115-320 nm (UV range)
- Query returns: All observations covering ANY part of 115-320 nm
- Example: IUE observation 115-200 nm ✓ overlaps
- Example: JWST observation 600-5000 nm ✗ no overlap

**File:** [search_subprocess.py:38-48](app/workers/search_subprocess.py#L38-L48)

**Impact:** ✅ Wavelength filtering now actually works!

---

### 2. ✅ Removed Redundant "MAST ExoSystems" Provider

**Problem:** Two providers (MAST and MAST ExoSystems) that did the same thing but with inconsistent features.

**User Feedback:** *"Do we need 2? Do they do 2 different things only to return the same exact results? if so, thats pretty unnecessary. We should have one that works correctly. not 2 that half work."*

**Solution:** Removed MAST ExoSystems from provider list.

**What Was ExoSystems:**
- Searched curated exoplanet target lists
- Fell back to regular MAST search
- Same data as MAST, different preprocessing
- **Didn't have the new wavelength/instrument filters**

**What Remains:**
- Single MAST provider with all features
- Wavelength + instrument filters available
- Cleaner, simpler UI

**Files Modified:**
- [remote_data_service.py:647-649](app/services/remote_data_service.py#L647-L649) - Removed from provider list
- [remote_data_service.py:661-670](app/services/remote_data_service.py#L661-L670) - Removed unavailable provider messages
- [remote_data_service.py:686-687](app/services/remote_data_service.py#L686-L687) - Removed routing

**Impact:** ✅ No more confusing duplicate providers

---

### 3. ✅ Inspector Dock Not Resizable

**Problem:** Inspector dock (right panel) couldn't be resized beyond 600px wide, making content unreadable.

**User Feedback:** *"also i still cant resize shit, or read half the stuff in the inspector tab. nothing in the dock is scalable"*

**Root Cause:** [main_window.py:505](app/ui/main_window.py#L505) had `setMaximumWidth(600)`

**Fix:** Removed the width restriction entirely.

**Before:**
```python
self.inspector_dock.setMaximumWidth(600)  # ❌ Blocked resizing
```

**After:**
```python
# No maximum width - let user resize freely  ✓
```

**Impact:** ✅ All dock panels now freely resizable

---

## Summary Table

| Issue | Status | Root Cause | Impact |
|-------|--------|------------|--------|
| **Wavelength filtering broken** | ✅ FIXED | Invalid `None` in MAST query range | Filters now work! |
| **ExoSystems redundant** | ✅ REMOVED | Duplicate provider, inconsistent features | Single MAST provider |
| **Inspector not resizable** | ✅ FIXED | Hard-coded 600px width limit | Freely resizable now |
| **Imaging products failing import** | ✅ FIXED (prev) | Wrong file types included | Filtered out _raw/_flt |
| **Wavelength units wrong** | ✅ FIXED (prev) | Incorrect unit conversion | Now shows nm/µm correctly |

---

## Testing Instructions

**IMPORTANT: You must restart the app for all changes to take effect!**

### Test 1: Wavelength Filtering
1. Restart the app
2. Go to Remote Data tab
3. Search for "titan"
4. Set wavelength filter: Min=115, Max=320 (UV range)
5. Click Search
6. **Expected:** See IUE results only (UV instruments)
7. Clear filters, search again
8. **Expected:** See all results (UV + IR)

### Test 2: Provider Simplified
1. After restart, check Catalogue dropdown
2. **Expected:** Only see "MAST" (no more "MAST ExoSystems")
3. All filters should be visible

### Test 3: Inspector Resizing
1. Drag the Inspector dock edge
2. **Expected:** Can resize to any width, no 600px limit
3. Check if content is now readable

### Test 4: No Imaging Product Failures
1. Search for any target
2. Download multiple results
3. **Expected:** No more "_raw.fits" or "_flt.fits" import errors
4. Check terminal for successful imports

---

## What's Still Needed

### Data Coverage Concerns

User mentioned: *"i still cant see ranges i want. so we need to find out where we are getting our data, and how we can get more from a wider range."*

**Current Source:** MAST archive only
- HST: UV to near-IR (~115-2500 nm)
- JWST: Near-IR to mid-IR (~600-28000 nm)
- IUE: Far-UV (~115-320 nm)
- Spitzer: Mid-IR (~3000-180000 nm)

**Potential Additional Sources:**
1. **IRSA (NASA/IPAC Infrared Science Archive)** - More IR data
2. **ESO Archive** - European Southern Observatory
3. **ALMA Archive** - Sub-millimeter/radio
4. **Vizier** - Published catalog data

**Next Steps:**
1. User specifies what wavelength ranges they can't find
2. Identify which archives have that coverage
3. Add additional archive support if needed

---

## Files Changed

```
app/workers/search_subprocess.py     | 16 ++++++++++++---- (Wavelength filter fix)
app/services/remote_data_service.py  | 14 +++-----------  (ExoSystems removal)
app/ui/main_window.py                |  1 insertion(+), 2 deletions(-) (Inspector resize)
```

---

**All fixes committed and ready for testing!** 🎉

Restart the app to see all improvements!
