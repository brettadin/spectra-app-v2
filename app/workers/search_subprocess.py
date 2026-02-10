#!/usr/bin/env python
"""Simple subprocess script for MAST searches.

This runs in a separate process to avoid blocking the main UI.
Results are printed as JSON to stdout.
"""
import json
import sys


def search_mast(target_name: str, page: int = 1, page_size: int = 50,
                wavelength_min: float = None, wavelength_max: float = None,
                instruments: list = None) -> dict:
    """Search MAST for spectra of a target. Returns dict with results and pagination info.

    Args:
        target_name: Target name to search for
        page: Page number (1-indexed)
        page_size: Number of results per page
        wavelength_min: Minimum wavelength in nm (optional)
        wavelength_max: Maximum wavelength in nm (optional)
        instruments: List of instrument names to filter by (optional)
    """
    try:
        from astroquery.mast import Observations
    except ImportError:
        return {'results': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}

    try:
        # Build query criteria
        criteria = {
            "target_name": target_name,
            "dataproduct_type": "spectrum",
            "intentType": "science",
            "calib_level": [2, 3],
        }

        # Add wavelength filters (MAST uses NANOMETERS for both query and results)
        # To find observations overlapping the user's wavelength range:
        # - Obs must start (em_min) at or before user's max wavelength
        # - Obs must end (em_max) at or after user's min wavelength
        if wavelength_min is not None and wavelength_max is not None:
            # NO conversion needed - MAST uses nm directly!
            criteria["em_min"] = [0, wavelength_max]  # Obs starts at or before user's max (nm)
            criteria["em_max"] = [wavelength_min, 100000]  # Obs ends at or after user's min (nm, up to 100µm)
        elif wavelength_min is not None:
            criteria["em_max"] = [wavelength_min, 100000]  # Obs includes at least this wavelength
        elif wavelength_max is not None:
            criteria["em_min"] = [0, wavelength_max]  # Obs starts before this wavelength

        # Query MAST
        table = Observations.query_criteria(**criteria)

        if table is None or len(table) == 0:
            return {'results': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}

        # Apply instrument filter if specified (post-query filter)
        if instruments:
            mask = []
            for row in table:
                inst = str(row.get('instrument_name', '')).upper()
                matches = any(inst.startswith(i.upper()) for i in instruments)
                mask.append(matches)

            if not any(mask):
                return {'results': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}

            # Filter table by mask
            table = table[mask]

        total_observations = len(table)
        total_pages = (total_observations + page_size - 1) // page_size

        # Calculate slice for current page
        start_idx = (page - 1) * page_size
        end_idx = min(start_idx + page_size, total_observations)

        # Slice table for current page
        if start_idx >= total_observations:
            return {'results': [], 'total': total_observations, 'page': page, 'page_size': page_size, 'total_pages': total_pages}

        table = table[start_idx:end_idx]
        
        # Build lookup of observation metadata by obsid
        obs_meta = {}
        for row in table:
            obsid = str(row.get('obsid', ''))

            # Extract wavelength range from observations table
            # MAST returns em_min/em_max in nanometers (usually)
            # NOTE: Some instruments (e.g. EUVE) report in Angstroms instead!
            # The actual FITS files have correct wavelengths; this is just display metadata.
            wavelength_range = ''
            try:
                em_min = row.get('em_min')  # nanometers
                em_max = row.get('em_max')  # nanometers

                if em_min is not None and em_max is not None and em_min > 0 and em_max > 0:
                    wl_min_nm = float(em_min)
                    wl_max_nm = float(em_max)

                    # Smart formatting based on range
                    if wl_max_nm < 1000:  # UV/Vis: display in nm
                        wavelength_range = f"{wl_min_nm:.1f}–{wl_max_nm:.1f} nm"
                    elif wl_max_nm < 2500:  # Near-IR: display in nm or µm
                        wl_min_um = wl_min_nm / 1000
                        wl_max_um = wl_max_nm / 1000
                        wavelength_range = f"{wl_min_um:.2f}–{wl_max_um:.2f} µm"
                    else:  # Mid/Far-IR: display in µm
                        wl_min_um = wl_min_nm / 1000
                        wl_max_um = wl_max_nm / 1000
                        wavelength_range = f"{wl_min_um:.1f}–{wl_max_um:.1f} µm"
                else:
                    # Try wavelength_region as fallback
                    wl_region = row.get('wavelength_region')
                    if wl_region:
                        wavelength_range = str(wl_region)
            except Exception:
                wavelength_range = ''

            obs_meta[obsid] = {
                'instrument': str(row.get('instrument_name', '')),
                'target': str(row.get('target_name', target_name)),
                'telescope': str(row.get('obs_collection', '')),
                't_min': row.get('t_min'),
                't_max': row.get('t_max'),
                'wavelength_range': wavelength_range,
            }
        
        # Get products for these observations
        products = Observations.get_product_list(table)
        if products is None or len(products) == 0:
            return []
        
        # Filter to science products with spectral file patterns
        results = []
        seen = set()

        # Expanded patterns to include HST, JWST, Spitzer, and other missions
        spectral_patterns = (
            # HST (COS, STIS, FOS, GHRS, etc.)
            '_x1d.fits', '_sx1.fits', '_sx2.fits', '_s1d.fits',
            '_spec.fits', '_vo.fits', '_cspec.fits', '_mxlo_vo.fits',
            # JWST (NIRSpec, MIRI, NIRCam, NIRISS)
            '_x1dints.fits', '_s2d.fits', '_s3d.fits', '_calints.fits',
            '_x1d.fits', '_cal.fits', '_rate.fits', '_rateints.fits',
            # Spitzer IRS
            '_bcd.fits', '_cal.fits',
            # Generic spectral indicators
            'spec.fits', 'spectrum.fits', 'extracted.fits',
        )

        for row in products:
            try:
                uri = str(row.get('dataURI', ''))
                if not uri:
                    continue

                # Only process FITS files
                if not uri.lower().endswith('.fits'):
                    continue

                # Skip duplicates
                if uri in seen:
                    continue
                seen.add(uri)

                # Skip auxiliary/preview/metadata files
                ptype = str(row.get('productType', '')).upper()
                if ptype in ('AUXILIARY', 'PREVIEW', 'INFO', 'THUMBNAIL'):
                    continue

                # Skip imaging products (raw, flat-fielded, drizzled, etc.)
                uri_lower = uri.lower()
                imaging_patterns = (
                    '_raw.fits',     # Raw detector images
                    '_flt.fits',     # Flat-fielded images
                    '_flc.fits',     # Flat-fielded, CTE-corrected images
                    '_i2d.fits',     # 2D resampled images
                    '_drz.fits',     # Drizzled images
                    '_drc.fits',     # Drizzled, CTE-corrected images
                    '_crj.fits',     # Cosmic ray rejected images
                    '_c0m.fits',     # Uncalibrated images
                    '_c1f.fits',     # Calibrated images
                )

                if any(pat in uri_lower for pat in imaging_patterns):
                    continue

                # Check if it's a spectral product by filename pattern
                is_spectral = any(pat in uri_lower for pat in spectral_patterns)

                # Also accept SCIENCE products even if pattern doesn't match
                # (for newer missions like JWST with evolving naming conventions)
                if not is_spectral and ptype == 'SCIENCE':
                    is_spectral = True

                if not is_spectral:
                    continue
                
                filename = str(row.get('productFilename', '') or uri.split('/')[-1])
                obsid = str(row.get('obsID', ''))

                # Get observation metadata (including wavelength range)
                meta = obs_meta.get(obsid, {})
                telescope = str(row.get('obs_collection', '')) or meta.get('telescope', '')
                instrument = meta.get('instrument', '')
                target = meta.get('target', target_name)
                wavelength_range = meta.get('wavelength_range', '')
                description = str(row.get('description', ''))

                # Build a useful title with filename instead of truncated description
                filename_base = filename.replace('.fits', '').replace('_', ' ')
                title = f"{telescope} / {instrument}" if instrument else telescope
                if len(filename_base) < 40:
                    title = filename_base

                results.append({
                    'identifier': filename,
                    'title': title,
                    'download_url': uri,
                    'target': target,
                    'telescope': telescope,
                    'instrument': instrument,
                    'wavelength_range': wavelength_range,
                })

            except Exception:
                continue

        return {
            'results': results,
            'total': total_observations,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        }

    except Exception as e:
        # Return error as special result
        return {'results': [{'error': str(e)}], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No target specified'}))
        sys.exit(1)

    target = sys.argv[1]
    page = int(sys.argv[2]) if len(sys.argv) > 2 else 1

    # Parse optional filters from JSON in argv[3]
    wavelength_min = None
    wavelength_max = None
    instruments = None
    if len(sys.argv) > 3:
        try:
            filters = json.loads(sys.argv[3])
            wavelength_min = filters.get('wavelength_min')
            wavelength_max = filters.get('wavelength_max')
            instruments = filters.get('instruments')
        except:
            pass

    results = search_mast(target, page=page,
                         wavelength_min=wavelength_min,
                         wavelength_max=wavelength_max,
                         instruments=instruments)
    print(json.dumps(results))


if __name__ == '__main__':
    main()
