#!/usr/bin/env python
"""Simple subprocess script for MAST searches.

This runs in a separate process to avoid blocking the main UI.
Results are printed as JSON to stdout.
"""
import json
import sys


def search_mast(target_name: str, page: int = 1, page_size: int = 50) -> dict:
    """Search MAST for spectra of a target. Returns dict with results and pagination info."""
    try:
        from astroquery.mast import Observations
    except ImportError:
        return {'results': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}

    try:
        # Single, simple query - no complex batching
        table = Observations.query_criteria(
            target_name=target_name,
            dataproduct_type="spectrum",
            intentType="science",
            calib_level=[2, 3],
        )

        if table is None or len(table) == 0:
            return {'results': [], 'total': 0, 'page': 1, 'page_size': page_size, 'total_pages': 0}

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
            # MAST returns em_min/em_max in micrometers (despite docs saying meters)
            wavelength_range = ''
            try:
                em_min = row.get('em_min')  # micrometers
                em_max = row.get('em_max')  # micrometers

                if em_min is not None and em_max is not None and em_min > 0 and em_max > 0:
                    # Convert µm to nm for display
                    wl_min_nm = float(em_min) * 1000
                    wl_max_nm = float(em_max) * 1000

                    # Smart formatting based on range
                    if wl_max_nm < 1000:  # UV/Vis: display in nm
                        wavelength_range = f"{wl_min_nm:.0f}–{wl_max_nm:.0f} nm"
                    elif wl_max_nm < 2500:  # Near-IR: display in µm
                        wavelength_range = f"{em_min:.2f}–{em_max:.2f} µm"
                    else:  # Mid/Far-IR: display in µm
                        wavelength_range = f"{em_min:.1f}–{em_max:.1f} µm"
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

                # Check if it's a spectral product by filename pattern
                uri_lower = uri.lower()
                is_spectral = any(pat in uri_lower for pat in spectral_patterns)

                # Also accept SCIENCE products even if pattern doesn't match
                # (for newer missions like JWST with evolving naming conventions)
                if not is_spectral and ptype == 'SCIENCE':
                    # Check if it's likely a spectrum (not an image)
                    # Skip common imaging suffixes
                    if not any(img in uri_lower for img in ('_cal.fits', '_i2d.fits', '_drz.fits', '_drc.fits')):
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
    results = search_mast(target, page=page)
    print(json.dumps(results))


if __name__ == '__main__':
    main()
