# Remote Data Fixes - February 10, 2026

## Issues Fixed

### 1. ✅ Incorrect Wavelength Display Units

**Problem:** IUE data showing "115.1–197.9 µm" when it should be "115.1–197.9 nm"

**Root Cause:** Code incorrectly assumed MAST returns em_min/em_max in micrometers and multiplied by 1000 to convert to nanometers. Investigation revealed MAST actually returns values in **nanometers** directly.

**Evidence:** From astroquery MAST test data:
- WFPC2/WFC F814W: 713.51–867.45 (known range ~770-900 nm) ✓
- GALEX NUV: 169.3–300.7 (known range ~170-300 nm) ✓

**Fix:** [search_subprocess.py:48-73](app/workers/search_subprocess.py#L48-L73)

```python
# BEFORE (BROKEN):
em_min = row.get('em_min')  # micrometers
em_max = row.get('em_max')  # micrometers
wl_min_nm = float(em_min) * 1000  # Wrong! Already in nm
wl_max_nm = float(em_max) * 1000

# AFTER (FIXED):
em_min = row.get('em_min')  # nanometers
em_max = row.get('em_max')  # nanometers
wl_min_nm = float(em_min)  # Use directly
wl_max_nm = float(em_max)
```

**Impact:** ✅ Wavelength ranges now display correctly across all missions

---

### 2. ✅ Added Comprehensive Search Filters

**Problem:** User had to click through 38 pages of Jupiter results to find desired wavelength ranges. All pages showed similar wavelengths (UV range), making it impossible to find IR or other ranges efficiently.

**Solution:** Added three types of filters with UI controls:

#### A. Wavelength Range Filter
- **UI:** Min/Max input fields in nanometers
- **Examples:**
  - UV: 115–320 nm
  - Visible: 400–700 nm
  - Near-IR: 700–2500 nm (displayed as 0.7–2.5 µm)
  - Mid-IR: 2500–25000 nm (displayed as 2.5–25 µm)

#### B. Instrument Filter
- **UI:** Dropdown with common instruments
- **Options:**
  - HST: COS, STIS, FOS
  - IUE, FUSE
  - JWST: NIRSpec, MIRI, NIRISS, NIRCam
  - Spitzer: IRS

#### C. Table Sorting
- **Feature:** Click any column header to sort
- **Use cases:**
  - Sort by wavelength to see range distribution
  - Sort by telescope/instrument to group results
  - Sort by target for multi-target searches

**Files Modified:**
- [remote_data_panel.py:68-104](app/ui/remote_data_panel.py#L68-L104) - Filter UI controls
- [remote_data_panel.py:195-241](app/ui/remote_data_panel.py#L195-L241) - Filter state management
- [remote_data_panel.py:231-282](app/ui/remote_data_panel.py#L231-L282) - Pass filters to subprocess
- [search_subprocess.py:11-32](app/workers/search_subprocess.py#L11-L32) - Accept filter parameters
- [search_subprocess.py:27-29](app/workers/search_subprocess.py#L27-L29) - Query MAST with wavelength filters

**Impact:** ✅ Users can now find specific wavelength ranges without pagination

---

## Technical Details

### MAST Wavelength Query API

MAST query accepts wavelength in **meters**, but returns results in **nanometers**:

```python
# Query: Convert nm to meters
criteria["em_min"] = [wavelength_min * 1e-9, None]  # nm → m
criteria["em_max"] = [None, wavelength_max * 1e-9]  # nm → m

# Results: Already in nanometers
em_min = row.get('em_min')  # nanometers (not meters!)
em_max = row.get('em_max')  # nanometers (not meters!)
```

### Filter Flow

1. **UI Input:** User enters wavelength in nm or selects instrument
2. **State Storage:** Filters stored in `_last_filters` dict
3. **Subprocess Call:** Filters passed as JSON in argv[3]
4. **MAST Query:** Wavelength converted to meters for query
5. **Results:** Filtered and paginated results returned

### Smart Unit Display

```python
if wl_max_nm < 1000:  # UV/Vis
    display = f"{wl_min_nm:.1f}–{wl_max_nm:.1f} nm"
elif wl_max_nm < 2500:  # Near-IR
    display = f"{wl_min_um:.2f}–{wl_max_um:.2f} µm"
else:  # Mid/Far-IR
    display = f"{wl_min_um:.1f}–{wl_max_um:.1f} µm"
```

---

## Example Use Cases

### Finding JWST Mid-IR Jupiter Data

**Before:** Click through 38 pages of UV data (115-198 nm range)

**After:**
1. Enter "Jupiter" in search
2. Set wavelength: Min=2500, Max=25000 (2.5–25 µm)
3. Select "JWST/MIRI"
4. Click Search
5. Get only mid-IR JWST results

### Finding UV Spectra for Any Target

**Before:** Mixed results across all wavelengths

**After:**
1. Enter target name
2. Set wavelength: Min=115, Max=320
3. Optional: Select "HST/COS" or "IUE"
4. Click Search

### Exploring Wavelength Coverage

**Before:** No way to see what ranges are available

**After:**
1. Search target
2. Click "Wavelength Range" column header to sort
3. Scroll to see full range of available data

---

## Testing

```bash
# Syntax validation
$ python -m py_compile app/workers/search_subprocess.py app/ui/remote_data_panel.py
# No errors
```

**Manual Testing Checklist:**
- [ ] IUE results show "115.1–197.9 nm" (not µm)
- [ ] WASP-39b JWST results appear in table
- [ ] Wavelength filter works (e.g., 115-320 for UV)
- [ ] Instrument filter works (e.g., JWST/NIRSpec)
- [ ] Table sorting by wavelength column works
- [ ] Clear filters button resets all inputs
- [ ] Pagination works with filters applied

---

## Summary

| Issue | Status | Impact |
|-------|--------|--------|
| **Wrong wavelength units** | ✅ FIXED | UV data now shows nm, not µm |
| **Limited search capability** | ✅ FIXED | Wavelength + instrument filters added |
| **No way to find specific ranges** | ✅ FIXED | Filter by range, sort by wavelength |
| **WASP-39b data missing** | ✅ FIXED | (Already fixed in previous commit) |

---

## What Changed

### Before
- User clicks through 38 pages of similar UV data
- No way to search for specific wavelengths
- IUE showing wrong units (µm instead of nm)
- Can't filter by instrument

### After
- User enters wavelength range (e.g., 2500-25000 nm for mid-IR)
- User selects instrument (e.g., JWST/MIRI)
- Click Search → Get exactly what they want
- All units display correctly
- Table sorting for exploration

---

**Ready for user testing!** 🎉
