#!/usr/bin/env python
"""Simple subprocess script for MAST searches.

This runs in a separate process to avoid blocking the main UI.
Results are printed as JSON to stdout.
"""
import json
import sys


def search_mast(target_name: str) -> list[dict]:
    """Search MAST for spectra of a target. Returns list of record dicts."""
    try:
        from astroquery.mast import Observations
    except ImportError:
        return []
    
    try:
        # Single, simple query - no complex batching
        table = Observations.query_criteria(
            target_name=target_name,
            dataproduct_type="spectrum",
            intentType="science",
            calib_level=[2, 3],
        )
        
        if table is None or len(table) == 0:
            return []
        
        # Limit to 50 observations max
        if len(table) > 50:
            table = table[:50]
        
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
                })
                
                # Limit results
                if len(results) >= 100:
                    break
                    
            except Exception:
                continue
        
        return results
        
    except Exception as e:
        # Return error as special result
        return [{'error': str(e)}]


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'error': 'No target specified'}))
        sys.exit(1)
    
    target = sys.argv[1]
    results = search_mast(target)
    print(json.dumps(results))


if __name__ == '__main__':
    main()
