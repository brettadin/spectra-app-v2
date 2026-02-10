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
            obs_meta[obsid] = {
                'instrument': str(row.get('instrument_name', '')),
                'target': str(row.get('target_name', target_name)),
                'telescope': str(row.get('obs_collection', '')),
                't_min': row.get('t_min'),
                't_max': row.get('t_max'),
            }
        
        # Get products for these observations
        products = Observations.get_product_list(table)
        if products is None or len(products) == 0:
            return []
        
        # Filter to science products with known spectral file patterns
        results = []
        seen = set()
        
        spectral_patterns = ('_x1d.fits', '_sx1.fits', '_sx2.fits', '_s1d.fits', 
                            '_spec.fits', '_vo.fits', '_cspec.fits', '_mxlo_vo.fits')
        
        for row in products:
            try:
                uri = str(row.get('dataURI', ''))
                if not uri:
                    continue
                
                # Skip non-FITS
                if not uri.lower().endswith('.fits'):
                    continue
                
                # Skip non-spectral files
                uri_lower = uri.lower()
                is_spectral = any(pat in uri_lower for pat in spectral_patterns)
                if not is_spectral:
                    continue
                
                # Skip duplicates
                if uri in seen:
                    continue
                seen.add(uri)
                
                # Skip auxiliary/preview
                ptype = str(row.get('productType', '')).upper()
                if ptype in ('AUXILIARY', 'PREVIEW', 'INFO', 'THUMBNAIL'):
                    continue
                
                filename = str(row.get('productFilename', '') or uri.split('/')[-1])
                obsid = str(row.get('obsID', ''))

                # Get observation metadata
                meta = obs_meta.get(obsid, {})
                telescope = str(row.get('obs_collection', '')) or meta.get('telescope', '')
                instrument = meta.get('instrument', '')
                target = meta.get('target', target_name)
                description = str(row.get('description', ''))

                # Extract wavelength range (em_min/em_max are in meters)
                wavelength_range = ''
                try:
                    em_min = row.get('em_min')  # meters
                    em_max = row.get('em_max')  # meters

                    if em_min is not None and em_max is not None and em_min > 0 and em_max > 0:
                        # Convert to nm for display
                        wl_min_nm = float(em_min) * 1e9
                        wl_max_nm = float(em_max) * 1e9

                        # Smart formatting based on range
                        if wl_max_nm < 1000:  # Stay in nm
                            wavelength_range = f"{wl_min_nm:.0f}–{wl_max_nm:.0f} nm"
                        elif wl_max_nm < 2500:  # Still nm but show µm option
                            wl_min_um = wl_min_nm / 1000
                            wl_max_um = wl_max_nm / 1000
                            wavelength_range = f"{wl_min_um:.2f}–{wl_max_um:.2f} µm"
                        else:  # Infrared, use µm
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

                # Build a useful title
                title = f"{telescope} / {instrument}" if instrument else telescope
                if description:
                    title = description[:60]

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
