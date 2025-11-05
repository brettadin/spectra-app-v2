"""Simple Calibration panel for Inspector dock.

Provides controls for resolution matching (FWHM), radial velocity shift, and
frame selection. Emits a consolidated signal when settings change so the main
window can apply display-time calibration via CalibrationService.
"""
from __future__ import annotations

from typing import Optional, Any

from app.qt_compat import get_qt

QtCore: Any
QtGui: Any
QtWidgets: Any
_, _, QtWidgets, _ = get_qt()
QtCore, QtGui, QtWidgets, _ = get_qt()


Signal = getattr(QtCore, "Signal", None)  # type: ignore[attr-defined]
if Signal is None:
    Signal = getattr(QtCore, "pyqtSignal")  # type: ignore[attr-defined]


class CalibrationPanel(QtWidgets.QWidget):
    """Compact panel with calibration controls.

    Signals:
      - configChanged(dict): emitted when any control changes; payload contains
        keys 'target_fwhm' (float|None), 'rv_kms' (float), 'frame' (str)
    """

    configChanged = Signal(dict)  # type: ignore[misc]

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        layout.setFieldGrowthPolicy(QtWidgets.QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        layout.setLabelAlignment(QtCore.Qt.AlignmentFlag.AlignRight)

        # Resolution matching
        self.enable_fwhm = QtWidgets.QCheckBox("Enable")
        self.fwhm_spin = QtWidgets.QDoubleSpinBox()
        self.fwhm_spin.setDecimals(4)
        self.fwhm_spin.setRange(0.0, 1e9)
        self.fwhm_spin.setSingleStep(0.01)
        self.fwhm_spin.setValue(0.0)
        self.fwhm_spin.setEnabled(False)
        fwhm_row = QtWidgets.QHBoxLayout()
        fwhm_row.addWidget(self.enable_fwhm)
        fwhm_row.addWidget(self.fwhm_spin)
        fwhm_container = QtWidgets.QWidget()
        fwhm_container.setLayout(fwhm_row)
        layout.addRow("Target FWHM:", fwhm_container)

        # RV control
        self.rv_spin = QtWidgets.QDoubleSpinBox()
        self.rv_spin.setDecimals(3)
        self.rv_spin.setRange(-100000.0, 100000.0)
        self.rv_spin.setSingleStep(0.1)
        self.rv_spin.setSuffix(" km/s")
        layout.addRow("Radial velocity:", self.rv_spin)

        # Frame control
        self.frame_combo = QtWidgets.QComboBox()
        self.frame_combo.addItems(["observer", "rest"])
        layout.addRow("Frame:", self.frame_combo)

        # Wire signals
        self.enable_fwhm.toggled.connect(lambda _: self._on_changed())
        self.fwhm_spin.valueChanged.connect(lambda *_: self._on_changed())
        self.rv_spin.valueChanged.connect(lambda *_: self._on_changed())
        self.frame_combo.currentTextChanged.connect(lambda *_: self._on_changed())

        # Hints
        self.fwhm_spin.setToolTip("Target resolution full-width half-maximum in current display units (0 = off)")
        self.rv_spin.setToolTip("Apply a Doppler shift to wavelength axis")
        self.frame_combo.setToolTip("Target frame for wavelength axis")

        # Keep enable state in sync
        self.enable_fwhm.toggled.connect(self.fwhm_spin.setEnabled)

    def _on_changed(self) -> None:
        target = float(self.fwhm_spin.value()) if self.enable_fwhm.isChecked() else None
        payload = {
            "target_fwhm": target,
            "rv_kms": float(self.rv_spin.value()),
            "frame": str(self.frame_combo.currentText()),
        }
        try:
            self.configChanged.emit(payload)
        except Exception:
            pass
