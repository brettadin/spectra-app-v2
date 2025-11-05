"""Manual debug to test normalization visually (moved from repo root).

Run with:
  python -m tests.manual.manual_normalization_debug
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

    repo_root = Path(__file__).resolve().parents[2]
    sample_csv = repo_root / "samples" / "sample_spectrum.csv"
    if sample_csv.exists():
        print("\n=== LOADING SAMPLE FILE ===")
        print(f"File: {sample_csv}")
        window._ingest_path(sample_csv)
        print("Spectrum loaded")
    else:
        x = np.linspace(400, 700, 100)
        y = np.array([0.5, 1.0, 1.5, 2.0, 2.5] * 20)
        spectrum = Spectrum(
            id="test_spectrum",
            name="Test Spectrum (Max=2.5)",
            x=x,
            y=y,
            x_unit="nm",
            y_unit="intensity",
            metadata={},
        )
        window.overlay_service.add(spectrum)
        window._add_spectrum(spectrum)

        print("\n=== TEST SPECTRUM CREATED ===")
        print(f"X range: {x.min():.1f} - {x.max():.1f} nm")
        print(f"Y range: {y.min():.2f} - {y.max():.2f}")
        print(f"Y max value: {np.max(y):.2f}")

    print("\nInstructions:")
    print("1. Window should show spectrum")
    print("2. Note the Y-axis range")
    print("3. Change 'Normalize' dropdown to 'Max'")
    print("4. Y-axis should now show 0 to 1")
    print("5. Peak of spectrum should be at Y=1.0")
    print("6. Check console/log file for normalization messages\n")

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
