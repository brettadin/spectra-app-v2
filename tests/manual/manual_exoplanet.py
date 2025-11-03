"""Manual test for exoplanet CSV loader."""

from pathlib import Path
from app.services.data_ingest_service import DataIngestService
from app.services.units_service import UnitsService

def test_exoplanet_csv():
    """Test loading various exoplanet CSV files."""
    
    units_service = UnitsService()
    ingest_service = DataIngestService(units_service=units_service)
    
    # Test files
    test_files = [
        "samples/exoplanets/table_WASP-96-b-Radica-et-al.-2023.csv",
        "samples/exoplanets/table_WASP-39-b-Rustamkulov-et-al.-2023.csv",
        "samples/exoplanets/table_WASP-178-b-Lothringer-et-al.-2022.csv",
        "samples/exoplanets/table_WASP-17-b-Louie-et-al.-2025.csv",
        "samples/exoplanets/table_Luhman-16-b-Biller-et-al.-2024.csv",
    ]
    
    print("\nTesting exoplanet CSV files:\n")
    
    for filepath in test_files:
        path = Path(filepath)
        if not path.exists():
            print(f"⚠ File not found: {filepath}")
            continue
        
        try:
            specs = ingest_service.ingest(path)
            for spec in specs:
                print(f"✓ Loaded: {spec.name}")
                print(f"  X unit: {spec.x_unit}")
                print(f"  Y unit: {spec.y_unit}")
                print(f"  X range: {spec.x[0]:.4f} to {spec.x[-1]:.4f} {spec.x_unit}")
                print(f"  Y range: {spec.y.min():.6e} to {spec.y.max():.6e}")
                print(f"  Points: {len(spec.x)}")

                # Metadata (best-effort, tolerant to missing keys)
                meta = getattr(spec, 'metadata', {}) or {}
                if isinstance(meta, dict):
                    fmt = meta.get('format')
                    cols = meta.get('columns') or {}
                    print(f"  Format: {fmt}")
                    print(f"  Columns: wave={cols.get('wavelength')}, flux={cols.get('flux')}")

                print()

        except Exception as e:
            print(f"✗ Error loading {filepath}:")
            print(f"  {type(e).__name__}: {e}")
            print()
    
    print("Test complete!")

if __name__ == "__main__":
    test_exoplanet_csv()
