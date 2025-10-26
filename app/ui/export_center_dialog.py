"""Unified Export Center dialog for choosing export artifacts."""
from __future__ import annotations

from dataclasses import dataclass
from app.qt_compat import get_qt

QtCore, QtGui, QtWidgets, _ = get_qt()


@dataclass
class ExportCenterOptions:
    manifest: bool
    wide_csv: bool
    composite_csv: bool
    plot_png: bool
    plot_svg: bool
    plot_csv: bool


class ExportCenterDialog(QtWidgets.QDialog):
    def __init__(self, parent: QtWidgets.QWidget | None = None, *, allow_composite: bool = False) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)
        info = QtWidgets.QLabel(
            "Choose what to export. Files are written next to the chosen base name."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.chk_manifest = QtWidgets.QCheckBox(
            "Manifest bundle (JSON, per-spectrum CSV, plot snapshot PNG)"
        )
        self.chk_manifest.setChecked(True)
        layout.addWidget(self.chk_manifest)

        self.chk_wide = QtWidgets.QCheckBox(
            "Wide CSV (paired wavelength/intensity columns per spectrum)"
        )
        layout.addWidget(self.chk_wide)

        self.chk_composite = QtWidgets.QCheckBox(
            "Composite CSV (mean intensity across visible spectra)"
        )
        self.chk_composite.setEnabled(allow_composite)
        layout.addWidget(self.chk_composite)

        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        layout.addWidget(sep)

        self.chk_plot_png = QtWidgets.QCheckBox("Plot image (PNG)")
        layout.addWidget(self.chk_plot_png)

        self.chk_plot_svg = QtWidgets.QCheckBox("Plot graphic (SVG)")
        layout.addWidget(self.chk_plot_svg)

        self.chk_plot_csv = QtWidgets.QCheckBox("CSV of plot data (current curves as displayed)")
        layout.addWidget(self.chk_plot_csv)

        btns = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.StandardButton.Ok | QtWidgets.QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def result(self) -> ExportCenterOptions:
        return ExportCenterOptions(
            manifest=self.chk_manifest.isChecked(),
            wide_csv=self.chk_wide.isChecked(),
            composite_csv=self.chk_composite.isChecked(),
            plot_png=self.chk_plot_png.isChecked(),
            plot_svg=self.chk_plot_svg.isChecked(),
            plot_csv=self.chk_plot_csv.isChecked(),
        )
