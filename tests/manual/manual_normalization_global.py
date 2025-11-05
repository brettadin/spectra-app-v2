"""Manual test to verify global normalization feature (moved from repo root).

Run with:
  python -m tests.manual.manual_normalization_global
"""

import sys
from pathlib import Path
import numpy as np

from app.qt_compat import get_qt
from app.services.knowledge_log_service import KnowledgeLogService
from app.ui.main_window import SpectraMainWindow
from app.services.spectrum import Spectrum

QtCore, QtGui, QtWidgets, _ = get_qt()


def main() -> None:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv)

    log_service = KnowledgeLogService(log_path=Path("test_history.md"), author="debug")
    window = SpectraMainWindow(knowledge_log_service=log_service)

    x = np.linspace(400, 700, 100)

    y1 = np.sin(np.linspace(0, 4 * np.pi, 100)) * 50 + 50
    spectrum1 = Spectrum(
        id="large_spectrum",
        name="Large Spectrum (Max=100)",
        x=x,
        y=y1,
        x_unit="nm",
        y_unit="intensity",
        metadata={},
    )

    y2 = np.sin(np.linspace(0, 3 * np.pi, 100)) * 0.5 + 0.5
    spectrum2 = Spectrum(
        id="small_spectrum",
        name="Small Spectrum (Max=1)",
        x=x,
        y=y2,
        x_unit="nm",
        y_unit="intensity",
        metadata={},
    )

    window.overlay_service.add(spectrum1)
    window._add_spectrum(spectrum1)
    window.overlay_service.add(spectrum2)
    window._add_spectrum(spectrum2)

    print("\n=== GLOBAL NORMALIZATION TEST ===")
    print("Two spectra loaded:")
    print(f"  1. Large Spectrum: Y range = {y1.min():.2f} to {y1.max():.2f}")
    print(f"  2. Small Spectrum: Y range = {y2.min():.2f} to {y2.max():.2f}")
    print("\nInstructions:")
    print("  1. Initially, both spectra should be visible (no normalization)")
    print("  2. Set Normalize to 'Max' (leave 'Global' unchecked)")
    print("     → Per-spectrum: Both peaks at Y=1.0, small spectrum still hard to see")
    print("  3. Check the 'Global' checkbox")
    print("     → Global: Large spectrum peak at Y=1.0, small spectrum scaled proportionally")
    print("     → Small spectrum becomes MUCH more visible!")
    print("  4. Uncheck 'Global' to compare\n")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
