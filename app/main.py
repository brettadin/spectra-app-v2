"""Main entry point and UI shell for the Spectra application."""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis

from .services import (
    DataIngestService,
    MathResult,
    MathService,
    OverlayService,
    ProvenanceService,
    Spectrum,
    UnitsService,
)

logger = logging.getLogger(__name__)
APP_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ServiceContainer:
    units: UnitsService
    provenance: ProvenanceService
    ingest: DataIngestService
    overlay: OverlayService
    math: MathService


class OverlayChart(QtWidgets.QWidget):
    """Simple multi-series chart for spectrum overlays."""

    def __init__(self, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self._chart = QChart()
        self._chart.legend().setVisible(True)
        self._chart.legend().setAlignment(QtCore.Qt.AlignBottom)
        self._chart.setAnimationOptions(QChart.NoAnimation)
        self._view = QChartView(self._chart)
        self._view.setRenderHint(QtGui.QPainter.Antialiasing)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._view)

    def update_series(self, series_data: Iterable[tuple[str, np.ndarray, np.ndarray]]) -> None:
        self._chart.removeAllSeries()
        for axis in list(self._chart.axes()):
            self._chart.removeAxis(axis)
        x_min, x_max, y_min, y_max = None, None, None, None
        for name, x_values, y_values in series_data:
            series = QLineSeries()
            series.setName(name)
            for xv, yv in zip(x_values, y_values):
                series.append(float(xv), float(yv))
            self._chart.addSeries(series)
            if x_min is None:
                x_min = float(np.min(x_values))
                x_max = float(np.max(x_values))
                y_min = float(np.min(y_values))
                y_max = float(np.max(y_values))
            else:
                x_min = min(x_min, float(np.min(x_values)))
                x_max = max(x_max, float(np.max(x_values)))
                y_min = min(y_min, float(np.min(y_values)))
                y_max = max(y_max, float(np.max(y_values)))
        if self._chart.series():
            axis_x = QValueAxis()
            axis_y = QValueAxis()
            axis_x.setTitleText("Wavelength")
            axis_y.setTitleText("Flux")
            if x_min == x_max:
                x_max = x_min + 1
            if y_min == y_max:
                y_max = y_min + 1
            axis_x.setRange(x_min, x_max)
            axis_y.setRange(y_min, y_max)
            self._chart.setAxisX(axis_x)
            self._chart.setAxisY(axis_y)
            for series in self._chart.series():
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)
        else:
            for axis in list(self._chart.axes()):
                self._chart.removeAxis(axis)


