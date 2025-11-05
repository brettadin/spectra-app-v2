"""Test script to verify global normalization feature."""

import pytest

# Ensure pytest won't try to collect/execute this interactive manual runner
pytestmark = pytest.mark.skip(reason="Manual UI check moved to tests/manual; run directly as a script if needed.")

import sys
from pathlib import Path
import numpy as np

# Add the app to path
repo_root = Path(__file__).parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from app.qt_compat import get_qt
from app.services.knowledge_log_service import KnowledgeLogService
from app.ui.main_window import SpectraMainWindow
from app.services.spectrum import Spectrum

QtCore, QtGui, QtWidgets, _ = get_qt()


def main():
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)
    
    # Create main window
    log_service = KnowledgeLogService(log_path=Path("test_history.md"), author="debug")
    window = SpectraMainWindow(knowledge_log_service=log_service)
    
    # Create two spectra with very different scales
    x = np.linspace(400, 700, 100)
    
    # Spectrum 1: Large values (max = 100)
    y1 = np.sin(np.linspace(0, 4*np.pi, 100)) * 50 + 50
    spectrum1 = Spectrum(
        id="large_spectrum",
        name="Large Spectrum (Max=100)",
        x=x,
        y=y1,
        x_unit="nm",
        y_unit="intensity",
        metadata={}
    )
    
    # Spectrum 2: Small values (max = 1)
    y2 = np.sin(np.linspace(0, 3*np.pi, 100)) * 0.5 + 0.5
    spectrum2 = Spectrum(
        id="small_spectrum",
        name="Small Spectrum (Max=1)",
        x=x,
        y=y2,
        x_unit="nm",
        y_unit="intensity",
        metadata={}
    )
    
    # Add spectra
    window.overlay_service.add(spectrum1)
    window._add_spectrum(spectrum1)
    window.overlay_service.add(spectrum2)
    window._add_spectrum(spectrum2)
    
    print(f"\n=== GLOBAL NORMALIZATION TEST ===")
    print(f"\nTwo spectra loaded:")
    print(f"  1. Large Spectrum: Y range = {y1.min():.2f} to {y1.max():.2f}")
    print(f"  2. Small Spectrum: Y range = {y2.min():.2f} to {y2.max():.2f}")
    print(f"\nInstructions:")
    print(f"  1. Initially, both spectra should be visible (no normalization)")
    print(f"  2. Set Normalize to 'Max' (leave 'Global' unchecked)")
    print(f"     → Per-spectrum: Both peaks at Y=1.0, small spectrum still hard to see")
    print(f"  3. Check the 'Global' checkbox")
    print(f"     → Global: Large spectrum peak at Y=1.0, small spectrum scaled proportionally")
    print(f"     → Small spectrum becomes MUCH more visible!")
    print(f"  4. Uncheck 'Global' to compare")
    print(f"\n" + "="*50 + "\n")
    
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
