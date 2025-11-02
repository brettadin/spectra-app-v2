"""Quick manual test for SpeX FITS file ingestion and plotting."""

from pathlib import Path
import sys

# Add repo to path
repo = Path(__file__).parent
sys.path.insert(0, str(repo))

import numpy as np
from app.services import DataIngestService, UnitsService

def test_spex_file():
    path = repo / "samples" / "fits data" / "SpeX 0.7-5.3 Micron Medium-Resolution Spectrograph and Imager" / "C7,6e(N4)_HD31996.fits"
    
    if not path.exists():
        print(f"❌ File not found: {path}")
        return False
    
    units_service = UnitsService()
    ingest_service = DataIngestService(units_service, store=None)
    
    # Ingest
    spectra = ingest_service.ingest(path)
    spec = spectra[0]
    
    print(f"✓ Ingested: {spec.name}")
    print(f"  X unit: {spec.x_unit}")
    print(f"  Y unit: {spec.y_unit}")
    print(f"  X range: {spec.x.min():.3f} to {spec.x.max():.3f} {spec.x_unit}")
    
    # Simulate what the plot does: convert X to nm
    try:
        x_nm = units_service._to_canonical_wavelength(
            np.asarray(spec.x, dtype=float), spec.x_unit
        )
        print(f"✓ Converted X to nm: {x_nm.min():.1f} to {x_nm.max():.1f} nm")
    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        return False
    
    # Verify conversion is correct (0.804 µm = 804 nm)
    expected_min = 804
    expected_max = 5064
    actual_min = x_nm.min()
    actual_max = x_nm.max()
    
    if abs(actual_min - expected_min) < 1 and abs(actual_max - expected_max) < 1:
        print(f"✓ Conversion correct! 0.804 µm → {actual_min:.1f} nm ≈ {expected_min} nm")
        print(f"✓ All checks passed!")
        return True
    else:
        print(f"❌ Conversion incorrect:")
        print(f"  Expected: {expected_min} to {expected_max} nm")
        print(f"  Got: {actual_min:.1f} to {actual_max:.1f} nm")
        return False

if __name__ == "__main__":
    success = test_spex_file()
    sys.exit(0 if success else 1)