class DataTab(QtWidgets.QWidget):
    """Data ingest and overlay management tab."""

    spectra_changed = QtCore.Signal()
    status_message = QtCore.Signal(str)
    error_occurred = QtCore.Signal(str)

    def __init__(self, container: ServiceContainer, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.container = container
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        ingest_row = QtWidgets.QHBoxLayout()
        self.ingest_button = QtWidgets.QPushButton("Browse…")
        self.ingest_button.setToolTip("Select spectra files to ingest")
        self.ingest_button.clicked.connect(self._open_files)
        ingest_row.addWidget(self.ingest_button)

        self.load_sample_button = QtWidgets.QPushButton("Load Sample")
        self.load_sample_button.clicked.connect(self._load_sample)
        ingest_row.addWidget(self.load_sample_button)

        ingest_row.addStretch(1)

        layout.addLayout(ingest_row)

        unit_row = QtWidgets.QHBoxLayout()
        unit_row.addWidget(QtWidgets.QLabel("Wavelength unit:"))
        self.wavelength_unit = QtWidgets.QComboBox()
        self.wavelength_unit.addItems(["nm", "µm", "Å", "cm^-1"])
        self.wavelength_unit.currentTextChanged.connect(self.refresh_chart)
        unit_row.addWidget(self.wavelength_unit)

        unit_row.addWidget(QtWidgets.QLabel("Flux unit:"))
        self.flux_unit = QtWidgets.QComboBox()
        self.flux_unit.addItems(["absorbance", "transmittance", "percent_transmittance"])
        self.flux_unit.currentTextChanged.connect(self.refresh_chart)
        unit_row.addStretch(1)
        layout.addLayout(unit_row)

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Points", "Source", "Flux Unit"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.table)

        self.chart = OverlayChart()
        layout.addWidget(self.chart)

    def _open_files(self) -> None:
        dialog = QtWidgets.QFileDialog(self, "Select spectra")
        dialog.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
        dialog.setNameFilters(["Delimited files (*.csv *.txt *.dat)", "All files (*.*)"])
        if dialog.exec():
            for file_path in dialog.selectedFiles():
                self.ingest_path(Path(file_path))

    def _load_sample(self) -> None:
        sample = APP_ROOT / "samples" / "sample_spectrum.csv"
        if sample.exists():
            self.ingest_path(sample)
        else:
            self.error_occurred.emit("Sample dataset not found.")

    def ingest_path(self, path: Path) -> None:
        try:
            spectrum = self.container.ingest.ingest(path)
            self.container.overlay.add(spectrum)
            self.status_message.emit(f"Loaded {path.name}")
            self.refresh()
            self.spectra_changed.emit()
        except Exception as exc:  # noqa: BLE001 - show to user
            self.error_occurred.emit(str(exc))
            logger.exception("Failed to ingest %s", path)

    def refresh(self) -> None:
        spectra = self.container.overlay.spectra()
        self.table.setRowCount(len(spectra))
        for idx, spectrum in enumerate(spectra):
            self.table.setItem(idx, 0, QtWidgets.QTableWidgetItem(spectrum.name))
            self.table.setItem(idx, 1, QtWidgets.QTableWidgetItem(str(len(spectrum.wavelength_nm))))
            source = spectrum.metadata.get("source", {})
            self.table.setItem(idx, 2, QtWidgets.QTableWidgetItem(Path(source.get("path", "")).name))
            self.table.setItem(idx, 3, QtWidgets.QTableWidgetItem(spectrum.flux_unit))
        self.refresh_chart()

    def refresh_chart(self) -> None:
        spectra = self.container.overlay.spectra()
        data: List[tuple[str, np.ndarray, np.ndarray]] = []
        for spectrum in spectra:
            context = spectrum.metadata.get("flux_context", {}) if isinstance(spectrum.metadata, dict) else {}
            x, y = spectrum.as_units(
                self.container.units,
                wavelength_unit=self.wavelength_unit.currentText(),
                flux_unit=self.flux_unit.currentText(),
                context=context,
            )
            data.append((spectrum.name, x, y))
        self.chart.update_series(data)


class CompareTab(QtWidgets.QWidget):
    """Tab for differential math operations."""

    status_message = QtCore.Signal(str)
    error_occurred = QtCore.Signal(str)
    spectrum_created = QtCore.Signal(Spectrum)

    def __init__(self, container: ServiceContainer, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.container = container
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)

        selector_layout = QtWidgets.QHBoxLayout()
        selector_layout.addWidget(QtWidgets.QLabel("Spectrum A:"))
        self.combo_a = QtWidgets.QComboBox()
        self.combo_a.currentIndexChanged.connect(self._update_chart)
        selector_layout.addWidget(self.combo_a)

        selector_layout.addWidget(QtWidgets.QLabel("Spectrum B:"))
        self.combo_b = QtWidgets.QComboBox()
        self.combo_b.currentIndexChanged.connect(self._update_chart)
        selector_layout.addWidget(self.combo_b)
        selector_layout.addStretch(1)
        layout.addLayout(selector_layout)

        button_row = QtWidgets.QHBoxLayout()
        self.diff_button = QtWidgets.QPushButton("Subtract (A − B)")
        self.diff_button.clicked.connect(self._compute_difference)
        button_row.addWidget(self.diff_button)

        self.ratio_button = QtWidgets.QPushButton("Ratio (A / B)")
        self.ratio_button.clicked.connect(self._compute_ratio)
        button_row.addWidget(self.ratio_button)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        self.chart = OverlayChart()
        layout.addWidget(self.chart)

        self.result_summary = QtWidgets.QPlainTextEdit()
        self.result_summary.setReadOnly(True)
        layout.addWidget(self.result_summary)

    def update_spectra(self) -> None:
        spectra = self.container.overlay.spectra()
        self.combo_a.blockSignals(True)
        self.combo_b.blockSignals(True)
        self.combo_a.clear()
        self.combo_b.clear()
        for spectrum in spectra:
            self.combo_a.addItem(spectrum.name, spectrum.id)
            self.combo_b.addItem(spectrum.name, spectrum.id)
        self.combo_a.blockSignals(False)
        self.combo_b.blockSignals(False)
        self._update_chart()

    def _selected_spectra(self) -> Optional[tuple[Spectrum, Spectrum]]:
        id_a = self.combo_a.currentData()
        id_b = self.combo_b.currentData()
        if not id_a or not id_b:
            return None
        spec_a = self.container.overlay.get(id_a)
        spec_b = self.container.overlay.get(id_b)
        if spec_a is None or spec_b is None:
            return None
        return spec_a, spec_b

    def _update_chart(self) -> None:
        spectra_pair = self._selected_spectra()
        if spectra_pair is None:
            self.chart.update_series([])
            return
        a, b = spectra_pair
        data = [
            (a.name, a.wavelength_nm, a.flux),
            (b.name, b.wavelength_nm, b.flux),
        ]
        self.chart.update_series(data)

    def _compute_difference(self) -> None:
        self._run_operation(self.container.math.difference)

    def _compute_ratio(self) -> None:
        self._run_operation(self.container.math.ratio)

    def _run_operation(self, operation) -> None:
        spectra_pair = self._selected_spectra()
        if spectra_pair is None:
            self.error_occurred.emit("Select both spectra before running operations.")
            return
        a, b = spectra_pair
        result: MathResult = operation(a, b)
        if result.suppressed:
            self.status_message.emit(f"Operation suppressed: {result.message}")
            self.result_summary.setPlainText(f"Suppressed: {result.message}")
            return
        assert result.spectrum is not None
        manifest = self.container.provenance.create_manifest([result.spectrum, a, b], operations=result.spectrum.provenance)
        self.result_summary.setPlainText(json.dumps(manifest, indent=2))
        self.spectrum_created.emit(result.spectrum)
        self.status_message.emit(f"Created derived spectrum: {result.spectrum.name}")


class ProvenanceTab(QtWidgets.QWidget):
    """Display provenance manifests for loaded spectra."""

    def __init__(self, container: ServiceContainer, parent: Optional[QtWidgets.QWidget] = None) -> None:
        super().__init__(parent)
        self.container = container
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        selector_layout = QtWidgets.QHBoxLayout()
        selector_layout.addWidget(QtWidgets.QLabel("Spectrum:"))
        self.combo = QtWidgets.QComboBox()
        selector_layout.addWidget(self.combo)
        self.refresh_button = QtWidgets.QPushButton("Generate Manifest")
        self.refresh_button.clicked.connect(self._generate_manifest)
        selector_layout.addWidget(self.refresh_button)
        selector_layout.addStretch(1)
        layout.addLayout(selector_layout)

        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

    def update_spectra(self) -> None:
        self.combo.blockSignals(True)
        self.combo.clear()
        for spectrum in self.container.overlay.spectra():
            self.combo.addItem(spectrum.name, spectrum.id)
        self.combo.blockSignals(False)

    def _generate_manifest(self) -> None:
        spectrum_id = self.combo.currentData()
        if not spectrum_id:
            self.output.setPlainText("No spectrum selected.")
            return
        spectrum = self.container.overlay.get(spectrum_id)
        if spectrum is None:
            self.output.setPlainText("Spectrum not found.")
            return
        manifest = self.container.provenance.create_manifest([spectrum])
        self.output.setPlainText(json.dumps(manifest, indent=2))


class MainWindow(QtWidgets.QMainWindow):
    """Main application window containing the minimal UI shell."""

    def __init__(self, container: ServiceContainer) -> None:
        super().__init__()
        self.container = container
        self.setWindowTitle("Spectra Application")
        self.resize(1200, 800)
        self._build_menu()
        self.statusBar().showMessage("Ready")
        self.tabs = QtWidgets.QTabWidget()
        self.data_tab = DataTab(container)
        self.compare_tab = CompareTab(container)
        self.provenance_tab = ProvenanceTab(container)
        self.tabs.addTab(self.data_tab, "Data")
        self.tabs.addTab(self.compare_tab, "Compare")
        self.tabs.addTab(self.provenance_tab, "Provenance")
        self.setCentralWidget(self.tabs)

        self.data_tab.status_message.connect(self._set_status)
        self.data_tab.error_occurred.connect(self._show_error)
        self.data_tab.spectra_changed.connect(self._propagate_spectra_changed)

        self.compare_tab.status_message.connect(self._set_status)
        self.compare_tab.error_occurred.connect(self._show_error)
        self.compare_tab.spectrum_created.connect(self._add_derived_spectrum)

        self._propagate_spectra_changed()

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        open_action = QtGui.QAction("&Open…", self)
        open_action.triggered.connect(self.data_tab._open_files)  # type: ignore[attr-defined]
        file_menu.addAction(open_action)

        save_manifest = QtGui.QAction("Export Manifest…", self)
        save_manifest.triggered.connect(self._export_manifest)
        file_menu.addAction(save_manifest)

        exit_action = QtGui.QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _set_status(self, message: str) -> None:
        self.statusBar().showMessage(message, 5000)

    def _show_error(self, message: str) -> None:
        QtWidgets.QMessageBox.critical(self, "Error", message)

    def _propagate_spectra_changed(self) -> None:
        self.compare_tab.update_spectra()
        self.provenance_tab.update_spectra()

    def _add_derived_spectrum(self, spectrum: Spectrum) -> None:
        self.container.overlay.add(spectrum)
        self.data_tab.refresh()
        self._propagate_spectra_changed()

    def _export_manifest(self) -> None:
        spectra = self.container.overlay.spectra()
        if not spectra:
            self._show_error("No spectra loaded")
            return
        manifest = self.container.provenance.create_manifest(spectra)
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save manifest",
            str(APP_ROOT / "reports" / "latest_manifest.json"),
            "JSON files (*.json)",
        )
        if path:
            self.container.provenance.save_manifest(manifest, Path(path))
            self._set_status(f"Manifest saved to {path}")


def build_container() -> ServiceContainer:
    units = UnitsService()
    provenance = ProvenanceService()
    ingest = DataIngestService(units_service=units, provenance_service=provenance)
    overlay = OverlayService()
    math = MathService()
    return ServiceContainer(units=units, provenance=provenance, ingest=ingest, overlay=overlay, math=math)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    app = QtWidgets.QApplication([])
    container = build_container()
    window = MainWindow(container)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
